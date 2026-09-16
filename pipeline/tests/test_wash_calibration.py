"""Score the designer-labelled set with the wash check in place.

This is the held-out fixture the thresholds in brand/gate.toml were set from,
so it is a regression test against the labels, not a proof of generality. The
next generated batch is the honest test; this one stops the numbers drifting.

Run with -s to see the confusion matrix and the per-axis sweep.
"""
from __future__ import annotations

import glob
import json
import os

import pytest

from pipeline import gate, rules

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LABELS = os.path.join(ROOT, "docs", "calibration-labels.json")
CALIB = os.path.join(ROOT, "surfaces", "_calibration")
TAKES = os.path.join(ROOT, "lookdev", "archive", "takes_02.png")

# The floor is re-derived on every calibration pass, on the set as it stands, never
# lowered to make a change fit. Second pass, 2026-09-15: 24 of 27, two false passes.
# Late that day the designer labelled the shipped hero pair and the gate was wrong on
# both: 24 of 29, three false passes. Third pass, 2026-09-16 (#22, docs/calibration.md):
# nine labels from the day's review joined the set (38), the dull-wash axis, the
# thin-wash fault, the flatness test on colour.03 and two bars moved by the procedure
# took it from 25 of 38 with eight false passes to 31 of 38 with six. Then the designer
# accepted the five composed surfaces on the mesh ground and a portrait mesh ground (44),
# dark_chroma_max moved to 56.2 by the procedure, and the set stands at 36 of 44. The
# two false fails are the novelty bar on mesh near-twins, not a brand rule. The six false
# passes are the frames whose fault no axis measures yet: four say "too much dark on the
# left" or "a big splotch of black", which is the dark-mass axis waiting on a relabel
# decision recorded in the doc; two say "not enough bleed" in a way edge_p99 does not see.
MIN_AGREE = 36
MAX_FALSE_PASS = 6


def _labelled():
    with open(LABELS, encoding="utf-8") as fh:
        labels = json.load(fh)["labels"]
    files = {os.path.splitext(os.path.basename(p))[0]: p
             for p in glob.glob(os.path.join(CALIB, "*.png"))}
    rows = []
    for tid, lab in labels.items():
        if tid.startswith("takes_02_t"):
            rows.append((tid, lab, TAKES, tid.rsplit("_", 1)[1]))
        elif tid.startswith("surface:"):
            # A composed surface the designer accepted as shipped (#22, 2026-09-16). It is
            # scored the way the composer scores it: with its declared foreground, so the
            # wash is judged on the wash and not on the wordmark. The stem is repo-relative.
            stem = os.path.join(ROOT, tid[len("surface:"):])
            if os.path.exists(stem + ".png") and os.path.exists(stem + "-foreground.png"):
                rows.append((tid, lab, stem + ".png", "surface"))
        elif tid in files:
            rows.append((tid, lab, files[tid], None))
    return rows


@pytest.fixture(scope="module")
def scored():
    rows = _labelled()
    gen = [r for r in rows if r[3] is None]
    if len(gen) < 15:
        pytest.skip(f"only {len(gen)} labelled frames on disk under {CALIB}; "
                    "regenerate with `python -m pipeline.calibrate batch --count 30`")
    out = []
    for tid, lab, path, crop in rows:
        if crop == "surface":
            from surfaces import _lib
            mask = _lib.mask_from_png(path[:-4] + "-foreground.png")
            r = gate.score_image(gate.load_image(path), gate.load_config(), rules.load(),
                                 accepted_paths=[], foreground=mask)
        else:
            r = gate.score_path(path, crop)
        washrow = next((b for b in r["breakdown"] if b["check"] == "wash"), None)
        out.append({"id": tid, "label": lab, "verdict": r["verdict"],
                    "failed": r["failed_rules"], "wash": washrow})
    return out


def _matrix(rows):
    m = {("on", "pass"): 0, ("on", "fail"): 0, ("off", "pass"): 0, ("off", "fail"): 0}
    for r in rows:
        m[(r["label"], r["verdict"])] += 1
    return m


def test_agreement_with_the_designer(scored):
    m = _matrix(scored)
    agree = m[("on", "pass")] + m[("off", "fail")]
    print(f"\n              designer on   designer off\n"
          f"  gate pass   {m[('on', 'pass')]:>11}   {m[('off', 'pass')]:>12}\n"
          f"  gate fail   {m[('on', 'fail')]:>11}   {m[('off', 'fail')]:>12}\n"
          f"  agree {agree}/{len(scored)}")
    for r in scored:
        if (r["label"] == "on") != (r["verdict"] == "pass"):
            w = r["wash"] or {}
            print(f"  disagree: {r['id'][:32]:<32} label={r['label']} gate={r['verdict']} "
                  f"failed={','.join(r['failed']) or '-'} wash={w.get('reason', 'n/a')[:70]}")
    assert agree >= MIN_AGREE, f"agreement fell to {agree}/{len(scored)}"
    assert m[("off", "pass")] <= MAX_FALSE_PASS


def test_every_take_still_passes(scored):
    takes = [r for r in scored if r["id"].startswith("takes_02")]
    assert takes and all(r["verdict"] == "pass" for r in takes), \
        [(r["id"], r["failed"]) for r in takes if r["verdict"] != "pass"]


def test_wash_measurements_printed_for_the_sweep(scored):
    """Not an assertion, a record: the per-frame numbers the thresholds came
    from, so the toml comments can be checked against the data."""
    print("\n  id                               label  dark_chroma  edge_p99  min stop share  dark_mass  L_p02  chroma_mean")
    for r in sorted(scored, key=lambda r: r["label"]):
        w = r["wash"]
        if not w or "dark_chroma" not in w.get("detail", {}):
            continue
        d = w["detail"]
        print(f"  {r['id'][:32]:<32} {r['label']:<5}  {d['dark_chroma']:>10.1f}  "
              f"{d['edge_p99']:>8.1f}  {min(d['stop_share'].values()):>7.3f}  "
              f"{d.get('dark_mass', 0):>9.4f}  {d.get('L_p02', 0):>5.1f}  {d.get('chroma_mean', 0):>6.1f}")
