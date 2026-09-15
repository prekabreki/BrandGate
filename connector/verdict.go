// Package main is brandgate-connector: the plumbing that carries gate
// verdicts into Slack and onto the site. It never scores, never decides and
// never edits a verdict. The gate is the only judge; this binary is a relay.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"strings"
)

// Verdict is one row of runs/verdicts.jsonl, written by
// `python -m pipeline.gate score <image> --emit <file>`. The shape is the
// contract between the Python gate and this binary; connector/README.md
// documents it and pipeline/gate.py's verdict_row writes it.
type Verdict struct {
	ID          string            `json:"id"`
	Image       string            `json:"image"`
	Verdict     string            `json:"verdict"`
	OnBrand     *float64          `json:"on_brand"`
	Novelty     float64           `json:"novelty"`
	FailedRules []string          `json:"failed_rules"`
	Reasons     map[string]string `json:"reasons"`
	TS          string            `json:"ts"`
	Git         *string           `json:"git"`
}

// Key is what idempotency is keyed on: the same id at the same timestamp is
// the same verdict, however many times the row is read.
func (v Verdict) Key() string { return v.ID + "@" + v.TS }

// Accepted reports whether the row is a pass on an accepted surface, which is
// the only kind of verdict that changes the site.
func (v Verdict) Accepted() bool {
	return v.Verdict == "pass" && strings.Contains(v.Image, "/accepted/")
}

// parseVerdicts reads JSON rows, one per line, skipping blank lines. A line
// that is not a verdict is an error naming the line, not a silent skip: a
// relay that drops rows quietly is a relay nobody can trust.
func parseVerdicts(r io.Reader) ([]Verdict, error) {
	var out []Verdict
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)
	n := 0
	for sc.Scan() {
		n++
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		var v Verdict
		if err := json.Unmarshal([]byte(line), &v); err != nil {
			return out, fmt.Errorf("line %d: %w", n, err)
		}
		if v.ID == "" || v.TS == "" {
			return out, fmt.Errorf("line %d: a verdict needs an id and a ts", n)
		}
		out = append(out, v)
	}
	return out, sc.Err()
}
