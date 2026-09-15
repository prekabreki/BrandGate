"""Fill the sameness pool: many grounds from ONE model at ONE tier.

    python -m runs.pool --count 200
    python -m runs.pool --count 200 --dry-run

The calibration batch spreads seeds across both models and both tiers on
purpose. The sameness run (#10) wants the opposite: hold everything still
except the seed, so that when the gate is tightened and the accepted set goes
uniform, the uniformity is the gate's doing and not a model's. Seeds start at
2000 so no pool frame shares a seed with a calibration frame.

Resumable. A seed whose frame is already in the pool is skipped, so a run that
dies at frame 140 picks up at 141 and the ledger gets one row per frame.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

POOL_DIR = os.path.join(ROOT, "surfaces", "_pool")
SEED_START = 2000


def existing_seeds(dest: str, prompt: str, tier: str) -> set[int]:
    """Seeds already rendered into dest. The filename is
    <prompt>_<tier>_<seed>_<run>_00001_.png, per gen.generate's prefix."""
    seeds = set()
    for p in glob.glob(os.path.join(dest, f"{prompt}_{tier}_*.png")):
        parts = os.path.basename(p).split("_")
        try:
            seeds.add(int(parts[len(prompt.split("_")) + 1]))
        except (IndexError, ValueError):
            continue
    return seeds


def fill(count: int, prompt: str, model: str, tier: str, dest: str,
         seed_start: int = SEED_START, dry_run: bool = False,
         backend=None, ledger_path: str | None = None) -> list[dict]:
    from pipeline import gen

    os.makedirs(dest, exist_ok=True)
    done = existing_seeds(dest, prompt, tier)
    rows, t0 = [], time.monotonic()
    for i in range(count):
        seed = seed_start + i
        label = f"[{i + 1:>3}/{count}] {model}/{tier} seed {seed}"
        if seed in done:
            print(f"{label}  already in the pool", flush=True)
            continue
        if dry_run:
            print(f"{label}  would generate", flush=True)
            rows.append({"seed": seed, "output_path": None})
            continue
        _, record = gen.generate(prompt, seed=seed, model=model, tier=tier,
                                 dest_dir=dest, backend=backend,
                                 ledger_path=ledger_path)
        rows.append(record)
        if record["error"]:
            # Keep going. One refused frame must not cost the rest of the pool.
            print(f"{label}  ERROR {record['error']}", flush=True)
            continue
        elapsed = time.monotonic() - t0
        print(f"{label}  {record['latency_s']}s  ({elapsed / 60:.0f} min so far)",
              flush=True)
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m runs.pool")
    p.add_argument("--count", type=int, default=200)
    p.add_argument("--prompt", default="hero-ground")
    p.add_argument("--model", default="krea2")
    p.add_argument("--tier", default="turbo", choices=("turbo", "raw"))
    p.add_argument("--out", default=POOL_DIR)
    p.add_argument("--seed-start", type=int, default=SEED_START)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    rows = fill(a.count, a.prompt, a.model, a.tier, a.out,
                seed_start=a.seed_start, dry_run=a.dry_run)
    failed = [r for r in rows if r.get("error")]
    print(f"{len(rows) - len(failed)} generated, {len(failed)} failed, "
          f"{len(existing_seeds(a.out, a.prompt, a.tier))} in the pool")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
