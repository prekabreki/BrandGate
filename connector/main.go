package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

const usage = `brandgate-connector carries gate verdicts into Slack and onto the site.

  brandgate-connector [--dry-run] post  <verdicts.jsonl | verdict.json>
  brandgate-connector [--dry-run] watch <verdicts.jsonl>

Environment:
  SLACK_WEBHOOK_URL    incoming webhook; every verdict becomes one message
  VERCEL_DEPLOY_HOOK   called once per 30 s window when an accepted surface lands
  SITE_BASE_URL        where deployed surfaces live; images are linked by URL

The gate is the only judge. This binary never scores, never decides and never
edits a verdict. --dry-run prints the exact payloads and calls nothing.
`

type relay struct {
	slackHook string
	siteBase  string
	dryRun    bool
	poster    *poster
	deploy    *deployer
	state     *postedState
	out       func(format string, args ...any)
	log       func(format string, args ...any)
}

// handle posts one verdict once. A key already in the state file is skipped
// in silence, because that is the contract, not an error.
func (r *relay) handle(ctx context.Context, v Verdict) error {
	if r.state.has(v.Key()) {
		return nil
	}
	payload := slackMessage(v, r.siteBase)
	if r.dryRun {
		b, _ := json.MarshalIndent(payload, "", "  ")
		r.out("%s\n", b)
	} else if r.slackHook != "" {
		if err := r.poster.post(ctx, r.slackHook, payload); err != nil {
			row, _ := json.Marshal(v)
			r.log("not posted: %v\n%s", err, row)
			return err
		}
	}
	// A dry run leaves no trace: the point is to see the payloads, then run
	// it for real and have every row still post.
	if !r.dryRun {
		if err := r.state.mark(v.Key()); err != nil {
			return err
		}
	}
	if v.Accepted() {
		if r.dryRun {
			r.out("deploy hook would be called (debounced 30 s)\n")
		} else {
			r.deploy.trigger()
		}
	}
	return nil
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr *os.File) int {
	fs := flag.NewFlagSet("brandgate-connector", flag.ContinueOnError)
	fs.SetOutput(stderr)
	dry := fs.Bool("dry-run", false, "print payloads, call nothing")
	every := fs.Duration("every", time.Second, "poll interval for watch")
	fs.Usage = func() { fmt.Fprint(stderr, usage) }
	if err := fs.Parse(args); err != nil {
		return 2
	}
	rest := fs.Args()
	if len(rest) != 2 {
		fs.Usage()
		return 2
	}
	cmd, path := rest[0], rest[1]
	logger := log.New(stderr, "", log.LstdFlags)
	logf := func(format string, a ...any) { logger.Printf(format, a...) }
	outf := func(format string, a ...any) { fmt.Fprintf(stdout, format, a...) }

	statePath := strings.TrimSuffix(path, filepath.Ext(path)) + ".posted"
	state, err := loadState(statePath)
	if err != nil {
		logf("state file %s: %v", statePath, err)
		return 1
	}
	client := &http.Client{Timeout: 15 * time.Second}
	p := newPoster(client, logf)
	r := &relay{
		slackHook: os.Getenv("SLACK_WEBHOOK_URL"),
		siteBase:  os.Getenv("SITE_BASE_URL"),
		dryRun:    *dry,
		poster:    p,
		deploy:    newDeployer(os.Getenv("VERCEL_DEPLOY_HOOK"), 30*time.Second, p.post, logf),
		state:     state,
		out:       outf,
		log:       logf,
	}
	if !*dry && r.slackHook == "" {
		logf("SLACK_WEBHOOK_URL is not set; verdicts will be marked posted without a message. Use --dry-run to see payloads.")
	}
	if r.slackHook != "" {
		logf("slack webhook host: %s", hostOf(r.slackHook))
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	switch cmd {
	case "post":
		f, err := os.Open(path)
		if err != nil {
			logf("%v", err)
			return 1
		}
		rows, err := parseVerdicts(f)
		f.Close()
		if err != nil {
			logf("%s: %v", path, err)
			return 1
		}
		failed := 0
		for _, v := range rows {
			if err := r.handle(ctx, v); err != nil {
				failed++
			}
		}
		r.deploy.wait()
		if failed > 0 {
			logf("%d of %d rows not posted", failed, len(rows))
			return 1
		}
		return 0
	case "watch":
		logf("watching %s from its end; %d verdicts already posted", path, len(state.seen))
		err := watchFile(ctx, path, *every, func(line string) {
			rows, err := parseVerdicts(strings.NewReader(line))
			if err != nil {
				logf("skipping a line that is not a verdict: %v", err)
				return
			}
			for _, v := range rows {
				_ = r.handle(ctx, v)
			}
		})
		if err != nil {
			logf("%v", err)
			return 1
		}
		return 0
	default:
		fs.Usage()
		return 2
	}
}
