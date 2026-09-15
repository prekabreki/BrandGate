"""Is the six-slice mark present, and is it level?

Template matching against the mark rendered from its own SVG, not against a
stored bitmap: the SVG is the artwork, so a change to the mark changes what the
gate looks for, with no second copy to keep in step.

Matched on blurred gradient magnitude rather than raw pixels. The mark appears
in a gradient, in solid ink and in solid white, over paper and over night, so a
brightness template matches one of those and misses the rest; edges are what
all five variants share. The blur is not cosmetic: a solid shape's edges are
one or two pixels wide, so without it a two-pixel scale error takes the
correlation to nothing.

Candidate windows are gated on edge energy before their score is believed. A
smooth gradient wash carries almost no edge energy, and normalised correlation
between two near-empty patches comes back a confident 1.00. Measured on these
takes sheets, an ungated detector reported a perfect match on blank wash in
every frame, and pointed at the caption strip rather than the mark. The floor
is the difference between a detector and a random number generator.
"""
from __future__ import annotations

import functools
import os

import numpy as np

from pipeline.checks import (
    CheckDependencyError,
    Finding,
    memo,
    not_applicable,
    register,
)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MARK_SVG = os.path.join(ROOT, "brand", "logo", "slice-mark-blank.svg")


def _edges(gray: np.ndarray, blur: float) -> np.ndarray:
    import cv2
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    peak = mag.max()
    mag = mag / peak if peak > 0 else mag
    if blur:
        mag = cv2.GaussianBlur(mag, (0, 0), blur)
    return mag.astype(np.float32)


@functools.lru_cache(maxsize=64)
def _template(width: int, blur: float, svg_path: str, mtime: float) -> np.ndarray:
    """The mark rasterised at a width, as an edge map. Cached on the file's
    mtime so editing the SVG invalidates it rather than serving the old mark."""
    try:
        # cairosvg imports fine and then fails to LOAD libcairo (an OSError
        # from cffi), so both exception types mean the same thing here.
        import cairosvg
    except (ImportError, OSError) as e:
        raise CheckDependencyError("cairosvg", e) from e
    import cv2
    png = cairosvg.svg2png(url=svg_path, output_width=width)
    arr = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)
    if arr.ndim == 3 and arr.shape[2] == 4:
        # Composite onto mid grey: the alpha carries the shape, and a white or
        # black matte would hand the edge detector a border that is not there.
        alpha = arr[:, :, 3:4].astype(np.float32) / 255.0
        arr = (arr[:, :, :3].astype(np.float32) * alpha
               + 128 * (1 - alpha)).astype(np.uint8)
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if arr.ndim == 3 else arr
    return _edges(gray.astype(np.float32), blur)


def _match(scene: np.ndarray, template: np.ndarray, energy_floor: float):
    """Best correlation of template over scene, ignoring windows too empty to
    contain it. Returns (score, (x, y)) of the window's top-left."""
    import cv2
    th, tw = template.shape
    if th >= scene.shape[0] or tw >= scene.shape[1]:
        return -1.0, (0, 0)
    res = cv2.matchTemplate(scene, template, cv2.TM_CCOEFF_NORMED)
    kernel = np.ones(template.shape, np.float32) / template.size
    energy = cv2.filter2D(scene, -1, kernel)[
        th // 2:th // 2 + res.shape[0], tw // 2:tw // 2 + res.shape[1]]
    res = np.where(energy >= energy_floor * float(template.mean()), res, -1.0)
    y, x = np.unravel_index(int(res.argmax()), res.shape)
    return float(res.max()), (int(x), int(y))


def locate(img: np.ndarray, cfg: dict, svg_path: str | None = None):
    """Best match of the mark over the scale pyramid, level and rotated.

    Returns (level_score, rotated_score, hits) where hits are every location
    scoring above the presence threshold, for the motif check to count.
    """
    import cv2
    c = cfg["band"]
    svg = svg_path or MARK_SVG
    mtime = os.path.getmtime(svg)
    blur = c["edge_blur"]
    floor = c["energy_floor"]
    scene = _edges(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32), blur)

    level, rotated, hits = -1.0, -1.0, []
    rendered, last_error = 0, None
    for scale in np.linspace(c["scale_min"], c["scale_max"], int(c["scale_steps"])):
        width = int(img.shape[1] * float(scale))
        if width < 24:
            continue
        try:
            tpl = _template(width, blur, svg, mtime)
        except CheckDependencyError:
            # A missing library is the same at every scale. Say so once, loudly:
            # swallowing it here is what made a dead detector read as "no mark
            # in the frame" across a whole calibration set.
            raise
        except Exception as e:
            last_error = e
            continue
        rendered += 1
        s, (x, y) = _match(scene, tpl, floor)
        level = max(level, s)
        if s >= c["present_min"]:
            hits.append({"scale": round(float(scale), 3), "score": s,
                         "x": x + tpl.shape[1] / 2, "y": y + tpl.shape[0] / 2})
        # 90 degrees is the cheap, unambiguous rotation test. A mark tilted by
        # a few degrees is not caught here; that is named as a v1 limit in
        # docs/calibration.md rather than left for someone to discover.
        r, _ = _match(scene, np.rot90(tpl).copy(), floor)
        rotated = max(rotated, r)
    if not rendered and last_error is not None:
        # Every scale failed for some other reason. That is still a detector
        # that did not run, not a frame without a mark.
        raise RuntimeError(
            f"the mark could not be rendered at any scale: {last_error}") from last_error
    return level, rotated, hits


@register("band")
def check(img: np.ndarray, rule: dict, cfg: dict, ctx: dict) -> Finding:
    level, rotated, hits = memo(ctx, "band", cfg["band"], lambda: locate(img, cfg))
    present_min = cfg["band"]["present_min"]
    margin = cfg["band"]["rotation_margin"]
    forbidden = rule["params"].get("forbid_transforms") or []

    if level < present_min and rotated < present_min:
        # Every mark rule describes the mark AS USED, not a requirement that
        # every surface carry one. A hero ground has no mark and is not in
        # breach of the mark rules; scoring that as a failure is how a gate
        # earns a reputation for crying wolf and stops being read.
        return not_applicable(rule["id"], "band",
                              "no mark in the frame, so the mark rules do not apply")

    if "rotated" in forbidden or "mirrored" in forbidden:
        if rotated > level + margin:
            return Finding(rule["id"], "band", 0.0, False,
                           f"the mark matches {rotated:.2f} rotated against "
                           f"{level:.2f} level, so it is not upright",
                           {"level": level, "rotated": rotated})
        return Finding(rule["id"], "band", 1.0, True,
                       f"the mark is level (level {level:.2f}, rotated {rotated:.2f})",
                       {"level": level, "rotated": rotated})

    # A mark is present and this rule describes its construction. v1 confirms
    # the mark matches the artwork the SVG defines; it does not yet measure
    # slice count or band ratio independently, which is named as a limit in
    # docs/calibration.md rather than implied to be covered.
    return Finding(rule["id"], "band",
                   float(max(0.0, min(1.0, level / max(present_min, 1e-6)))),
                   True, f"the mark matches the artwork at {level:.2f}",
                   {"level": level, "placements": len(hits)})
