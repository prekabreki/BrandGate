"""Generate the review UI's brand values from the repo's own tokens.

    python handsgate/scripts/tokens-to-tailwind.py

Reads `brand/tokens.json`, the same file the gate, the brand sheet and the one-pager
read, and writes `handsgate/src/brand/tokens.generated.css`. `tokens.css` imports it
and adds the things a token file cannot hold: which token is the ground in each theme,
the night overrides, and the surface primitives.

Tailwind v4 here is CSS-first, so there is no `tailwind.config.ts` to generate into.
The acceptance line on #5 still holds either way: no component states a colour, a font
or a radius of its own. Change a value in tokens.json, run this, and the UI follows,
exactly as the sheet and the page do.

The split is deliberate. Everything below is a value that exists in tokens.json and is
therefore generated. Anything you cannot find in tokens.json is a UI decision and lives
in tokens.css by hand, where it is reviewable as a decision rather than hidden as data.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOKENS = os.path.join(ROOT, "brand", "tokens.json")
OUT = os.path.join(ROOT, "handsgate", "src", "brand", "tokens.generated.css")

HEADER = """/*
 * GENERATED FILE. Do not edit.
 *
 * Written by handsgate/scripts/tokens-to-tailwind.py from brand/tokens.json,
 * the same source the gate, the brand sheet and the one-pager read. Edit the
 * token there and run the script; editing this file is how the UI starts
 * disagreeing with the brand it is supposed to be reviewing.
 */
"""


def stack(family: str, fallback: str) -> str:
    return f'"{family}", {fallback}'


def build(d: dict) -> str:
    color = d["color"]
    type_ = d["type"]
    grad = d["gradient"]
    mark = d["mark"]
    fb = type_["fallback"]

    lines = [HEADER, ":root {", "  /* palette, every hex from brand/tokens.json */"]
    for name, spec in color.items():
        lines.append(f"  --hg-{name}: {spec['hex'].lower()}; /* {spec['role']} */")

    lines += ["", "  /* gradients: the flow, its night variant, the text cut and the ground */"]
    lines.append(f"  --hg-flow-base: {grad['flow']['css']};")
    lines.append(f"  --hg-flow-night-base: {grad['flow_night']['css']};")
    for key, var in (("flow_text", "--hg-flow-text-base"), ("ground", "--hg-ground-wash")):
        spec = grad.get(key)
        css = spec.get("css") if isinstance(spec, dict) else spec
        if css:
            lines.append(f"  {var}: {css};")

    lines += ["", "  /* type: families and the metrics the display face is drawn at */"]
    lines.append(f"  --hg-font-display: {stack(type_['display']['family'], fb['display'])};")
    lines.append(f"  --hg-font-body: {stack(type_['body']['family'], fb['body'])};")
    lines.append(f"  --hg-font-mono: {stack(type_['mono']['family'], 'ui-monospace, monospace')};")
    lines.append(f"  --hg-display-weight: {type_['display']['weight']};")
    lines.append(f"  --hg-display-tracking: {type_['display']['tracking_em']}em;")
    lines.append(f"  --hg-body-weight: {type_['body']['weight']};")
    lines.append(f"  --hg-body-size: {type_['body']['size_px']}px;")
    lines.append(f"  --hg-body-leading: {type_['body']['line_height']};")

    lines += ["", "  /* mark geometry, so a lockup here cannot drift from the sheet */"]
    lines.append(f"  --hg-mark-aspect: {mark['aspect']};")
    lines.append(f"  --hg-mark-seam: {mark['seam']};")
    if "lockup" in mark:
        lines.append(f"  --hg-lockup-left: {mark['lockup']['text_left_frac']};")
    if "min_size_px" in d.get("rules", {}):
        lines.append(f"  --hg-mark-min: {d['rules']['min_size_px']}px;")
    lines.append("}")

    lines += ["", "/* Night takes the flow's own night stops, not a filtered copy of the day one. */",
              ".dark {", "  --hg-flow-base: var(--hg-flow-night-base);", "}", ""]
    return "\n".join(lines)


def copy_mark() -> None:
    """The mark itself, day and night, copied from brand/logo rather than redrawn.

    The first build shipped a placeholder: a 3:1 band painted with the flow. It was
    honest about being one, but a brand tool showing an approximation of its own mark
    in its own header is the exact failure the gate exists to catch."""
    src_dir = os.path.join(ROOT, "brand", "logo")
    dst_dir = os.path.join(ROOT, "handsgate", "public", "brand")
    os.makedirs(dst_dir, exist_ok=True)
    for name in ("slice-mark.svg", "slice-mark-night.svg"):
        src = os.path.join(src_dir, name)
        if not os.path.exists(src):
            raise SystemExit(f"missing {os.path.relpath(src, ROOT)}")
        with open(src, "rb") as fh:
            blob = fh.read()
        with open(os.path.join(dst_dir, name), "wb") as fh:
            fh.write(blob)
        print(f"copied brand/logo/{name} -> handsgate/public/brand/{name}")


# The eight surface thumbnails and the one run figure that exists, from the real
# renders the gate scored. The first build shipped soft SVG gradients in these slots,
# labelled HERO, SOCIAL, PRINT, MOTION and captioned with real scores, which is a
# picture of a surface that was never made.
SURFACES = [
    ("surfaces/hero/accepted/hero.png", "hero-accepted"),
    ("surfaces/hero/rejected/hero.png", "hero-rejected"),
    ("surfaces/social/accepted/og.png", "social-accepted"),
    ("surfaces/social/rejected/og.png", "social-rejected"),
    ("surfaces/print/accepted/onepager.png", "print-accepted"),
    ("surfaces/print/rejected/onepager.png", "print-rejected"),
    ("surfaces/motion/out/poster.jpg", "motion-accepted"),
    ("surfaces/motion/out/refused/poster.jpg", "motion-rejected"),
]
RUNS = [("runs/sameness/plot.png", "sameness")]


def copy_renders() -> None:
    """Cut the real renders down to thumbnails the app can load."""
    from PIL import Image

    for rel, stem, dest, width in (
        [(r, s, "surfaces", 720) for r, s in SURFACES]
        + [(r, s, "runs", 600) for r, s in RUNS]
    ):
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            raise SystemExit(f"missing {rel}; render it before syncing the UI")
        out_dir = os.path.join(ROOT, "handsgate", "public", dest)
        os.makedirs(out_dir, exist_ok=True)
        im = Image.open(src).convert("RGB")
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        out = os.path.join(out_dir, f"{stem}.png" if dest == "runs" else f"{stem}.jpg")
        if dest == "runs":
            im.save(out, "PNG", optimize=True)
        else:
            im.save(out, "JPEG", quality=84, optimize=True, progressive=True)
        print(f"copied {rel} -> handsgate/public/{dest}/{os.path.basename(out)}")


def main() -> int:
    with open(TOKENS, encoding="utf-8") as fh:
        d = json.load(fh)
    css = build(d)
    copy_mark()
    copy_renders()
    prev = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(css)
    rel = os.path.relpath(OUT, ROOT).replace(os.sep, "/")
    print(f"{'unchanged' if prev == css else 'wrote'} {rel}  "
          f"({len(css.splitlines())} lines from brand/tokens.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
