"""The social card set: square, story and OG from one ground and one headline.

    python -m surfaces.social.compose --ground surfaces/_pool/<frame>.png --out surfaces/social/accepted
    python -m surfaces.social.compose --ground <png> --out <dir> --headline "..." --only og

One campaign, three crops. The recipe is the hero's (ground, veil, grain,
mark, wordmark in the text gradient, headline in ink, tagline in graphite);
what changes per size is a small table of numbers below, and nothing else.
The safe margin is 5 percent of the short side on every size. Each size gets
its own PNG, foreground mask and score.json in <out>/.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from surfaces import _lib  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template.html")
DEFAULT_HEADLINE = "Six pieces of one thing."

# name: (width, height, mark width, h1, h2, p, gap to h2, gap to p, veil midpoint,
#        ground box top, ground box height, ground focus)
#
# The focus values were not chosen by eye. The gate scored the square at six
# horizontal positions on 2026-09-15: from 0 to 25 percent the crop concentrates
# the magenta orb past the 4 percent flat-accent bar, at 80 percent indigo
# leaves the frame and the wash loses a stop; 40 and 60 pass. The story is
# 9:16 from a 16:9 ground and NO cover crop of it passes: every vertical slice
# either drops a stop or is mostly one orb. So the story carries the ground as
# a horizontal band at its own aspect, faded into the paper above and below,
# which is also what the mark is: a band.
SIZES = {
    "square": (1080, 1080, 200, "150px", "42px", "24px", "18px", "14px", "40%", "0", "100%", "40% 50%"),
    "story":  (1080, 1920, 220, "170px", "50px", "27px", "22px", "16px", "48%", "480px", "700px", "50% 50%"),
    "og":     (1200, 630, 160, "132px", "36px", "21px", "12px", "10px", "34%", "0", "100%", "20% 50%"),
}
BAND_FADE = "linear-gradient(180deg, transparent 0%, black 18%, black 82%, transparent 100%)"


def layout_css(name: str) -> str:
    w, h, mark_w, h1, h2, p, gap_h2, gap_p, veil_mid, top, height, pos = SIZES[name]
    pad = int(round(0.05 * min(w, h)))
    mask = "none" if height == "100%" else BAND_FADE
    return (f"--pad: {pad}px; --mark-w: {mark_w}px; --h1: {h1}; --h2: {h2}; --p: {p}; "
            f"--gap-h2: {gap_h2}; --gap-p: {gap_p}; --veil-mid: {veil_mid}; "
            f"--ground-top: {top}; --ground-h: {height}; --ground-pos: {pos}; --ground-mask: {mask};")


def compose(ground: str, out_dir: str, headline: str = DEFAULT_HEADLINE,
            only: list[str] | None = None) -> dict[str, dict]:
    tokens = _lib.load_tokens()
    ground_copy = _lib.copy_ground(ground, out_dir)
    verdicts = {}
    for name in only or SIZES:
        w, h = SIZES[name][:2]
        page = _lib.fill(TEMPLATE, {
            "tokens_css": _lib.tokens_css(tokens), "layout_css": layout_css(name),
            "size_name": name, "width": w, "height": h, "ground": "ground.png",
            "mark": os.path.relpath(_lib.MARK, out_dir).replace(os.sep, "/"),
            "name": tokens["name"], "headline": headline, "tagline": tokens["tagline"],
        })
        png, mask = _lib.render_surface(page, out_dir, name, (w, h))
        verdicts[name] = _lib.score(png, ground_copy, mask, {"headline": headline, "size": name},
                                    score_path=os.path.join(out_dir, f"{name}.score.json"))
    return verdicts


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m surfaces.social.compose")
    p.add_argument("--ground", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--headline", default=DEFAULT_HEADLINE)
    p.add_argument("--only", nargs="*", choices=sorted(SIZES))
    a = p.parse_args(argv)
    vs = compose(a.ground, a.out, a.headline, a.only)
    for name, v in vs.items():
        _lib.report(name, v)
    return 0 if all(v["verdict"] == "pass" for v in vs.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
