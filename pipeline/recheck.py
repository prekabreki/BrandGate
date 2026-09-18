"""Re-score every surface this repo ships, and fail when one no longer passes.

    python -m pipeline.recheck [--summary FILE] [--emit runs/verdicts.jsonl]

This is the gate pointed at the repo instead of at one frame. CI runs it on
every push, so a commit that lowers the bar turns a check red instead of
sitting there looking accepted. Exit 1 when any shipped surface fails, 0 when
they all pass, 2 when a target cannot be read at all.

Three things make the difference between this and a green rubber stamp.

**Grounds are scored too, not only the composed surfaces.** The print rejected
candidate is the reason: its ground fails `gradient.03`, and the composed
surface passes at 1.00 because the coded foreground covers 88 percent of the
page. A gate that judged only the finished artwork would wave a broken
generation through whenever the type was big enough.

**A composed surface is scored with its foreground mask**, exactly as
`surfaces/_lib.score` scored it when it was accepted, so a verdict here is
comparable to the `score.json` beside it rather than a different measurement
that happens to use the same word. Without the mask the wash check reads the
letters as wash and the number moves for no brand reason.

**The committed verdict is the baseline.** Every row carries what `score.json`
recorded at acceptance, so the table says whether the number moved, not just
whether it still clears the bar. A rule change that drags every surface from
0.99 to 0.76 passes the threshold and is still the drift this repo exists to
catch.

Novelty is measured against an empty accepted set here, which is what
`_lib.score` does: a shipped surface is judged on brand, and novelty is the
runs' question, not this one's.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

from pipeline import gate, rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCEPTED = os.path.join(ROOT, "surfaces", "*", "accepted")
FOREGROUND_SUFFIX = "-foreground.png"


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def mask_from_png(path: str):
    """Imported from the composer rather than copied, so the dilation that
    grows the mask over an anti-aliased edge cannot drift between the code
    that accepted a surface and the code that re-scores it."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from surfaces import _lib
    return _lib.mask_from_png(path)


def targets(pattern: str = ACCEPTED) -> list[dict]:
    """Every PNG a surface ships, with its mask when it has one.

    The discovery rule is a property of the files, not a list to maintain: any
    PNG under `surfaces/*/accepted/` is a target, a `*-foreground.png` is a
    mask and never a target, and a PNG with a mask beside it is scored with it.
    Add a surface and CI picks it up; the list cannot go stale because there
    is no list.
    """
    out = []
    for d in sorted(glob.glob(pattern)):
        for png in sorted(glob.glob(os.path.join(d, "*.png"))):
            if png.endswith(FOREGROUND_SUFFIX):
                continue
            stem = os.path.basename(png)[:-4]
            mask = os.path.join(d, stem + FOREGROUND_SUFFIX)
            out.append({"image": png, "stem": stem,
                        "mask": mask if os.path.exists(mask) else None,
                        "kind": "surface" if os.path.exists(mask) else "ground"})
    return out


def baseline(target: dict) -> dict | None:
    """The verdict recorded when this file was accepted, or None.

    A composed surface reads its own `<stem>.score.json`, falling back to the
    directory's `score.json` for the surfaces that ship one apiece. A ground
    reads the `ground_verdict` of whichever score.json in the directory names
    it, which is how `ground-story.png` finds its own row rather than the
    story surface's."""
    d = os.path.dirname(target["image"])
    if target["kind"] == "surface":
        for name in (f"{target['stem']}.score.json", "score.json"):
            p = os.path.join(d, name)
            if os.path.exists(p):
                return _read(p)
        return None
    want = rel(target["image"])
    for p in sorted(glob.glob(os.path.join(d, "*score.json"))):
        doc = _read(p)
        if doc and doc.get("ground") == want:
            return doc.get("ground_verdict")
    return None


def _read(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def score_target(target: dict, cfg: dict, doc: dict) -> dict:
    img = gate.load_image(target["image"])
    fg = mask_from_png(target["mask"]) if target["mask"] else None
    r = gate.score_image(img, cfg, doc, accepted_paths=[], foreground=fg)
    r["image"] = rel(target["image"])
    r["kind"] = target["kind"]
    was = baseline(target) or {}
    r["was"] = {"verdict": was.get("verdict"), "on_brand": was.get("on_brand"),
                "scored": (was.get("counts") or {}).get("scored")}
    return r


def run(pattern: str = ACCEPTED) -> list[dict]:
    cfg = gate.load_config()
    doc = rules.load()
    return [score_target(t, cfg, doc) for t in targets(pattern)]


def _delta(r: dict) -> str:
    """How far this surface moved since it was accepted.

    On-brand is the mean of the rules that could be measured, so two means
    taken over different rule sets are not a difference, they are two
    different questions. When cairo is absent the six mark and motif rules
    error out and every surface reads about 0.02 lower, which looks exactly
    like a gentle brand drift and is nothing of the kind. Say so instead of
    printing the subtraction."""
    now, was = r["on_brand"], r["was"]["on_brand"]
    if now is None or was is None:
        return "n/a"
    n_now, n_was = r["counts"]["scored"], r["was"]["scored"]
    if n_was is not None and n_now != n_was:
        return f"{n_was}->{n_now} rules, not comparable"
    d = now - was
    return "same" if abs(d) < 5e-5 else f"{d:+.4f}"


def table(rows: list[dict]) -> str:
    """The Step Summary: one line per file, the reason for every failure.

    A reviewer reading a red check needs the file and the rule in the first
    screen, so the failures are named again underneath rather than left to be
    picked out of the table."""
    head = ["| | file | on-brand | at acceptance | moved | novelty | failed |",
            "|---|---|---|---|---|---|---|"]
    for r in rows:
        ob = "n/a" if r["on_brand"] is None else f"{r['on_brand']:.4f}"
        was = r["was"]["on_brand"]
        wass = "not recorded" if was is None else f"{was:.4f}"
        tick = {"pass": "ok", "fail": "FAIL"}.get(r["verdict"], "unscored")
        failed = ", ".join(f"`{x}`" for x in r["failed_rules"]) or ""
        head.append(f"| {tick} | `{r['image']}` | {ob} | {wass} | {_delta(r)} "
                    f"| {r['novelty']:.2f} | {failed} |")

    bad = [r for r in rows if r["verdict"] != "pass"]
    out = ["## brand gate", ""]
    out.append(f"**{len(rows) - len(bad)} of {len(rows)} shipped surfaces pass the gate.**"
               if not bad else
               f"**{len(bad)} of {len(rows)} shipped surfaces no longer pass the gate.**")
    out += ["", *head, ""]
    if bad:
        out.append("### what failed")
        for r in bad:
            out.append(f"- `{r['image']}`, verdict {r['verdict']}:")
            for b in r["breakdown"]:
                if not b["passed"]:
                    out.append(f"  - `{b['rule']}` scored {b['score']:.2f}: {b['reason']}")
            if r["was"]["verdict"] == "pass":
                out.append("  - this one passed when it was accepted, so something moved "
                           "under it: a rule, a threshold, or the file itself.")
    errored = [e for r in rows for e in r["errored"]]
    if errored:
        # A check that cannot run is not a check that passed. cairo missing on
        # the runner would silently retire the mark rules (#17), so the
        # summary says so above the fold rather than in a log.
        deps = sorted({e["dependency"] for e in errored if e.get("dependency")})
        out += ["", "### rules that could not run",
                f"{len(errored)} rule evaluation(s) errored and were not scored."
                + (f" Missing: {', '.join(deps)}." if deps else "")]
        for e in errored[:6]:
            out.append(f"- `{e['rule']}` ({e['check']}): {e['error']}")
    return "\n".join(out) + "\n"


def render(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        ob = " n/a " if r["on_brand"] is None else f"{r['on_brand']:.4f}"
        mark = {"pass": "PASS", "fail": "FAIL"}.get(r["verdict"], "UNSCORED")
        lines.append(f"{mark:<8} {ob}  {_delta(r):>8}  {r['image']}"
                     + (f"  failed {r['failed_rules']}" if r["failed_rules"] else ""))
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m pipeline.recheck")
    p.add_argument("--summary", metavar="FILE",
                   help="append the markdown table here (GITHUB_STEP_SUMMARY)")
    p.add_argument("--emit", metavar="JSONL",
                   help="append one verdict row per file, for the connector")
    p.add_argument("--json", action="store_true", help="full results to stdout")
    p.add_argument("--allow-missing-deps", action="store_true",
                   help="warn instead of failing when a check cannot run at all")
    p.add_argument("--glob", default=ACCEPTED, help=argparse.SUPPRESS)
    a = p.parse_args(argv)

    found = targets(a.glob)
    if not found:
        print(f"ERROR: no surfaces found under {a.glob}", file=sys.stderr)
        return 2
    try:
        rows = run(a.glob)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(json.dumps(rows, indent=2, ensure_ascii=False) if a.json else render(rows))
    # One warning for the run, not one per file: nine copies of the same cairo
    # error is how a real second failure gets scrolled off the screen.
    errored = {(e["rule"], e["error"]) for r in rows for e in r["errored"]}
    if errored:
        deps = sorted({d for r in rows for d in r["missing_dependencies"]})
        print(f"WARNING: {len(errored)} rule(s) errored on every file and were not scored "
              f"({', '.join(sorted(r for r, _ in errored))})"
              + (f"; missing {', '.join(deps)}" if deps else ""), file=sys.stderr)
        print(f"  {sorted(errored)[0][1][:200]}", file=sys.stderr)
    if a.summary:
        with open(a.summary, "a", encoding="utf-8") as fh:
            fh.write(table(rows))
    if a.emit:
        for r, t in zip(rows, found):
            gate.emit_verdict(r, t["image"], None, a.emit)

    bad = [r for r in rows if r["verdict"] != "pass"]
    if bad:
        print(f"\n{len(bad)} of {len(rows)} shipped surfaces no longer pass the gate.",
              file=sys.stderr)
        return 1
    # A gate missing six of its rules is not a gate that passed. Exit 2 keeps
    # the two failures apart: 1 is the brand, 2 is this tool. In CI either one
    # is red, and the summary says which, because a rotated mark sailing
    # through a cairo-less runner is the exact silence #17 was filed about.
    if errored and not a.allow_missing_deps:
        print("\nThe gate could not run every check, so a pass here is not a pass. "
              "Install the missing dependency, or pass --allow-missing-deps to say "
              "you meant it.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
