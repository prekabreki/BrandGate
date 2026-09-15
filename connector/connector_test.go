package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func f64(x float64) *float64 { return &x }

func sampleFail() Verdict {
	g := "abc1234"
	return Verdict{
		ID: "takes_02:t3", Image: "lookdev/archive/takes_02.png", Verdict: "fail",
		OnBrand: f64(0.79), Novelty: 1.0, FailedRules: []string{"colour.01"},
		Reasons: map[string]string{"colour.01": "the ground is #ECEAF6, 14 from the nearest allowed ground #FAFAF8"},
		TS:      "2026-09-15T21:00:00Z", Git: &g,
	}
}

func samplePass(id string) Verdict {
	return Verdict{
		ID: id, Image: "surfaces/hero/accepted/hero.png", Verdict: "pass",
		OnBrand: f64(0.99), Novelty: 1.0, FailedRules: nil, Reasons: map[string]string{},
		TS: "2026-09-15T21:01:00Z",
	}
}

func quiet(string, ...any) {}

func TestSlackMessageCarriesTheRuleAndItsReason(t *testing.T) {
	m := slackMessage(sampleFail(), "")
	b, _ := json.Marshal(m)
	s := string(b)
	for _, want := range []string{"takes_02:t3: FAIL", "colour.01", "#ECEAF6", "0.79", "abc1234"} {
		if !strings.Contains(s, want) {
			t.Errorf("payload lacks %q:\n%s", want, s)
		}
	}
	if strings.Contains(s, "\u2014") {
		t.Errorf("an em dash in a payload that ships under the brand")
	}
	if strings.Contains(s, "image_url") {
		t.Errorf("a failed verdict is not deployed, so it must not link an image")
	}
}

func TestSlackMessageLinksTheImageOnlyWhenDeployed(t *testing.T) {
	b, _ := json.Marshal(slackMessage(samplePass("hero"), "https://handsel-lovat.vercel.app/"))
	if !strings.Contains(string(b), "https://handsel-lovat.vercel.app/surfaces/hero/accepted/hero.png") {
		t.Errorf("accepted surface with a site base must be linked by URL:\n%s", b)
	}
	b, _ = json.Marshal(slackMessage(samplePass("hero"), ""))
	if strings.Contains(string(b), "image_url") {
		t.Errorf("no site base, no image block")
	}
}

func newServer(t *testing.T, codes ...int) (*httptest.Server, *int32) {
	t.Helper()
	var calls int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		n := atomic.AddInt32(&calls, 1)
		code := 200
		if int(n) <= len(codes) {
			code = codes[n-1]
		}
		w.WriteHeader(code)
	}))
	t.Cleanup(srv.Close)
	return srv, &calls
}

func TestPostRetriesOn5xxAndThenSucceeds(t *testing.T) {
	srv, calls := newServer(t, 503, 429, 200)
	p := newPoster(srv.Client(), quiet)
	var slept []time.Duration
	p.sleep = func(d time.Duration) { slept = append(slept, d) }
	if err := p.post(context.Background(), srv.URL, map[string]any{"text": "x"}); err != nil {
		t.Fatal(err)
	}
	if *calls != 3 {
		t.Errorf("want 3 calls, got %d", *calls)
	}
	if len(slept) != 2 || slept[1] != 2*slept[0] {
		t.Errorf("backoff should double: %v", slept)
	}
}

func TestPostGivesUpAfterFiveAttempts(t *testing.T) {
	srv, calls := newServer(t, 500, 500, 500, 500, 500, 500, 500)
	p := newPoster(srv.Client(), quiet)
	p.sleep = func(time.Duration) {}
	err := p.post(context.Background(), srv.URL, map[string]any{})
	if err == nil || !strings.Contains(err.Error(), "gave up after 5") {
		t.Fatalf("want a give-up error, got %v", err)
	}
	if *calls != 5 {
		t.Errorf("want exactly 5 attempts, got %d", *calls)
	}
}

func TestPostDoesNotRetryA4xxOtherThan429(t *testing.T) {
	srv, calls := newServer(t, 404)
	p := newPoster(srv.Client(), quiet)
	p.sleep = func(time.Duration) {}
	if err := p.post(context.Background(), srv.URL, map[string]any{}); err == nil {
		t.Fatal("a 404 must be an error")
	}
	if *calls != 1 {
		t.Errorf("a 404 is final, got %d calls", *calls)
	}
}

func TestErrorsNameTheHostNeverTheURL(t *testing.T) {
	srv, _ := newServer(t, 500, 500, 500, 500, 500)
	p := newPoster(srv.Client(), quiet)
	p.sleep = func(time.Duration) {}
	hook := srv.URL + "/services/T000/B000/SECRETSECRET"
	err := p.post(context.Background(), hook, map[string]any{})
	if err == nil || strings.Contains(err.Error(), "SECRET") || strings.Contains(err.Error(), "/services/") {
		t.Fatalf("the error must not carry the webhook path: %v", err)
	}
}

func newRelay(t *testing.T, srv *httptest.Server, dir string) (*relay, *int32) {
	t.Helper()
	state, err := loadState(filepath.Join(dir, "verdicts.posted"))
	if err != nil {
		t.Fatal(err)
	}
	p := newPoster(srv.Client(), quiet)
	p.sleep = func(time.Duration) {}
	var deploys int32
	d := newDeployer(srv.URL+"/deploy", 30*time.Second,
		func(context.Context, string, any) error { atomic.AddInt32(&deploys, 1); return nil }, quiet)
	return &relay{slackHook: srv.URL, poster: p, deploy: d, state: state,
		out: func(string, ...any) {}, log: quiet}, &deploys
}

func TestTheSameRowTwiceIsOneMessage(t *testing.T) {
	srv, calls := newServer(t)
	r, _ := newRelay(t, srv, t.TempDir())
	v := sampleFail()
	for i := 0; i < 3; i++ {
		if err := r.handle(context.Background(), v); err != nil {
			t.Fatal(err)
		}
	}
	if *calls != 1 {
		t.Errorf("want 1 message, got %d", *calls)
	}
	// And across a restart: a new relay on the same state file posts nothing.
	r2, _ := newRelay(t, srv, filepath.Dir(r.state.path))
	if err := r2.handle(context.Background(), v); err != nil {
		t.Fatal(err)
	}
	if *calls != 1 {
		t.Errorf("a restart replayed a posted verdict: %d", *calls)
	}
}

func TestADryRunLeavesNoTrace(t *testing.T) {
	srv, calls := newServer(t)
	r, _ := newRelay(t, srv, t.TempDir())
	r.dryRun = true
	v := sampleFail()
	if err := r.handle(context.Background(), v); err != nil {
		t.Fatal(err)
	}
	if *calls != 0 || r.state.has(v.Key()) {
		t.Fatalf("a dry run must call nothing (%d calls) and mark nothing (%v)", *calls, r.state.has(v.Key()))
	}
	r.dryRun = false
	if err := r.handle(context.Background(), v); err != nil {
		t.Fatal(err)
	}
	if *calls != 1 {
		t.Errorf("the real run after a dry run must still post, got %d", *calls)
	}
}

func TestAFailedPostIsNotMarkedPosted(t *testing.T) {
	srv, _ := newServer(t, 500, 500, 500, 500, 500, 200)
	r, _ := newRelay(t, srv, t.TempDir())
	v := sampleFail()
	if err := r.handle(context.Background(), v); err == nil {
		t.Fatal("five 500s must surface as an error")
	}
	if r.state.has(v.Key()) {
		t.Fatal("an unposted verdict must not be marked posted")
	}
	if err := r.handle(context.Background(), v); err != nil {
		t.Fatalf("the retry after recovery must post: %v", err)
	}
}

func TestABatchOfAcceptedFramesIsOneDeploy(t *testing.T) {
	srv, _ := newServer(t)
	r, deploys := newRelay(t, srv, t.TempDir())
	var fire []func()
	var mu sync.Mutex
	r.deploy.after = func(_ time.Duration, f func()) { mu.Lock(); fire = append(fire, f); mu.Unlock() }
	for i := 0; i < 6; i++ {
		if err := r.handle(context.Background(), samplePass(fmt.Sprintf("card-%d", i))); err != nil {
			t.Fatal(err)
		}
	}
	mu.Lock()
	armed := len(fire)
	mu.Unlock()
	if armed != 1 {
		t.Fatalf("six accepted frames inside one window must arm one timer, got %d", armed)
	}
	fire[0]()
	if *deploys != 1 {
		t.Errorf("want 1 deploy, got %d", *deploys)
	}
	// A frame after the window fires arms a new one.
	if err := r.handle(context.Background(), samplePass("late")); err != nil {
		t.Fatal(err)
	}
	mu.Lock()
	armed = len(fire)
	mu.Unlock()
	if armed != 2 {
		t.Errorf("a frame after the window must arm a second deploy, got %d timers", armed)
	}
	// And a failed verdict never deploys.
	if err := r.handle(context.Background(), sampleFail()); err != nil {
		t.Fatal(err)
	}
	mu.Lock()
	armed = len(fire)
	mu.Unlock()
	if armed != 2 {
		t.Errorf("a fail must not deploy")
	}
}

func TestWatchStartsAtTheEndAndPostsOnlyNewRows(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "verdicts.jsonl")
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 200; i++ {
		row, _ := json.Marshal(samplePass(fmt.Sprintf("old-%d", i)))
		f.Write(row)
		f.WriteString("\n")
	}
	f.Close()

	var got []string
	var mu sync.Mutex
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan error, 1)
	go func() {
		done <- watchFile(ctx, path, 5*time.Millisecond, func(line string) {
			mu.Lock()
			got = append(got, line)
			mu.Unlock()
		})
	}()
	time.Sleep(30 * time.Millisecond)
	f, _ = os.OpenFile(path, os.O_APPEND|os.O_WRONLY, 0o644)
	row, _ := json.Marshal(sampleFail())
	// Written in two halves, to prove a partial line is held until its newline.
	f.Write(row[:10])
	time.Sleep(20 * time.Millisecond)
	f.Write(row[10:])
	f.WriteString("\n")
	f.Close()
	deadline := time.Now().Add(2 * time.Second)
	for {
		mu.Lock()
		n := len(got)
		mu.Unlock()
		if n >= 1 || time.Now().After(deadline) {
			break
		}
		time.Sleep(5 * time.Millisecond)
	}
	cancel()
	if err := <-done; err != nil {
		t.Fatal(err)
	}
	mu.Lock()
	defer mu.Unlock()
	if len(got) != 1 {
		t.Fatalf("200 old rows must be skipped and 1 new row seen, got %d", len(got))
	}
	if got[0] != string(row) {
		t.Errorf("the row arrived corrupted:\n%s\n%s", got[0], row)
	}
}

func TestParseVerdictsRejectsAHalfRowLoudly(t *testing.T) {
	_, err := parseVerdicts(strings.NewReader(`{"id":"a","ts":"t"}` + "\n" + `{"id":` + "\n"))
	if err == nil || !strings.Contains(err.Error(), "line 2") {
		t.Fatalf("a broken line must be named, got %v", err)
	}
	_, err = parseVerdicts(strings.NewReader(`{"image":"x"}` + "\n"))
	if err == nil {
		t.Fatal("a row without id and ts is not a verdict")
	}
}
