"""What every composed surface shares: tokens into CSS, the render with its
foreground mask, and the gate verdict written beside the output.

A surface is a generated ground under a coded foreground. The ground is the
only thing a model made; the code lays the mark and the type over it from
brand/tokens.json, renders the page through lookdev/render.py, then renders it
once more with the ground hidden to get the foreground as a mask, and hands
the gate both. The gate judges the wash on the wash, not on the letters.
"""
from __future__ import annotations

import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lookdev import render as renderer  # noqa: E402
from pipeline import gate, rules  # noqa: E402

TOKENS = os.path.join(ROOT, "brand", "tokens.json")
MARK = os.path.join(ROOT, "brand", "logo", "slice-mark.svg")
MARK_INK = os.path.join(ROOT, "brand", "logo", "slice-mark-ink.svg")

# The same page with the ground layers hidden and the foreground painted black
# on white is the foreground mask, exactly where the type and the mark landed.
MASK_CSS = (".ground, .veil, .grain, .band { display: none !important; } "
            "html, body, .surface { background: #fff !important; } "
            ".fg { filter: brightness(0) !important; color: #000 !important; "
            "background: #000 !important; -webkit-text-fill-color: #000 !important; "
            "border-color: #000 !important; }")


def load_tokens(path: str = TOKENS) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _rgba(hex_colour: str, alpha: float) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def tokens_css(tokens: dict) -> str:
    """CSS custom properties from the tokens file: every colour by name, the
    flow, the text gradient (token colours, geometry here), paper at the three
    veil opacities, and the type families. Templates use only these."""
    c = {k: v["hex"] for k, v in tokens["color"].items()}
    t = tokens["type"]
    out = [f"--{k}: {v};" for k, v in c.items()]
    out += [
        f"--paper-a70: {_rgba(c['paper'], 0.70)};",
        f"--paper-a12: {_rgba(c['paper'], 0.12)};",
        f"--paper-a76: {_rgba(c['paper'], 0.76)};",
        f"--paper-a88: {_rgba(c['paper'], 0.88)};",
        f"--ink-a10: {_rgba(c['ink'], 0.10)};",
        f"--flow: {tokens['gradient']['flow']['css']};",
        f"--flow-text: {tokens['gradient']['flow_text']['css']};",
        f"--display: \"{t['display']['family']}\", \"Helvetica Neue\", Arial, sans-serif;",
        f"--body: \"{t['display']['family']}\", system-ui, sans-serif;",
        "--mono: \"IBM Plex Mono\", Consolas, monospace;",
    ]
    return " ".join(out)


def fill(template_path: str, values: dict) -> str:
    with open(template_path, encoding="utf-8") as fh:
        page = fh.read()
    for key, value in values.items():
        page = page.replace("{{" + key + "}}", str(value))
    return page


def mask_from_png(path: str):
    """The black-on-white foreground render as a boolean mask, grown by a hair
    so an anti-aliased edge does not count as wash."""
    import cv2
    import numpy as np
    gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    mask = gray < 128
    return cv2.dilate(mask.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)


def render_surface(page: str, out_dir: str, name: str, size: tuple[int, int],
                   scale: int = 1) -> tuple[str, object]:
    """Write <out_dir>/<name>.html, render <name>.png and <name>-foreground.png,
    return the PNG path and the mask."""
    html_path = os.path.join(out_dir, f"{name}.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(page)
    png = os.path.join(out_dir, f"{name}.png")
    renderer.render(html_path, png, size[0], size[1], renderer.chrome(), 4000, scale)
    mask_html = os.path.join(out_dir, f"{name}-foreground.html")
    with open(mask_html, "w", encoding="utf-8") as fh:
        fh.write(page.replace("</style>", MASK_CSS + "</style>"))
    mask_png = os.path.join(out_dir, f"{name}-foreground.png")
    renderer.render(mask_html, mask_png, size[0], size[1], renderer.chrome(), 4000, scale)
    os.remove(mask_html)
    return png, mask_from_png(mask_png)


def copy_ground(ground: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    dest = os.path.join(out_dir, "ground.png")
    if os.path.abspath(ground) != os.path.abspath(dest):
        shutil.copy(ground, dest)
    return dest


def score(png: str, ground: str, mask, extra: dict | None = None,
          score_path: str | None = None) -> dict:
    """The gate's verdict on the composed surface, with its foreground
    declared, plus the verdict on the bare ground. Measured against an empty
    accepted set: a surface is judged on brand here, novelty is the runs' job."""
    doc = rules.load()
    cfg = gate.load_config()
    verdict = gate.score_image(gate.load_image(png), cfg, doc, accepted_paths=[], foreground=mask)
    verdict["ground"] = os.path.relpath(ground, ROOT).replace(os.sep, "/")
    verdict["ground_verdict"] = gate.score_image(gate.load_image(ground), cfg, doc,
                                                 accepted_paths=[])
    verdict["foreground_frac"] = round(float(mask.mean()), 4)
    verdict.update(extra or {})
    with open(score_path or os.path.join(os.path.dirname(png), "score.json"), "w",
              encoding="utf-8") as fh:
        json.dump(verdict, fh, indent=1, ensure_ascii=False)
    return verdict


def report(label: str, v: dict) -> None:
    g = v["ground_verdict"]
    print(f"{label}: {v['verdict']} on-brand {v['on_brand']} failed {v['failed_rules']}")
    print(f"{' ' * len(label)}  ground {g['verdict']} on-brand {g['on_brand']} failed {g['failed_rules']}")
