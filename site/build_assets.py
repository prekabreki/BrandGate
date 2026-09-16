"""Build site/assets from the composed surfaces, so the page never drifts from them.

    uv run python site/build_assets.py

Every image the page shows is a JPEG cut from a PNG under surfaces/<name>/accepted or
rejected, plus the one-pager PDF copied across. The hero gets an 800-wide variant for
the srcset. Nothing here is hand-made; if a surface is recomposed, run this and the page
follows. Until #22 these were cut by hand in a session and the recipe lived nowhere.
"""
from __future__ import annotations

import os
import shutil
import sys

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
COPIES = [(f"{S}/print/accepted/onepager.pdf", "handsel-onepager.pdf")]


def cut(src: str, name: str, width: int | None, quality: int = 86) -> str:
    im = Image.open(src).convert("RGB")
    if width and im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    out = os.path.join(ASSETS, name)
    im.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
    return out


def main() -> int:
    os.makedirs(ASSETS, exist_ok=True)
    for src, name, width in CUTS:
        out = cut(src, name, width)
        print(f"{name:26s} {os.path.getsize(out) // 1024:>5} KB  <- {os.path.relpath(src, ROOT)}")
    for src, name in COPIES:
        out = os.path.join(ASSETS, name)
        shutil.copy(src, out)
        print(f"{name:26s} {os.path.getsize(out) // 1024:>5} KB  <- {os.path.relpath(src, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
