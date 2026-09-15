package main

import (
	"context"
	"sync"
	"time"
)

// deployer calls the Vercel deploy hook at most once per debounce window. A
// batch of accepted frames arriving together is one deploy, not one per
// frame. The timer is injectable so a test can fire it without waiting.
type deployer struct {
	hook   string
	window time.Duration
	post   func(ctx context.Context, hook string, payload any) error
	after  func(d time.Duration, f func()) // time.AfterFunc in production
	log    func(format string, args ...any)

	mu      sync.Mutex
	pending bool
	fired   int
	done    chan struct{}
}

func newDeployer(hook string, window time.Duration, post func(context.Context, string, any) error,
	log func(string, ...any)) *deployer {
	return &deployer{
		hook: hook, window: window, post: post, log: log,
		after: func(d time.Duration, f func()) { time.AfterFunc(d, f) },
	}
}

// trigger notes that a deploy is wanted. The first call in a quiet window
// arms the timer; later calls inside the window ride along.
func (d *deployer) trigger() {
	if d == nil || d.hook == "" {
		return
	}
	d.mu.Lock()
	defer d.mu.Unlock()
	if d.pending {
		return
	}
	d.pending = true
	d.done = make(chan struct{})
	done := d.done
	d.after(d.window, func() {
		defer close(done)
		d.mu.Lock()
		d.pending = false
		d.fired++
		d.mu.Unlock()
		if err := d.post(context.Background(), d.hook, map[string]any{}); err != nil {
			d.log("deploy hook at %s failed: %v", hostOf(d.hook), err)
			return
		}
		d.log("deploy hook at %s called", hostOf(d.hook))
	})
}

// wait blocks until an armed deploy has fired, for a clean exit of `post`.
func (d *deployer) wait() {
	if d == nil {
		return
	}
	d.mu.Lock()
	done := d.done
	pending := d.pending
	d.mu.Unlock()
	if pending && done != nil {
		<-done
	}
}
