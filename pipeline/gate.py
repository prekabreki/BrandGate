"""Score a frame against the brand.

    python -m pipeline.gate score <image> [--crop t3] [--json]

Two axes. On-brand is the weighted agreement of every check that could run.
Novelty is distance from what has already been accepted. A frame passes when it
clears both bars in brand/gate.toml.

A check that raises does not fail the frame and does not stop the run: that
rule becomes `errored` with its exception recorded, and the CLI says so on
stderr. The alternative is a gate that dies on an odd PNG, and a gate that dies
gets switched off. Errored is its own outcome, never folded into not-applicable
or manual: a missing library once read as "no mark in the frame" (#17).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
import traceback

import numpy as np

from pipeline import novelty as novelty_mod
from pipeline import rules as rules_mod
from pipeline.checks import Finding, get as get_check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE_TOML = os.path.join(ROOT, "brand", "gate.toml")

# The takes contact sheets are a grid of labelled tiles, three across and two
# down. --crop t3 pulls one out so a single take can be scored on its own,
# which is what the tiles are for; scoring the whole sheet would measure the
# sheet's layout instead. Tiles number left to right, top row first.
TAKES_GRID = (2, 3)


def load_config(path: str | None = None) -> dict:
    with open(path or GATE_TOML, "rb") as fh:
        return tomllib.load(fh)


def load_image(path: str, crop: str | None = None) -> np.ndarray:
    import cv2
    raw = cv2.imread(path, cv2.IMREAD_COLOR)
    if raw is None:
        raise FileNotFoundError(f"cannot read an image from {path}")
    img = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
    if crop:
        img = crop_tile(img, crop)
    return img


def crop_tile(img: np.ndarray, spec: str) -> np.ndarray:
    """`t3` is the third tile of a takes sheet, reading left to right."""
    s = spec.strip().lower()
    if not s.startswith("t") or not s[1:].isdigit():
        raise ValueError(f"crop must look like t1, t2, t3; got {spec!r}")
    n = int(s[1:]) - 1
    rows, cols = TAKES_GRID
    if not 0 <= n < rows * cols:
        raise ValueError(f"{spec!r} is outside a {rows}x{cols} sheet")
    h, w = img.shape[0] // rows, img.shape[1] // cols
    r, c = divmod(n, cols)
    return img[r * h:(r + 1) * h, c * w:(c + 1) * w]


def score_image(img: np.ndarray, cfg: dict | None = None,
                rules_doc: dict | None = None,
                accepted_glob: str | None = None,
                accepted_paths: list[str] | None = None,
                ctx: dict | None = None) -> dict:
    """`accepted_paths`, when given, is the accepted set novelty is measured
    against, instead of whatever `accepted_glob` matches on disk.

    `ctx` is the frame's measurement cache. Checks share their expensive
    measurements through it (the mark detector, text regions, the novelty
    features), each keyed on the config section it read. A caller scoring the
    same frame at several threshold sets, as the sameness sweep does, hands
    in one ctx per frame and pays for each measurement once; the verdicts are
    identical to scoring cold, because thresholds are applied after the memo.
    Left as None, the cache lives and dies with this call."""
    cfg = cfg or load_config()
    doc = rules_doc or rules_mod.load()
    if ctx is None:
        ctx = {}

    findings, errored, manual = [], [], []
    for rule in doc["rules"]:
        if rule["check"] == "manual":
            manual.append(rule["id"])
            continue
        fn = get_check(rule["check"])
        if fn is None:
            errored.append(_errored(rule, LookupError(f"no check named {rule['check']!r}")))
            continue
        try:
            findings.append(fn(img, rule, cfg, ctx))
        except Exception as e:
            errored.append(_errored(rule, e, traceback.format_exc(limit=3)))

    # Only rules that had something to measure count toward the score. A frame
    # with no type and no mark is not 100 percent on-brand, it is unjudged, and
    # the verdict says so rather than quietly awarding a pass for emptiness.
    scored = [f for f in findings if f.applicable]
    skipped = [f for f in findings if not f.applicable]
    failed = [f for f in scored if not f.passed]
    nov = novelty_mod.score(img, cfg, accepted_glob, paths=accepted_paths, ctx=ctx)

    if not scored:
        on_brand = None
        verdict = "unscored"
    else:
        on_brand = float(np.mean([f.score for f in scored]))
        verdict = ("pass" if (on_brand >= cfg["verdict"]["on_brand_min"]
                              and nov["novelty"] >= cfg["verdict"]["novelty_min"]
                              and not failed) else "fail")

    return {
        "verdict": verdict,
        "on_brand": None if on_brand is None else round(on_brand, 4),
        "novelty": round(nov["novelty"], 4),
        "thresholds": cfg["verdict"],
        "failed_rules": [f.rule_id for f in failed],
        "breakdown": [
            {"rule": f.rule_id, "check": f.check, "score": round(f.score, 4),
             "passed": f.passed, "reason": f.reason, "detail": f.detail}
            for f in scored],
        "not_applicable": [
            {"rule": f.rule_id, "check": f.check, "reason": f.reason}
            for f in skipped],
        "novelty_detail": nov,
        "manual": manual,
        "errored": errored,
        "missing_dependencies": sorted({e["dependency"] for e in errored
                                        if e.get("dependency")}),
        "counts": {"scored": len(scored), "failed": len(failed),
                   "not_applicable": len(skipped), "manual": len(manual),
                   "errored": len(errored)},
    }


def _errored(rule: dict, e: BaseException, tb: str | None = None) -> dict:
    """One errored rule. `dependency` is set when the check itself named the
    library it could not load, so the CLI can say which one."""
    entry = {"rule": rule["id"], "check": rule["check"],
             "error": f"{type(e).__name__}: {e}",
             "detail": {"traceback": tb} if tb else {}}
    dep = getattr(e, "dependency", None)
    if dep:
        entry["dependency"] = dep
    return entry


def _warn_errored(r: dict) -> str | None:
    """The one-line stderr warning for a result with errored rules, or None."""
    errored = r["errored"]
    if not errored:
        return None
    rules_ = ", ".join(e["rule"] for e in errored)
    deps = r["missing_dependencies"]
    if deps:
        first = next(e["error"] for e in errored if e.get("dependency"))
        head = f"missing dependency {', '.join(deps)}; {first}"
    else:
        head = errored[0]["error"]
    # cffi's load error is six lines long; the full text is in the JSON, and a
    # warning that scrolls the terminal is a warning that does not get read.
    flat = " ".join(head.split())
    if len(flat) > 240:
        flat = flat[:237] + "..."
    return (f"WARNING: {len(errored)} rule(s) errored and were not scored "
            f"({rules_}): {flat}")


def score_path(path: str, crop: str | None = None, **kw) -> dict:
    result = score_image(load_image(path, crop), **kw)
    result["image"] = os.path.relpath(path, ROOT).replace(os.sep, "/")
    if crop:
        result["crop"] = crop
    return result


def _render(r: dict) -> str:
    mark = {"pass": "PASS", "fail": "FAIL"}.get(r["verdict"], "UNSCORED")
    ob = "  n/a" if r["on_brand"] is None else f"{r['on_brand']:.2f}"
    c = r["counts"]
    lines = [f"{mark}  on-brand {ob}  novelty {r['novelty']:.2f}"
             f"  ({c['scored']} scored, {c['not_applicable']} n/a, "
             f"{c['manual']} manual, {c['errored']} errored)"]
    for b in sorted(r["breakdown"], key=lambda d: (d["passed"], d["score"])):
        tick = " " if b["passed"] else "x"
        lines.append(f" {tick} {b['rule']:<14} {b['score']:.2f}  {b['reason']}")
    for b in r["not_applicable"]:
        lines.append(f" - {b['rule']:<14}  --   {b['reason']}")
    for e in r["errored"]:
        lines.append(f" ! {e['rule']:<14}  --   errored, not scored: {e['error']}")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m pipeline.gate")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score", help="score one image")
    s.add_argument("image")
    s.add_argument("--crop", help="tile of a takes sheet, e.g. t3")
    s.add_argument("--json", action="store_true", help="machine-readable output")
    s.add_argument("--accepted", help="glob for the accepted set")
    a = p.parse_args(argv)

    try:
        r = score_path(a.image, a.crop, accepted_glob=a.accepted)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    warning = _warn_errored(r)
    if warning:
        print(warning, file=sys.stderr)
    print(json.dumps(r, indent=2, ensure_ascii=False) if a.json else _render(r))
    return 0 if r["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
