"""Build site/assets from the composed surfaces, so the page never drifts from them.

    uv run python site/build_assets.py

Every image the page shows is a JPEG cut from a PNG under surfaces/<name>/accepted or
rejected, plus the one-pager PDF copied across. The hero gets an 800-wide variant for
the srcset. Nothing here is hand-made; if a surface is recomposed, run this and the page
follows. Until #22 these were cut by hand in a session and the recipe lived nowhere.
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import urllib.request

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "site", "assets")
S = os.path.join(ROOT, "surfaces")

# (source PNG, asset name, max width or None for as-is)
CUTS = [
    (f"{S}/hero/accepted/ground.png", "ground-accepted.jpg", 1664),
    (f"{S}/hero/accepted/hero.png", "hero-accepted.jpg", 1600),
    (f"{S}/hero/accepted/hero.png", "hero-accepted-800.jpg", 800),
    (f"{S}/hero/rejected/hero.png", "hero-rejected.jpg", 1600),
    (f"{S}/hero/rejected/hero.png", "hero-rejected-800.jpg", 800),
    (f"{S}/social/accepted/square.png", "square.jpg", 1080),
    (f"{S}/social/accepted/story.png", "story.jpg", 1080),
    (f"{S}/social/accepted/og.png", "og.jpg", 1200),
    (f"{S}/print/accepted/onepager.png", "onepager.jpg", 1240),
]
COPIES = [(f"{S}/print/accepted/onepager.pdf", "handsel-onepager.pdf"),
          (f"{ROOT}/brand/guide_05.pdf", "handsel-brand-sheet.pdf"),
          # the ident, rendered by surfaces/motion/render.py; the site takes the 960 cut and its poster
          (f"{S}/motion/out/ident-960.mp4", "ident-960.mp4"),
          (f"{S}/motion/out/poster.jpg", "ident-poster.jpg"),
          (f"{S}/motion/out/refused/ident-960.mp4", "ident-refused-960.mp4"),
          (f"{S}/motion/out/refused/poster.jpg", "ident-refused-poster.jpg")]
# The brand sheet: the whole thing, and its head for the card on the page.
SHEET = f"{ROOT}/brand/guide_05.png"
# Screenshots of the public tools the page links to, pulled from each repo's own README
# so the site shows what the repo shows. (raw URL, asset stem, widths)
TOOLS = [
    ("https://raw.githubusercontent.com/prekabreki/ck3-llm-chronicler/HEAD/docs/images/chronicle.png",
     "ck3-chronicle", (1600, 800)),
]
# The other five tool cards. Their repos ship no screenshot yet, so the captures live in
# site/tools/ with their provenance in site/tools/README.md and are cut here the same way.
# Every card face is 8:5, so the grid never shows six different aspects. The crop box is
# what makes each capture 8:5 without padding; None means it already is.
# (source PNG under site/tools, asset stem, crop box or None)
SHOTS = [
    # Re-taken 2026-09-18 from the local build after the post-export pass: real mark,
    # real surface renders, the real sameness figure, and no Lovable badge to crop off.
    ("shot-brandgate.png", "tool-brandgate", None),
    ("shot-gate.png", "tool-gate", None),
    ("shot-swice.png", "tool-swice", (0, 0, 1350, 844)),
    ("shot-fetchforge.png", "tool-fetchforge", (0, 0, 1500, 938)),
    ("shot-scorescout.png", "tool-scorescout", (0, 0, 1400, 875)),
    ("shot-deciwaves.png", "tool-deciwaves", None),
]
SHOTS_DIR = os.path.join(ROOT, "site", "tools")


def cut(src: str, name: str, width: int | None, quality: int = 86) -> str:
    im = Image.open(src).convert("RGB")
    if width and im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    out = os.path.join(ASSETS, name)
    im.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
    return out


def fetch(url: str, stem: str, widths: tuple[int, ...]) -> None:
    with urllib.request.urlopen(url, timeout=60) as r:
        im = Image.open(io.BytesIO(r.read())).convert("RGB")
    for w in widths:
        name = f"{stem}.jpg" if w == widths[0] else f"{stem}-{w}.jpg"
        out = os.path.join(ASSETS, name)
        im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(
            out, "JPEG", quality=86, optimize=True, progressive=True)
        print(f"{name:26s} {os.path.getsize(out) // 1024:>5} KB  <- {url}")


def shots() -> None:
    """Cut site/tools/*.png to the 1600 and 800 wide JPEGs the tool cards load."""
    for name, stem, box in SHOTS:
        im = Image.open(os.path.join(SHOTS_DIR, name)).convert("RGB")
        if box:
            im = im.crop(box)
        for w in (1600, 800):
            asset = f"{stem}.jpg" if w == 1600 else f"{stem}-{w}.jpg"
            out = os.path.join(ASSETS, asset)
            im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(
                out, "JPEG", quality=86, optimize=True, progressive=True)
            print(f"{asset:26s} {os.path.getsize(out) // 1024:>5} KB  <- site/tools/{name}")


def sheet() -> None:
    im = Image.open(SHEET).convert("RGB")
    out = os.path.join(ASSETS, "brand-sheet.jpg")
    im.save(out, "JPEG", quality=86, optimize=True, progressive=True)
    print(f"{'brand-sheet.jpg':26s} {os.path.getsize(out) // 1024:>5} KB  <- brand/guide_05.png")
    head = im.crop((0, 0, im.width, 1500))
    out = os.path.join(ASSETS, "brand-sheet-head.jpg")
    head.save(out, "JPEG", quality=86, optimize=True, progressive=True)
    print(f"{'brand-sheet-head.jpg':26s} {os.path.getsize(out) // 1024:>5} KB  <- brand/guide_05.png, top 1500")


def stats() -> None:
    """The three numbers the one-pager prints, from the same function, so the site and
    the sheet never disagree. The page reads assets/stats.json and falls back to the
    numbers written into its HTML."""
    import json
    sys.path.insert(0, ROOT)
    from surfaces.print.compose import run_numbers
    out = os.path.join(ASSETS, "stats.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(run_numbers(), fh)
    print(f"{'stats.json':26s} {open(out).read()}")


def main() -> int:
    os.makedirs(ASSETS, exist_ok=True)
    sheet()
    stats()
    for src, name, width in CUTS:
        out = cut(src, name, width)
        print(f"{name:26s} {os.path.getsize(out) // 1024:>5} KB  <- {os.path.relpath(src, ROOT)}")
    for src, name in COPIES:
        out = os.path.join(ASSETS, name)
        shutil.copy(src, out)
        print(f"{name:26s} {os.path.getsize(out) // 1024:>5} KB  <- {os.path.relpath(src, ROOT)}")
    for url, stem, widths in TOOLS:
        fetch(url, stem, widths)
    shots()
    return 0


if __name__ == "__main__":
    sys.exit(main())
