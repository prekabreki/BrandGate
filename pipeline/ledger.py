"""The run ledger: one append-only JSON line per logical generation.

One row per logical run, not per attempt. If the backend is retried after a
timeout the run keeps its run_id and still writes a single row, because the
question the ledger answers later is "what did it take to get this frame",
and a retry is part of that answer rather than a second frame.

A failed run writes a row too, with `error` set and `output_path` null. A
ledger that records only successes cannot tell you what the gate rejected or
what the model refused, which is most of what a model scorecard is made of.

Nothing here may raise into the caller: losing a ledger row must never cost a
render that has already been paid for in GPU time.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "runs", "ledger.jsonl")

# Every row carries every key, in this order. A reader can then treat the file
# as a table without defaulting absent columns, and a diff of two rows from
# different models shows exactly the fields that moved.
FIELDS = (
    "run_id", "ts", "model", "tier", "prompt_id", "prompt_text",
    "params", "seed", "lora", "output_path", "cost_usd", "latency_s", "error",
)


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def now() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def row(*, run_id, model, tier, prompt_id, prompt_text, params, seed,
        lora=None, output_path=None, cost_usd=None, latency_s=None,
        error=None, ts=None) -> dict:
    """Build a ledger row with the full field set in a fixed order.

    cost_usd is null for every local run and that is deliberate, not a stub:
    generation happens on hardware already owned, so there is no per-frame
    price to record and inventing one would poison the scorecard. The column
    exists so a metered backend can fill it without reshaping the file.
    """
    return {
        "run_id": run_id,
        "ts": ts or now(),
        "model": model,
        "tier": tier,
        "prompt_id": prompt_id,
        "prompt_text": prompt_text,
        "params": params,
        "seed": seed,
        "lora": list(lora or []),
        "output_path": output_path,
        "cost_usd": cost_usd,
        "latency_s": None if latency_s is None else round(float(latency_s), 1),
        "error": error,
    }


def append(record: dict, path: str | None = None) -> bool:
    """Append one row. Returns True if it landed; warns and returns False if
    not. utf-8 and an explicit "\\n" are load-bearing across the two machines
    this repo is worked from: the default encoding on one of them would raise
    on an em dash and write CRLF the other churns back."""
    target = path or LEDGER
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with open(target, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line + "\n")
        return True
    except Exception as e:
        print(f"WARNING: ledger append failed ({e}), the render is unaffected",
              file=sys.stderr)
        return False


def read(path: str | None = None) -> list[dict]:
    """Every row in the ledger, oldest first. Blank lines are skipped; a
    corrupt line raises, because silently dropping one would understate a
    count the calibration write-up depends on."""
    target = path or LEDGER
    if not os.path.exists(target):
        return []
    rows = []
    with open(target, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{target}:{lineno}: corrupt ledger line: {e}") from None
    return rows
