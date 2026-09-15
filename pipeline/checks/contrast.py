"""Does any text in the frame stand off its ground?

There is no OCR here. Text regions are found with MSER, which returns stable
blobs of consistent tone, and then filtered to the shapes type actually makes:
small, dense, and arriving in horizontal runs. That finds lettering and also
finds anything else letter-shaped, which is the honest v1 limit and is recorded
in the calibration write-up rather than glossed.

The ratio is WCAG 2.1, measured between a blob's own tone and the ring of
ground immediately around it, not the frame average. On a gradient wash those
two numbers differ enormously, and it is the local one a reader experiences.
"""
from __future__ import annotations

import numpy as np

from pipeline.checks import Finding, memo, not_applicable, register
from pipeline.checks.colour import contrast_ratio


def text_regions(img: np.ndarray, cfg: dict):
    """Candidate type blobs as (x, y, w, h), largest first."""
    import cv2
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    mser = cv2.MSER_create()
    mser.setMinArea(int(cfg["contrast"]["min_region_px"]))
    mser.setMaxArea(int(0.05 * gray.size))
    try:
        regions, _ = mser.detectRegions(gray)
    except cv2.error:
        return []
    boxes = []
    for r in regions:
        x, y, w, h = cv2.boundingRect(r.reshape(-1, 1, 2))
        # Glyph-shaped: taller than a hairline, not a full-width band, and not
        # wildly elongated in either direction.
        if w < 3 or h < 6:
            continue
        ratio = w / h
        if ratio > 6 or ratio < 0.06:
            continue
        if w > 0.6 * img.shape[1] or h > 0.4 * img.shape[0]:
            continue
        # Type has ink AND paper inside its own bounding box, so a glyph's box
        # always carries a spread of tones. A flat patch does not, and MSER
        # returns plenty of those on a gradient wash. Without this filter the
        # check measured flat regions against themselves and reported a
        # nonsense 1.0:1 contrast failure on a correct night surface.
        patch = gray[y:y + h, x:x + w]
        if patch.size == 0 or float(patch.std()) < 12.0:
            continue
        boxes.append((x, y, w, h))
    return sorted(set(boxes), key=lambda b: -b[2] * b[3])


def _ink_and_ground(img: np.ndarray, box, pad: int = 6):
    """A blob's own tone, and the ground just outside it."""
    x, y, w, h = box
    H, W = img.shape[:2]
    inner = img[y:y + h, x:x + w].reshape(-1, 3)
    if len(inner) == 0:
        return None, None
    y0, y1 = max(0, y - pad), min(H, y + h + pad)
    x0, x1 = max(0, x - pad), min(W, x + w + pad)
    ring = img[y0:y1, x0:x1].astype(np.float64).copy()
    ring[y - y0:y - y0 + h, x - x0:x - x0 + w] = np.nan
    ring = ring.reshape(-1, 3)
    ring = ring[~np.isnan(ring).any(axis=1)]
    if len(ring) == 0:
        return None, None
    # The ink is whichever tone inside the box sits FURTHEST from the ground,
    # not simply the darkest. This brand sets white type on night as readily as
    # ink on paper, and assuming dark-on-light picked the ground as the ink on
    # every night surface, reporting a flat 1.0:1 and failing a take whose type
    # is in fact fully legible.
    ground = np.median(ring, axis=0)
    lum = inner.astype(np.float64).mean(axis=1)
    ground_lum = float(np.mean(ground))
    far = np.abs(lum - ground_lum)
    ink = inner[far >= np.percentile(far, 75)].mean(axis=0)
    return ink, ground


@register("contrast")
def check(img: np.ndarray, rule: dict, cfg: dict, ctx: dict) -> Finding:
    boxes = memo(ctx, "text_regions", cfg["contrast"], lambda: text_regions(img, cfg))
    if not boxes:
        return not_applicable(rule["id"], "contrast",
                              "no text region detected, nothing to measure")

    bar = cfg["contrast"]["ratio_min"]
    ratios = []
    for box in boxes[:40]:
        ink, ground = _ink_and_ground(img, box)
        if ink is None:
            continue
        ratios.append((contrast_ratio(ink, ground), box))
    if not ratios:
        return not_applicable(rule["id"], "contrast",
                              "text regions found but none measurable")

    ratios.sort(key=lambda t: t[0])
    worst, box = ratios[0]
    score = float(min(1.0, worst / bar))
    passed = worst >= bar
    return Finding(
        rule["id"], "contrast", score, passed,
        (f"every text region clears {bar}:1 (worst {worst:.1f}:1)" if passed
         else f"a text region at {box[0]},{box[1]} sits at {worst:.1f}:1 "
              f"against its ground, under the {bar}:1 bar"),
        {"worst_ratio": worst, "bar": bar, "regions": len(ratios)})
