"""The marketing hero: a generated ground under a coded foreground.

    python -m surfaces.hero.compose --ground surfaces/_pool/<frame>.png --out surfaces/hero/accepted
    python -m surfaces.hero.compose --ground <png> --out <dir> --headline "..."

The ground is the only thing a model made. Everything on top of it is code:
the mark is the SVG, the wordmark sits in the text gradient, the headline is
ink, the tagline graphite, and the paper veil and grain are the same two
layers take T1 used. Every colour the template uses comes from
brand/tokens.json through surfaces/_lib.tokens_css; the template holds
geometry only.

Output is <out>/hero.png at 1600 by 900, <out>/ground.png (copied so the pair
survives the pool being regenerated), <out>/hero-foreground.png (the declared
foreground the gate was handed) and <out>/score.json.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from surfaces import _lib  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template.html")
SIZE = (1600, 900)
DEFAULT_HEADLINE = "Six pieces of one thing."


def compose(ground: str, out_dir: str, headline: str = DEFAULT_HEADLINE) -> dict:
    tokens = _lib.load_tokens()
    ground_copy = _lib.copy_ground(ground, out_dir)
    page = _lib.fill(TEMPLATE, {
        "tokens_css": _lib.tokens_css(tokens), "width": SIZE[0], "height": SIZE[1],
        "ground": "ground.png", "mark": os.path.relpath(_lib.MARK, out_dir).replace(os.sep, "/"),
        "name": tokens["name"], "headline": headline, "tagline": tokens["tagline"],
    })
    png, mask = _lib.render_surface(page, out_dir, "hero", SIZE)
    return _lib.score(png, ground_copy, mask, {"headline": headline})


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m surfaces.hero.compose")
    p.add_argument("--ground", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--headline", default=DEFAULT_HEADLINE)
    a = p.parse_args(argv)
    v = compose(a.ground, a.out, a.headline)
    _lib.report("hero", v)
    return 0 if v["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
