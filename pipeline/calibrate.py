"""Build the calibration set: generate a spread of grounds, then a contact
sheet to label them on.

    python -m pipeline.calibrate batch --count 30
    python -m pipeline.calibrate sheet
    python -m pipeline.calibrate labels --set hero-ground_krea2_turbo_7 off

The gate is only as honest as the set it was calibrated against, and the set is
only worth anything if the labels come from the designer. So this does the
tedious half, and asks a person for nothing but a verdict per tile.

The batch spreads across seeds and both models on purpose. A calibration set
drawn from one model at one tier measures that corner and nothing else, and the
thresholds it produces would move the first time a surface came from elsewhere.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALIB_DIR = os.path.join(ROOT, "surfaces", "_calibration")
SHEET = os.path.join(ROOT, "docs", "calibration-sheet.png")
LABELS = os.path.join(ROOT, "docs", "calibration-labels.json")

TILE_W, COLS, PAD = 320, 5, 14


def plan(count: int, prompt: str, models=("krea2", "flux2"),
         tiers=("turbo", "raw")) -> list[dict]:
    """Seeds spread across models and tiers, round-robin so a short run still
    covers every combination rather than thirty frames of the first one."""
    combos = [(m, t) for m in models for t in tiers]
    return [{"prompt": prompt, "seed": 1000 + i,
             "model": combos[i % len(combos)][0],
             "tier": combos[i % len(combos)][1]}
            for i in range(count)]


def batch(count: int, prompt: str, dest: str | None = None, dry_run: bool = False,
          backend=None, ledger_path: str | None = None) -> list[dict]:
    from pipeline import gen

    dest = dest or CALIB_DIR
    rows = []
    for i, spec in enumerate(plan(count, prompt), start=1):
        label = f"{spec['model']}/{spec['tier']} seed {spec['seed']}"
        if dry_run:
            print(f"[{i:>2}/{count}] would generate {label}")
            rows.append({**spec, "output_path": None})
            continue
        print(f"[{i:>2}/{count}] {label}", flush=True)
        _, record = gen.generate(spec["prompt"], seed=spec["seed"],
                                 model=spec["model"], tier=spec["tier"],
                                 dest_dir=dest, backend=backend,
                                 ledger_path=ledger_path)
        if record["error"]:
            # Keep going. One refused frame must not cost the other twenty-nine,
            # and the failure is already a row in the ledger.
            print(f"      failed: {record['error'][:90]}", file=sys.stderr)
        rows.append({**spec, "output_path": record["output_path"]})
    return rows


def tile_id(path: str) -> str:
    """Stable, readable id for a frame, used on the sheet and in the labels."""
    return os.path.splitext(os.path.basename(path))[0]


def sheet(src: str | None = None, dest: str | None = None,
          extra: list[str] | None = None) -> str:
    """A numbered contact sheet. Every tile carries its id, so a label written
    against a number can never drift from the frame it was written for."""
    import glob

    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    paths = sorted(glob.glob(os.path.join(src or CALIB_DIR, "*.png")))
    paths += list(extra or [])
    if not paths:
        raise FileNotFoundError(f"no frames under {src or CALIB_DIR}")

    thumbs = []
    for p in paths:
        img = cv2.imread(p)
        if img is None:
            continue
        h = max(1, int(img.shape[0] * TILE_W / img.shape[1]))
        thumbs.append((tile_id(p), cv2.cvtColor(
            cv2.resize(img, (TILE_W, h), interpolation=cv2.INTER_AREA),
            cv2.COLOR_BGR2RGB)))
    if not thumbs:
        raise FileNotFoundError("every candidate frame failed to decode")

    tile_h = max(t.shape[0] for _, t in thumbs)
    rows = (len(thumbs) + COLS - 1) // COLS
    cap = 34
    W = COLS * TILE_W + (COLS + 1) * PAD
    H = rows * (tile_h + cap) + (rows + 1) * PAD
    canvas = Image.new("RGB", (W, H), (250, 250, 248))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Regular.ttf", 12)
    except OSError:
        font = ImageFont.load_default()

    for i, (tid, thumb) in enumerate(thumbs):
        r, c = divmod(i, COLS)
        x = PAD + c * (TILE_W + PAD)
        y = PAD + r * (tile_h + cap + PAD)
        canvas.paste(Image.fromarray(thumb), (x, y))
        draw.rectangle([x, y, x + TILE_W - 1, y + thumb.shape[0] - 1],
                       outline=(17, 17, 20, 40))
        # Captions sit on the ROW baseline, not under each thumb. Frames of
        # mixed aspect otherwise scatter the ids down the page and the sheet
        # stops being scannable, which is the one thing it is for.
        draw.text((x, y + tile_h + 8), f"{i + 1:>2}. {tid[:44]}",
                  fill=(74, 74, 85), font=font)

    target = dest or SHEET
    os.makedirs(os.path.dirname(target), exist_ok=True)
    canvas.save(target)
    return target


def write_labels(pairs: dict, path: str | None = None) -> dict:
    """Merge label decisions into docs/calibration-labels.json.

    Merged rather than replaced: labelling twenty images is a job done over more
    than one sitting, and a partial second pass must not silently discard the
    first.
    """
    target = path or LABELS
    doc = {"labels": {}}
    if os.path.exists(target):
        with open(target, encoding="utf-8") as fh:
            doc = json.load(fh)
    for tid, verdict in pairs.items():
        if verdict not in ("on", "off"):
            raise ValueError(f"{tid}: label must be 'on' or 'off', got {verdict!r}")
        doc.setdefault("labels", {})[tid] = verdict
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return doc


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m pipeline.calibrate")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("batch", help="generate a spread of grounds to label")
    b.add_argument("--count", type=int, default=30)
    b.add_argument("--prompt", default="hero-ground")
    b.add_argument("--out", default=CALIB_DIR)
    b.add_argument("--dry-run", action="store_true")

    s = sub.add_parser("sheet", help="build the contact sheet to label on")
    s.add_argument("--src", default=CALIB_DIR)
    s.add_argument("--out", default=SHEET)

    l = sub.add_parser("labels", help="record on/off labels")
    l.add_argument("--set", nargs=2, action="append", metavar=("ID", "VERDICT"),
                   required=True, help="a tile id and 'on' or 'off'")

    a = p.parse_args(argv)
    if a.cmd == "batch":
        rows = batch(a.count, a.prompt, a.out, a.dry_run)
        made = sum(1 for r in rows if r["output_path"])
        print(f"{made}/{len(rows)} frames under {a.out}")
    elif a.cmd == "sheet":
        try:
            print(sheet(a.src, a.out))
        except FileNotFoundError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
    else:
        doc = write_labels(dict(a.set))
        on = sum(1 for v in doc["labels"].values() if v == "on")
        print(f"{len(doc['labels'])} labelled ({on} on-brand, "
              f"{len(doc['labels']) - on} off-brand)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
