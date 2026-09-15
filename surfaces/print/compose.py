"""The print one-pager: A4, flat, the ground as a banner band.

    python -m surfaces.print.compose --ground surfaces/_pool/<frame>.png --out surfaces/print/accepted

Flat recipe from brand/rules.md: paper with a hairline border, no glass, no
grain, and the generated ground confined to a band at the top rather than
full bleed. Type is set in points, body 10.5 pt Archivo. Output is
<out>/onepager.pdf (the print file, A4 from the page's own @page rule) and
<out>/onepager.png at 2x A4 CSS pixels for the gate, with its foreground
mask and score.json beside it.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lookdev import render as renderer  # noqa: E402
from surfaces import _lib  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "onepager.html")
A4_CSS = (794, 1123)  # 210 by 297 mm at 96 dpi
SCALE = 2
SITE = "handsel-lovat.vercel.app"
DEFAULT_HEADLINE = "Six pieces of one thing."


def run_numbers() -> dict:
    """The three figures on the page, read from the sameness run and the
    calibration labels rather than typed, so the page cannot drift from them."""
    import json
    res = os.path.join(_lib.ROOT, "runs", "sameness", "results.json")
    labels = os.path.join(_lib.ROOT, "docs", "calibration-labels.json")
    with open(res, encoding="utf-8") as fh:
        steps = json.load(fh)["steps"]
    from runs.sameness import SHIPPED_STEP
    shipped = steps[SHIPPED_STEP]["pool"]
    with open(labels, encoding="utf-8") as fh:
        n_labels = len(json.load(fh)["labels"])
    return {"n_pool": shipped["n"], "n_pass": shipped["accepted_n"], "n_labels": n_labels}


def compose(ground: str, out_dir: str, headline: str = DEFAULT_HEADLINE) -> dict:
    tokens = _lib.load_tokens()
    ground_copy = _lib.copy_ground(ground, out_dir)
    page = _lib.fill(TEMPLATE, {
        "tokens_css": _lib.tokens_css(tokens), "ground": "ground.png",
        "mark": os.path.relpath(_lib.MARK, out_dir).replace(os.sep, "/"),
        "name": tokens["name"], "tagline": tokens["tagline"], "headline": headline,
        "positioning": tokens["positioning"]["is"], "site": SITE, **run_numbers(),
    })
    png, mask = _lib.render_surface(page, out_dir, "onepager", A4_CSS, SCALE)
    renderer.print_pdf(os.path.join(out_dir, "onepager.html"), os.path.join(out_dir, "onepager.pdf"),
                       renderer.chrome(), 4000)
    return _lib.score(png, ground_copy, mask, {"headline": headline, "page": "A4"})


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m surfaces.print.compose")
    p.add_argument("--ground", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--headline", default=DEFAULT_HEADLINE)
    a = p.parse_args(argv)
    v = compose(a.ground, a.out, a.headline)
    _lib.report("onepager", v)
    return 0 if v["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
