package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"sort"
	"strings"
	"time"
)

// slackMessage is the Block Kit payload for one verdict: the surface and its
// verdict in the header, on-brand and novelty as fields, each failed rule with
// the designer-readable reason the gate wrote, and the image by URL when the
// surface is deployed. Both passes and fails are posted; fail is what the
// channel exists for. No em dashes: this text ships under the brand.
func slackMessage(v Verdict, siteBase string) map[string]any {
	verdict := strings.ToUpper(v.Verdict)
	header := fmt.Sprintf("%s: %s", v.ID, verdict)
	onBrand := "unscored"
	if v.OnBrand != nil {
		onBrand = fmt.Sprintf("%.2f", *v.OnBrand)
	}
	blocks := []map[string]any{
		{"type": "header", "text": map[string]any{"type": "plain_text", "text": header, "emoji": false}},
		{"type": "section", "fields": []map[string]any{
			{"type": "mrkdwn", "text": "*On-brand*\n" + onBrand},
			{"type": "mrkdwn", "text": fmt.Sprintf("*Novelty*\n%.2f", v.Novelty)},
		}},
	}
	if len(v.FailedRules) > 0 {
		rules := append([]string(nil), v.FailedRules...)
		sort.Strings(rules)
		var b strings.Builder
		for _, r := range rules {
			reason := v.Reasons[r]
			if reason == "" {
				reason = "no reason recorded"
			}
			fmt.Fprintf(&b, "• `%s` %s\n", r, reason)
		}
		blocks = append(blocks, map[string]any{
			"type": "section",
			"text": map[string]any{"type": "mrkdwn", "text": strings.TrimRight(b.String(), "\n")},
		})
	}
	if siteBase != "" && v.Accepted() {
		u := strings.TrimRight(siteBase, "/") + "/" + strings.TrimLeft(v.Image, "/")
		blocks = append(blocks, map[string]any{
			"type": "image", "image_url": u,
			"alt_text": v.ID,
		})
	}
	ctx := fmt.Sprintf("%s · %s", v.Image, v.TS)
	if v.Git != nil && *v.Git != "" {
		ctx += " · " + *v.Git
	}
	blocks = append(blocks, map[string]any{
		"type":     "context",
		"elements": []map[string]any{{"type": "mrkdwn", "text": ctx}},
	})
	return map[string]any{"text": header, "blocks": blocks}
}

// poster posts JSON payloads to a webhook with bounded retries. The webhook
// URL is a secret and is never logged, not even redacted: only its host is.
type poster struct {
	client   *http.Client
	sleep    func(time.Duration)
	attempts int
	base     time.Duration
	log      func(format string, args ...any)
}

func newPoster(client *http.Client, log func(string, ...any)) *poster {
	return &poster{client: client, sleep: time.Sleep, attempts: 5, base: 200 * time.Millisecond, log: log}
}

func hostOf(raw string) string {
	u, err := url.Parse(raw)
	if err != nil || u.Host == "" {
		return "(unparseable url)"
	}
	return u.Host
}

// post sends payload to hook, retrying on 429 and 5xx with doubling backoff,
// and gives up after p.attempts. Anything else that is not 2xx is final.
func (p *poster) post(ctx context.Context, hook string, payload any) error {
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	host := hostOf(hook)
	var last error
	for i := 0; i < p.attempts; i++ {
		if i > 0 {
			p.sleep(p.base << (i - 1))
		}
		req, err := http.NewRequestWithContext(ctx, http.MethodPost, hook, bytes.NewReader(body))
		if err != nil {
			return err
		}
		req.Header.Set("Content-Type", "application/json")
		resp, err := p.client.Do(req)
		if err != nil {
			last = fmt.Errorf("post to %s: %w", host, err)
			continue
		}
		io.Copy(io.Discard, resp.Body)
		resp.Body.Close()
		switch {
		case resp.StatusCode >= 200 && resp.StatusCode < 300:
			return nil
		case resp.StatusCode == 429 || resp.StatusCode >= 500:
			last = fmt.Errorf("post to %s: status %d", host, resp.StatusCode)
			continue
		default:
			return fmt.Errorf("post to %s: status %d, not retrying", host, resp.StatusCode)
		}
	}
	return fmt.Errorf("gave up after %d attempts: %w", p.attempts, last)
}
