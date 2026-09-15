"""One gesture per surface.

A gesture is a deliberate brand move: the mark placed somewhere, a run of
gradient display type, or a field of slices. The rule says a surface gets one
of them. Two is the failure this counts.

Mark hits are merged by distance first, because the same mark found at three
template scales is one gesture seen three times, not three gestures. Getting
that wrong would fail every correct surface, which is the most expensive kind
of bug a gate can have: it teaches people to ignore it.
"""
from __future__ import annotations

import numpy as np

from pipeline.checks import Finding, memo, register
from pipeline.checks.band import locate
from pipeline.checks.contrast import text_regions


def _merge(hits, width, frac):
    """Collapse hits that sit within frac of the frame width of each other."""
    kept = []
    for h in sorted(hits, key=lambda d: -d["score"]):
        if all((h["x"] - k["x"]) ** 2 + (h["y"] - k["y"]) ** 2
               > (frac * width) ** 2 for k in kept):
            kept.append(h)
    return kept


def _overlaps_mark(box, hits, img) -> bool:
    """True if a blob sits inside a detected mark placement.

    The mark IS a gradient shape, so MSER reads its slices as glyph-shaped
    blobs with hue travel across them and the gradient-type test fires on the
    mark itself. Counted naively that makes every correct surface carrying one
    gradient mark score two gestures and fail the one-gesture rule: the check
    would reject the brand for wearing itself.

    RULED 2026-09-14 by the designer, on take 1, which carries the mark and the
    wordmark in the flow: a mark and the wordmark together are ONE lockup, so
    the overlap merge stands. This is a taste call that was put to him and
    answered, not an assumption. Changing it changes what motif.02 means.
    """
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2
    for hit in hits:
        # The template's own aspect is about 3:1; allow the placement a
        # generous box around its centre.
        half_w = img.shape[1] * hit["scale"] / 2
        half_h = half_w / 1.5
        if abs(cx - hit["x"]) <= half_w and abs(cy - hit["y"]) <= half_h:
            return True
    return False


def gradient_type_present(img: np.ndarray, boxes, hits=()) -> bool:
    """True when a run of type carries a colour sweep across it.

    Display type in the flow is a gesture; the same words in flat ink are not.
    Measured as hue travel along the text run, which is what a gradient is and
    what a flat colour is not.
    """
    import cv2
    if not boxes:
        return False
    big = [b for b in boxes
           if b[2] * b[3] > 0.004 * img.shape[0] * img.shape[1]
           and not _overlaps_mark(b, hits, img)]
    if not big:
        return False
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    for x, y, w, h in big[:10]:
        strip = hsv[y:y + h, x:x + w]
        sat = strip[:, :, 1].astype(np.float64)
        hue = strip[:, :, 0].astype(np.float64)
        ink = sat > 60
        if ink.sum() < 50:
            continue
        cols = [np.median(hue[:, c][ink[:, c]]) for c in range(w)
                if ink[:, c].sum() > 3]
        if len(cols) < 8:
            continue
        # OpenCV hue is 0-179. A sweep of more than 10 units across the run is
        # a gradient; anti-aliasing noise on flat type stays well under it.
        if np.ptp(np.array(cols)) > 10:
            return True
    return False


@register("motif")
def check(img: np.ndarray, rule: dict, cfg: dict, ctx: dict) -> Finding:
    level, rotated, hits = memo(ctx, "band", cfg["band"], lambda: locate(img, cfg))
    boxes = memo(ctx, "text_regions", cfg["contrast"], lambda: text_regions(img, cfg))
    merged = _merge(hits, img.shape[1], cfg["motif"]["merge_distance"])

    gestures = []
    if merged:
        gestures.append(f"the mark ({len(merged)} placement"
                        f"{'s' if len(merged) > 1 else ''})")
    if gradient_type_present(img, boxes, merged):
        gestures.append("gradient display type")

    limit = cfg["motif"]["max_gestures"]
    count = len(gestures)
    passed = count <= limit
    score = 1.0 if passed else max(0.0, 1.0 - (count - limit) / max(limit, 1))
    return Finding(
        rule["id"], "motif", float(score), passed,
        (f"{count} gesture{'s' if count != 1 else ''} on the surface"
         + (f": {', '.join(gestures)}" if gestures else "")
         + ("" if passed else f", over the {limit} the rule allows")),
        {"gestures": gestures, "mark_placements": len(merged)})
