"""The sameness run (#10): tighten the gate on a fixed pool until the accepted
set stops moving, with the designer kept in the plot.

    python -m runs.sameness --pool surfaces/_pool --steps 5
    python -m runs.sameness --pool surfaces/_calibration --limit 8 --out /tmp/smoke

"Reliably" in the brief cuts both ways. A gate tightened until nothing new
survives is a brand that stopped moving, and it is the failure no pass rate
will show, because a gate that only accepts near-copies of what it already
knows can be tuned to accept them every time. So this run re-scores one fixed
pool of grounds at five threshold sets, loose to tight, and plots three things:
the pass rate, how alike the accepted frames are to each other, and how often
the gate agrees with the designer's 27 labels. The designer line is the point.
It peaks, then falls as the gate tightens past the designer's own taste.

The sweep never writes brand/gate.toml. It loads the file, overrides in memory
per step, and records verbatim what it used in runs/sameness/steps.md.
"""
from __future__ import annotations

import argparse
import copy
import glob
import itertools
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline import gate, novelty as novelty_mod, rules as rules_mod  # noqa: E402

POOL_DIR = os.path.join(ROOT, "surfaces", "_pool")
OUT_DIR = os.path.join(ROOT, "runs", "sameness")
LABELS = os.path.join(ROOT, "docs", "calibration-labels.json")
CALIB_DIR = os.path.join(ROOT, "surfaces", "_calibration")
TAKES = os.path.join(ROOT, "lookdev", "archive", "takes_02.png")

# The five threshold sets, loose to tight, as dotted keys into gate.toml.
# Step 2 is the shipped file as of 2026-09-15 (docs/calibration.md). Two
# steps sit looser than shipped so the designer's peak can show as a peak:
# the first run put the shipped bar at step 1, agreement peaked at step 0,
# and the curve had no left side. Every knob here is an on-brand bar.
#
# The table was cut against the 200-frame pool on 2026-09-15, judging the
# frames once measured. Step 0 accepts 165, step 1 145, shipped 79, step 3
# 16, step 4 three. The wash bars are what empty the set: the pool's edge
# p99 sits between 10 and 11 and its dark chroma between 38 and 40, so
# edge_max 10 or dark_chroma_max 38 alone leaves almost nothing. The first
# table stepped both to 9 and 35 and accepted nothing at either tight step,
# which is a badly chosen sweep, not a result.
#
# The novelty bar is NOT applied to pool acceptance during the sweep. Novelty
# is what this run measures; when it also filtered, 172 of the 200 frames
# were rejected as repeats before a brand bar had a say, and the pass rate
# was a novelty curve wearing an on-brand label. verdict.novelty_min is set
# to 0 in memory for the pool at every step and recorded in steps.md. The
# designer line never met the novelty bar (empty accepted set) either way.
#
# palette.tolerance_lab is NOT swept, and no longer needs to be avoided.
# Until #19 it served the permission ("the ground is paper") and the
# prohibition ("magenta is never a flat accent") with opposite senses, and
# three labelled frames failed colour.03 at a loose step and passed it at a
# tighter one. The prohibition now reads palette.forbid_tolerance_lab. The
# sweep still tightens the palette through forbid_mass alone, because that is
# the knob whose direction is unambiguous, and the run stays comparable with
# the one recorded in runs/sameness/steps.md.
KNOBS = ("verdict.on_brand_min", "palette.forbid_mass", "wash.dark_chroma_max",
         "wash.edge_max", "wash.stop_share_min")
STEPS = [
    dict(zip(KNOBS, (0.60, 0.10, 60.0, 20.0, 0.02))),
    dict(zip(KNOBS, (0.70, 0.06, 52.0, 16.0, 0.04))),
    dict(zip(KNOBS, (0.75, 0.04, 45.0, 13.0, 0.06))),
    dict(zip(KNOBS, (0.85, 0.025, 40.0, 11.5, 0.08))),
    dict(zip(KNOBS, (0.90, 0.02, 38.0, 11.0, 0.09))),
]
SHIPPED_STEP = 2


def build_steps(n: int = 5) -> list[dict]:
    """The table above when n is 5; otherwise n sets interpolated linearly
    between its first and last rows, so a smoke test can run three."""
    if n == len(STEPS):
        return [dict(s) for s in STEPS]
    if n < 2:
        raise ValueError("a sweep needs at least two steps")
    lo, hi = STEPS[0], STEPS[-1]
    return [{k: round(lo[k] + (hi[k] - lo[k]) * i / (n - 1), 4) for k in KNOBS}
            for i in range(n)]


def override(cfg: dict, thresholds: dict) -> dict:
    """A deep copy of cfg with each dotted key set. cfg itself is untouched."""
    out = copy.deepcopy(cfg)
    for dotted, value in thresholds.items():
        section, key = dotted.split(".")
        if key not in out[section]:
            raise KeyError(f"{dotted} is not a threshold in gate.toml")
        out[section][key] = value
    return out


def pool_paths(pool_dir: str, limit: int | None = None) -> list[str]:
    paths = sorted(glob.glob(os.path.join(pool_dir, "*.png")))
    if not paths:
        raise FileNotFoundError(f"no frames in {pool_dir}")
    return paths[:limit] if limit else paths


def labelled_frames(labels_path: str = LABELS, calib_dir: str = CALIB_DIR,
                    takes_path: str = TAKES) -> list[dict]:
    """The designer's labels resolved to something loadable. Generated frames
    are files in the calibration dir; the six takes are tiles of one sheet."""
    with open(labels_path, encoding="utf-8") as fh:
        labels = json.load(fh)["labels"]
    frames = []
    for frame_id, verdict in labels.items():
        if frame_id.startswith("takes_") and "_t" in frame_id:
            sheet, tile = frame_id.rsplit("_", 1)
            frames.append({"id": frame_id, "on": verdict == "on",
                           "path": os.path.join(os.path.dirname(takes_path), f"{sheet}.png"),
                           "crop": tile})
        else:
            frames.append({"id": frame_id, "on": verdict == "on",
                           "path": os.path.join(calib_dir, f"{frame_id}.png"),
                           "crop": None})
    missing = [f["id"] for f in frames if not os.path.exists(f["path"])]
    if missing:
        raise FileNotFoundError(f"{len(missing)} labelled frame(s) not on disk: "
                                f"{', '.join(missing[:5])}")
    return frames


def score_pool(paths: list[str], cfg: dict, doc: dict, log=print,
               ctxs: dict | None = None) -> tuple[list[dict], list[str]]:
    """Score the pool in seed order. Novelty is measured against what this
    step has accepted so far, from an empty set, so the run is self-contained
    and no earlier session's accepted frames leak in.

    `ctxs` maps a frame path to its measurement cache and is kept across steps:
    the mark detector, text regions and novelty features do not depend on the
    thresholds a step moves, so they are measured once per frame and judged
    five times. The accepted set is NOT in the cache; it is rebuilt per step."""
    accepted, rows = [], []
    ctxs = {} if ctxs is None else ctxs
    cfg = copy.deepcopy(cfg)
    cfg["verdict"]["novelty_min"] = 0.0  # measured, not gated; see the note above STEPS
    for i, p in enumerate(paths, start=1):
        r = gate.score_image(gate.load_image(p), cfg, doc, accepted_paths=list(accepted),
                             ctx=ctxs.setdefault(p, {}))
        rows.append({"path": _rel(p), "verdict": r["verdict"], "on_brand": r["on_brand"],
                     "novelty": r["novelty"], "failed_rules": r["failed_rules"],
                     "errored": [e["rule"] for e in r["errored"]]})
        if r["verdict"] == "pass":
            accepted.append(p)
        if i % 25 == 0 or i == len(paths):
            log(f"    {i}/{len(paths)} scored, {len(accepted)} accepted")
    return rows, accepted


def mean_pairwise_novelty(paths: list[str], cfg: dict) -> float | None:
    """How alike the accepted set is to itself: the mean gate-novelty distance
    over every pair. Order-free, so it does not depend on which frame the gate
    happened to see first. None below two frames."""
    if len(paths) < 2:
        return None
    feats = [novelty_mod.features(p, cfg["novelty"]["phash_bits"]) for p in paths]
    ds = [novelty_mod.distance(a, b, cfg) for a, b in itertools.combinations(feats, 2)]
    return float(sum(ds) / len(ds))


def designer_agreement(frames: list[dict], cfg: dict, doc: dict,
                       ctxs: dict | None = None) -> dict:
    """Re-score the labelled frames on this step's brand bars alone (an empty
    accepted set, so novelty is 1.0 and cannot decide the verdict) and count
    where the gate and the designer agree. `ctxs` as in score_pool, keyed on
    the frame id because six of the frames are tiles of one sheet."""
    tp = fp = fn = tn = 0
    ctxs = {} if ctxs is None else ctxs
    for f in frames:
        r = gate.score_image(gate.load_image(f["path"], f["crop"]), cfg, doc,
                             accepted_paths=[], ctx=ctxs.setdefault(f["id"], {}))
        passed = r["verdict"] == "pass"
        if passed and f["on"]:
            tp += 1
        elif passed and not f["on"]:
            fp += 1
        elif not passed and f["on"]:
            fn += 1
        else:
            tn += 1
    n = len(frames)
    return {"n": n, "agreement": (tp + tn) / n if n else 0.0,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


POOL_NOTE = "krea2 turbo, hero-ground@3, seeds 2000 and up"


def run(pool_dir: str = POOL_DIR, steps: int = 5, out_dir: str = OUT_DIR,
        limit: int | None = None, labels_path: str = LABELS,
        calib_dir: str = CALIB_DIR, takes_path: str = TAKES,
        note: str = POOL_NOTE, log=print) -> list[dict]:
    base_cfg = gate.load_config()
    doc = rules_mod.load()
    paths = pool_paths(pool_dir, limit)
    frames = labelled_frames(labels_path, calib_dir, takes_path)
    clip_on = novelty_mod.clip_available()
    log(f"pool: {len(paths)} frames from {_rel(pool_dir)}; {len(frames)} labelled frames; "
        f"novelty {'hash + CLIP' if clip_on else 'HASH ONLY, open_clip not installed'}")

    results = []
    pool_ctxs: dict = {}
    label_ctxs: dict = {}
    for k, thresholds in enumerate(build_steps(steps)):
        t0 = time.monotonic()
        cfg = override(base_cfg, thresholds)
        log(f"step {k}: " + ", ".join(f"{a}={b}" for a, b in thresholds.items()))
        rows, accepted = score_pool(paths, cfg, doc, log, pool_ctxs)
        designer = designer_agreement(frames, cfg, doc, label_ctxs)
        results.append({
            "step": k, "thresholds": thresholds,
            "pool": {"n": len(paths), "accepted_n": len(accepted),
                     "pass_rate": len(accepted) / len(paths),
                     "mean_pairwise_novelty": mean_pairwise_novelty(accepted, cfg),
                     "accepted": [_rel(p) for p in accepted], "rows": rows},
            "designer": designer,
            "seconds": round(time.monotonic() - t0, 1),
        })
        log(f"    pass {100 * results[-1]['pool']['pass_rate']:.0f}%, "
            f"pairwise novelty {_fmt(results[-1]['pool']['mean_pairwise_novelty'])}, "
            f"designer agreement {100 * designer['agreement']:.0f}% "
            f"(fp {designer['fp']}, fn {designer['fn']}), {results[-1]['seconds']}s")

    write_outputs(results, out_dir, pool_dir, clip_on, steps, note)
    return results


def write_outputs(results: list[dict], out_dir: str, pool_dir: str, clip_on: bool,
                  steps: int, note: str = POOL_NOTE) -> None:
    from runs import plot

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump({"pool": _rel(pool_dir), "note": note, "clip": clip_on,
                   "steps": results}, fh, indent=1, ensure_ascii=False)

    shipped = SHIPPED_STEP if steps == len(STEPS) else None
    plot.sweep_figure(results, os.path.join(out_dir, "plot.png"), shipped,
                      caption=_caption(results, clip_on, note))
    loose, tight = results[0], results[-1]
    plot.side_by_side([
        (_sheet_title(loose, "loosest"), plot.contact_sheet(
             [os.path.join(ROOT, p) for p in loose["pool"]["accepted"][:SHEET_CAP]])),
        (_sheet_title(tight, "tightest"), plot.contact_sheet(
             [os.path.join(ROOT, p) for p in tight["pool"]["accepted"][:SHEET_CAP]])),
    ], os.path.join(out_dir, "sheets.png"))
    with open(os.path.join(out_dir, "steps.md"), "w", encoding="utf-8") as fh:
        fh.write(steps_markdown(results, pool_dir, clip_on))


# A loose step accepts most of a 200-frame pool, and a sheet of 165 tiles is a
# texture, not a comparison. The first N in seed order, with the count said.
SHEET_CAP = 30


def _sheet_title(r: dict, word: str) -> str:
    n, total = r["pool"]["accepted_n"], r["pool"]["n"]
    shown = "" if n <= SHEET_CAP else f", first {SHEET_CAP} shown"
    return f"step {r['step']}, {word}: {n} of {total} accepted{shown}"


def steps_markdown(results: list[dict], pool_dir: str, clip_on: bool) -> str:
    lines = [
        "# Sameness run: the five threshold sets",
        "",
        f"Pool: `{_rel(pool_dir)}`, {results[0]['pool']['n']} frames, scored in filename order. "
        f"Novelty: {'perceptual hash and CLIP (ViT-B-32)' if clip_on else 'perceptual hash only'}. "
        "Every other key in `brand/gate.toml` stayed at its shipped value. `verdict.novelty_min` "
        "was set to 0 for pool acceptance: novelty is what this run measures, so it is neither "
        "a knob nor a filter here. Each frame's novelty against the accepted set is still in "
        "`results.json`.",
        "",
        "Reproduce: `python -m runs.pool --count 200` on the 4080, then "
        "`python -m runs.sameness --pool surfaces/_pool --steps 5`.",
        "",
        "## Thresholds, verbatim",
        "",
        "| step | " + " | ".join(f"`{k}`" for k in KNOBS) + " |",
        "|---|" + "---|" * len(KNOBS),
    ]
    for r in results:
        t = r["thresholds"]
        tag = " (shipped)" if r["step"] == SHIPPED_STEP and len(results) == len(STEPS) else ""
        lines.append(f"| {r['step']}{tag} | " + " | ".join(str(t[k]) for k in KNOBS) + " |")
    lines += [
        "",
        "## What each step did",
        "",
        "| step | accepted | pass rate | mean pairwise novelty of accepted | "
        "designer agreement (of 27) | false passes | false fails |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        p, d = r["pool"], r["designer"]
        lines.append(f"| {r['step']} | {p['accepted_n']} of {p['n']} | "
                     f"{100 * p['pass_rate']:.0f}% | {_fmt(p['mean_pairwise_novelty'])} | "
                     f"{d['tp'] + d['tn']} ({100 * d['agreement']:.0f}%) | {d['fp']} | {d['fn']} |")
    lines.append("")
    return "\n".join(lines)


def _caption(results: list[dict], clip_on: bool, note: str) -> str:
    best = max(results, key=lambda r: r["designer"]["agreement"])
    tail = (f"Agreement with the designer peaks at step {best['step']} "
            f"({100 * best['designer']['agreement']:.0f}%)")
    tail += (" and falls past it: a tighter gate is not a better one."
             if best is not results[-1] else
             ", the tightest step: this sweep does not reach past the designer's taste.")
    return (f"Fixed pool of {results[0]['pool']['n']} frames, {note}, re-scored at each step. "
            f"{tail} Novelty is {'hash and CLIP' if clip_on else 'hash only'}.")


def _fmt(x) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def _rel(p: str) -> str:
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def _log(msg: str) -> None:
    """print with a flush, so a run redirected to a file shows progress while it
    is still going: the first 200-frame sweep wrote nothing for half an hour."""
    print(msg, flush=True)


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m runs.sameness")
    p.add_argument("--pool", default=POOL_DIR)
    p.add_argument("--steps", type=int, default=5)
    p.add_argument("--out", default=OUT_DIR)
    p.add_argument("--limit", type=int, help="score only the first N pool frames (smoke test)")
    p.add_argument("--labels", default=LABELS)
    p.add_argument("--calibration", default=CALIB_DIR)
    p.add_argument("--takes", default=TAKES)
    p.add_argument("--note", default=POOL_NOTE,
                   help="what the pool is, for the caption and results.json")
    a = p.parse_args(argv)
    try:
        results = run(a.pool, a.steps, a.out, a.limit, a.labels, a.calibration, a.takes,
                      note=a.note, log=_log)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    agree = [r["designer"]["agreement"] for r in results]
    peak = agree.index(max(agree))
    print(f"wrote {_rel(a.out)}/plot.png, sheets.png, steps.md, results.json; "
          f"designer agreement peaks at step {peak}"
          + ("" if peak < len(results) - 1 else
             "  (AT THE TIGHTEST STEP: the sweep does not reach past the designer's taste)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
