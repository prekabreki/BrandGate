"""The marketing hero: a generated ground under a coded foreground.

    python -m surfaces.hero.compose --ground surfaces/_pool/<frame>.png --out surfaces/hero/accepted
    python -m surfaces.hero.compose --ground <png> --out <dir> --headline "..."

The ground is the only thing a model made. Everything on top of it is code:
the mark is the SVG, the wordmark sits in the text gradient, the headline is
ink, the tagline graphite, and the paper veil and grain are the same two
layers take T1 used. Every colour the template uses is written here from
brand/tokens.json into CSS variables; the template holds geometry only.

Output is <out>/hero.png at 1600 by 900, <out>/ground.png (the ground it was
built on, copied so the pair survives the pool being regenerated) and
<out>/score.json, the gate's verdict on the composed hero. The verdict is
measured against an empty accepted set, because the first surface has
nothing to be a repeat of.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from lookdev import render as renderer  # noqa: E402
from pipeline import gate, rules  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template.html")
TOKENS = os.path.join(ROOT, "brand", "tokens.json")
MARK = os.path.join(ROOT, "brand", "logo", "slice-mark.svg")
SIZE = (1600, 900)
DEFAULT_HEADLINE = "Six pieces of one thing."


def _hex_to_rgba(hex_colour: str, alpha: float) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def tokens_css(tokens: dict) -> str:
    """CSS custom properties from the tokens file. The text gradient is the
    ink-to-indigo-to-magenta ramp the takes use; its stops are token colours,
    its geometry is here."""
    c = {k: v["hex"] for k, v in tokens["color"].items()}
    t = tokens["type"]
    out = [f"--{k}: {v};" for k, v in c.items()]
    out += [
        f"--paper-a70: {_hex_to_rgba(c['paper'], 0.70)};",
        f"--paper-a12: {_hex_to_rgba(c['paper'], 0.12)};",
        f"--paper-a76: {_hex_to_rgba(c['paper'], 0.76)};",
        f"--flow: {tokens['gradient']['flow']['css']};",
        f"--flow-text: linear-gradient(120deg, {c['ink']} 10%, {c['indigo']} 55%, {c['magenta']} 95%);",
        f"--display: \"{t['display']['family']}\", \"Helvetica Neue\", Arial, sans-serif;",
        f"--body: \"{t['display']['family']}\", system-ui, sans-serif;",
        "--mono: \"IBM Plex Mono\", Consolas, monospace;",
    ]
    return " ".join(out)


MASK_CSS = (".ground, .veil, .grain { display: none !important; } "
            "body, .hero { background: #fff !important; } "
            ".mark, h1, h2, p { filter: brightness(0) !important; color: #000 !important; "
            "background: #000 !important; -webkit-text-fill-color: #000 !important; }")


def _mask_from_png(path: str):
    import cv2
    import numpy as np
    gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    mask = gray < 128
    # Grow the mask by a hair so an anti-aliased edge does not count as wash.
    return cv2.dilate(mask.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)


def compose(ground: str, out_dir: str, headline: str = DEFAULT_HEADLINE,
            tokens_path: str = TOKENS) -> dict:
    with open(tokens_path, encoding="utf-8") as fh:
        tokens = json.load(fh)
    os.makedirs(out_dir, exist_ok=True)
    ground_copy = os.path.join(out_dir, "ground.png")
    if os.path.abspath(ground) != os.path.abspath(ground_copy):
        shutil.copy(ground, ground_copy)

    html_path = os.path.join(out_dir, "hero.html")
    with open(TEMPLATE, encoding="utf-8") as fh:
        page = fh.read()
    for key, value in {
        "tokens_css": tokens_css(tokens), "width": SIZE[0], "height": SIZE[1],
        "ground": "ground.png", "mark": os.path.relpath(MARK, out_dir).replace(os.sep, "/"),
        "name": tokens["name"], "headline": headline,
        "tagline": tokens["tagline"],
    }.items():
        page = page.replace("{{" + key + "}}", str(value))
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(page)

    hero_png = os.path.join(out_dir, "hero.png")
    renderer.render(html_path, hero_png, SIZE[0], SIZE[1], renderer.chrome(), 4000)

    # The same page with the ground layers hidden and the foreground painted
    # black on white is the foreground mask, exactly where the type and the
    # mark landed. The gate is handed it so the wash is judged on the wash.
    mask_html = os.path.join(out_dir, "foreground.html")
    with open(mask_html, "w", encoding="utf-8") as fh:
        fh.write(page.replace("</style>", MASK_CSS + "</style>"))
    mask_png = os.path.join(out_dir, "foreground.png")
    renderer.render(mask_html, mask_png, SIZE[0], SIZE[1], renderer.chrome(), 4000)
    os.remove(mask_html)
    foreground = _mask_from_png(mask_png)

    doc = rules.load()
    cfg = gate.load_config()
    verdict = gate.score_image(gate.load_image(hero_png), cfg, doc, accepted_paths=[],
                               foreground=foreground)
    verdict["foreground_frac"] = round(float(foreground.mean()), 4)
    verdict["ground"] = os.path.relpath(ground, ROOT).replace(os.sep, "/")
    verdict["ground_verdict"] = gate.score_image(gate.load_image(ground_copy), cfg, doc,
                                                 accepted_paths=[])
    verdict["headline"] = headline
    with open(os.path.join(out_dir, "score.json"), "w", encoding="utf-8") as fh:
        json.dump(verdict, fh, indent=1, ensure_ascii=False)
    return verdict


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m surfaces.hero.compose")
    p.add_argument("--ground", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--headline", default=DEFAULT_HEADLINE)
    a = p.parse_args(argv)
    v = compose(a.ground, a.out, a.headline)
    g = v["ground_verdict"]
    print(f"hero: {v['verdict']} on-brand {v['on_brand']} failed {v['failed_rules']}")
    print(f"ground: {g['verdict']} on-brand {g['on_brand']} failed {g['failed_rules']}")
    return 0 if v["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
