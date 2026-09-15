# brandgate-connector

The plumbing that carries gate verdicts into Slack and onto the site. Go, stdlib only, one
binary. It never scores, never decides and never edits a verdict; the gate is the only judge.

```bash
cd connector && go build -o brandgate-connector .

brandgate-connector --dry-run post  runs/verdicts.jsonl   # print every payload, call nothing
brandgate-connector post  runs/verdicts.jsonl             # post each row once, then exit (CI)
brandgate-connector watch runs/verdicts.jsonl             # tail the file, post each new row
```

| env | what |
|---|---|
| `SLACK_WEBHOOK_URL` | incoming webhook. Every verdict becomes one Block Kit message, pass and fail alike. |
| `VERCEL_DEPLOY_HOOK` | called once per 30 second window when a verdict for `surfaces/*/accepted/` arrives. |
| `SITE_BASE_URL` | where deployed surfaces live. An accepted image is linked by URL; otherwise text only. |

Secrets stay in the environment. The binary logs the webhook's host and never the URL, not
even redacted.

## The row

`python -m pipeline.gate score <image> --emit runs/verdicts.jsonl` appends one line of JSON
per scored image. That line is the contract between the gate and this binary; the gate writes
it in `pipeline/gate.py`, `verdict_row`, and `verdict.go` reads it.

```json
{"id": "takes_02:t3",
 "image": "lookdev/archive/takes_02.png",
 "verdict": "fail",
 "on_brand": 0.79,
 "novelty": 1.0,
 "failed_rules": ["colour.01"],
 "reasons": {"colour.01": "the ground is #ECEAF6, 14 from the nearest allowed ground #FAFAF8"},
 "ts": "2026-09-15T21:00:00Z",
 "git": "604343b"}
```

`id` is the image's stem, plus `:tN` for a tile of a takes sheet. `image` is repo-relative.
`on_brand` is null and `verdict` is `unscored` when nothing in the frame could be measured.
`reasons` carries the gate's own sentence for every failed rule, which is what the channel
is for. `git` is the short SHA of the checkout that scored it, or null outside a repo.

## What it promises

- **Once.** A row is keyed on `id` plus `ts` and recorded in `<verdicts>.posted` beside the
  file the moment its message lands. The same row read twice is one message; a restart of
  `watch` replays nothing, and `watch` starts at the end of the file besides.
- **Bounded retries.** 429 and 5xx are retried five times with doubling backoff, then the
  row is logged to stderr and left unmarked so a later `post` picks it up. Any other error is
  final.
- **One deploy per batch.** Accepted frames arriving together arm one timer; the hook is
  called once when it fires.
- **Nothing on `--dry-run`.** The exact payloads, printed. This is the demo with no workspace.

## Try it without a workspace

```bash
python -m pipeline.gate score lookdev/archive/takes_02.png --crop t3 --emit /tmp/v.jsonl
connector/brandgate-connector --dry-run post /tmp/v.jsonl
```

`go test ./...` covers the message shape, retry and give-up, the host-only error text,
idempotency across a restart, the debounce with an injected timer, and `watch` skipping two
hundred old rows and reassembling a row written in two halves.
