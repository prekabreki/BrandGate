"""Plotting helpers shared by the runs (#9 drift, #10 sameness).

Brand colours from brand/tokens.json, never a default palette; contact sheets
through PIL so they need nothing matplotlib does not already need. Matplotlib
itself is imported inside the function that draws, so a box without it can
still import this module and build sheets.
"""
from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKENS = os.path.join(ROOT, "brand", "tokens.json")


def brand() -> dict:
    """Colour name to hex, straight from the tokens file."""
    with open(TOKENS, encoding="utf-8") as fh:
        doc = json.load(fh)
    return {k: v["hex"] for k, v in doc["color"].items()}


def _font(size: int):
    # Archivo and Plex Mono are the brand faces, and Pillow will not find them
    # unless they are installed system-wide. The default face is a fallback,
    # not a choice; the figure's typography is matplotlib's job.
    for name in ("Archivo-Regular.ttf", "IBMPlexMono-Regular.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def contact_sheet(paths: list[str], cols: int = 6, tile_w: int = 260,
                  pad: int = 10, caption=None, colours: dict | None = None) -> Image.Image:
    """A grid of frames with one caption under each. `caption(path)` returns
    the label; by default the seed pulled from the ledger-style filename."""
    c = colours or brand()
    caption = caption or _seed_caption
    if not paths:
        img = Image.new("RGB", (tile_w * 2 + pad * 3, tile_w // 2), c["paper"])
        d = ImageDraw.Draw(img)
        d.text((pad * 2, pad * 2), "nothing accepted at this step",
               fill=c["graphite"], font=_font(16))
        return img
    first = Image.open(paths[0])
    tile_h = int(tile_w * first.height / first.width)
    line = 22
    rows = (len(paths) + cols - 1) // cols
    ncols = min(cols, len(paths))
    W = ncols * tile_w + (ncols + 1) * pad
    H = rows * (tile_h + line) + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), c["paper"])
    d = ImageDraw.Draw(sheet)
    font = _font(13)
    for i, p in enumerate(paths):
        r, col = divmod(i, cols)
        x = pad + col * (tile_w + pad)
        y = pad + r * (tile_h + line + pad)
        tile = Image.open(p).convert("RGB").resize((tile_w, tile_h), Image.LANCZOS)
        sheet.paste(tile, (x, y))
        d.text((x, y + tile_h + 4), caption(p), fill=c["graphite"], font=font)
    return sheet


def _seed_caption(path: str) -> str:
    parts = os.path.basename(path).split("_")
    for i, part in enumerate(parts):
        if part in ("turbo", "raw") and i + 1 < len(parts):
            return f"{part} {parts[i + 1]}"
    return os.path.splitext(os.path.basename(path))[0]


def side_by_side(panels: list[tuple[str, Image.Image]], out_path: str,
                 colours: dict | None = None, gap: int = 40) -> None:
    """Sheets next to each other, each under its title, on paper."""
    c = colours or brand()
    title_h = 44
    W = sum(im.width for _, im in panels) + gap * (len(panels) + 1)
    H = max(im.height for _, im in panels) + title_h + gap * 2
    canvas = Image.new("RGB", (W, H), c["paper"])
    d = ImageDraw.Draw(canvas)
    font = _font(20)
    x = gap
    for title, im in panels:
        d.text((x, gap), title, fill=c["ink"], font=font)
        canvas.paste(im, (x, gap + title_h))
        x += im.width + gap
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path)


def sweep_figure(results: list[dict], out_path: str, shipped_step: int | None,
                 caption: str, colours: dict | None = None) -> None:
    """The sameness figure: three lines over the steps.

    Pass rate of the pool, mean pairwise novelty of the accepted set, and
    agreement with the designer's 27 labels. The designer line is the one that
    gives the figure its point: it peaks, then falls as the gate tightens past
    the designer's own taste.
    """
    import logging

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Archivo is a Google Font and is not installed on either box; matplotlib
    # falls through the family list to DejaVu Sans and would say so once per
    # text object. The fallback is deliberate, so the warning is noise.
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

    c = colours or brand()
    plt.rcParams.update({
        "font.family": ["Archivo", "IBM Plex Sans", "DejaVu Sans", "sans-serif"],
        "font.size": 11,
        "axes.edgecolor": c["graphite"], "axes.labelcolor": c["ink"],
        "xtick.color": c["graphite"], "ytick.color": c["graphite"],
        "text.color": c["ink"],
        "figure.facecolor": c["paper"], "axes.facecolor": c["paper"],
        "savefig.facecolor": c["paper"],
    })
    xs = [r["step"] for r in results]
    pass_rate = [100 * r["pool"]["pass_rate"] for r in results]
    novelty = [r["pool"]["mean_pairwise_novelty"] for r in results]
    agree = [100 * r["designer"]["agreement"] for r in results]

    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=150)
    ax.plot(xs, pass_rate, color=c["indigo"], lw=2.4, marker="o",
            label="pool pass rate, percent")
    ax.plot(xs, agree, color=c["ink"], lw=2.4, marker="s",
            label="agreement with the designer, percent of 27 labels")
    ax.set_ylim(0, 105)
    ax.set_ylabel("percent")
    ax.set_xticks(xs)
    ax.set_xticklabels([f"step {r['step']}\n{_step_label(r['thresholds'])}"
                        for r in results], fontsize=8.5)
    ax.spines["top"].set_visible(False)

    ax2 = ax.twinx()
    nov_x = [x for x, n in zip(xs, novelty) if n is not None]
    nov_y = [n for n in novelty if n is not None]
    ax2.plot(nov_x, nov_y, color=c["rose"], lw=2.4, marker="D",
             label="mean pairwise novelty of the accepted set")
    ax2.set_ylim(0, max(0.5, max(nov_y) * 1.25) if nov_y else 0.5)
    ax2.set_ylabel("novelty, 0 is identical", color=c["rose"])
    ax2.tick_params(axis="y", colors=c["rose"])
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(c["rose"])

    if shipped_step is not None:
        ax.axvline(shipped_step, color=c["graphite"], lw=1, ls="--")
        ax.annotate("shipped gate.toml", (shipped_step, 100), ha="left",
                    va="top", fontsize=9, color=c["graphite"],
                    xytext=(5, 0), textcoords="offset points")

    for x, n, y in zip(xs, [r["pool"]["accepted_n"] for r in results], pass_rate):
        # To the right of the point and a little above, clear of the falling
        # line, the novelty line and the tick text alike. The last point has
        # no right; it goes left.
        last = x == xs[-1]
        ax.annotate(f"{n} accepted", (x, y), xytext=(-7 if last else 7, 6),
                    textcoords="offset points", ha="right" if last else "left",
                    va="bottom", fontsize=8, color=c["indigo"])

    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, -0.2),
              ncol=2, frameon=False, fontsize=9)
    ax.set_title(f"Tightening the gate on a fixed pool of {results[0]['pool']['n']} grounds",
                 loc="left", fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    fig.text(0.01, -0.06, caption, ha="left", va="top", fontsize=9,
             color=c["graphite"], wrap=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def _step_label(t: dict) -> str:
    return (f"on-brand {t['verdict.on_brand_min']:.2f}\n"
            f"forbid {t['palette.forbid_mass']:.3f}  "
            f"chroma {t['wash.dark_chroma_max']:.0f}\n"
            f"edge {t['wash.edge_max']:.0f}  stop {t['wash.stop_share_min']:.2f}")
