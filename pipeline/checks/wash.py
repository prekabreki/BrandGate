"""Is a generated ground softened the way the gradient rule says?

The first calibration set (docs/calibration.md, 2026-09-15) found the gate
passing seven frames the designer rejected, every one for "too dark" or "not
enough bleed". No check measured either. This one measures three things the
designer's notes turned out to mean:

- dark chroma: how saturated the dark pixels are. A wash is light on paper;
  the rejects had deep, saturated indigo and magenta where the designer wanted
  a tint. Measured as the mean Lab chroma of pixels below mid luminance.
- edge steepness: how hard the transitions are. "Strong outlines" and "too
  much separation" are steep chroma gradients around an orb. Measured as the
  99th percentile of the blurred chroma gradient, so a few pixels of a mark's
  edge do not dominate, but a ring around every orb does.
- stop coverage: whether every named stop is present. "Too few colours" was a
  wash of one hue. Each colour the rule names must hold a minimum share of the
  chromatic pixels, matched on hue alone, since a veiled tint keeps its hue and
  little else.

Chroma, not luminance, on purpose: ink type on a surface is achromatic, so a
hero with a headline on it is measured on its wash and not on its letters.

Applies only where there is a wash to judge: a light ground with chromatic
pixels covering a real share of the frame. A flat surface with a small mark
has no wash. A night ground is not applicable for now; the rule allows night,
but every labelled frame is paper, so a night bar would be a guess.

Every threshold lives in brand/gate.toml [wash] and every one was set from the
labelled set by the procedure written beside it there.
"""
from __future__ import annotations

import cv2
import numpy as np

from pipeline.checks import Finding, not_applicable, register
from pipeline.checks.colour import hex_to_rgb

WORK_W = 512  # measurements are made on a copy this wide, whatever came in


def _lab(img_rgb: np.ndarray):
    lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    L = lab[..., 0] * (100.0 / 255.0)
    a = lab[..., 1] - 128.0
    b = lab[..., 2] - 128.0
    return L, a, b


def _stop_lab(hex_colour: str) -> np.ndarray:
    px = np.array([[hex_to_rgb(hex_colour)]], dtype=np.uint8)
    L, a, b = _lab(px)
    return np.array([L[0, 0], a[0, 0], b[0, 0]], dtype=np.float32)


def measure(img_rgb: np.ndarray, stops: list[str], cfg: dict) -> dict:
    """The raw numbers, before any threshold is applied."""
    h = max(1, int(img_rgb.shape[0] * WORK_W / img_rgb.shape[1]))
    im = cv2.resize(img_rgb, (WORK_W, h), interpolation=cv2.INTER_AREA)
    L, a, b = _lab(im)
    C = np.sqrt(a * a + b * b)

    chrom = C > cfg["chroma_floor"]
    achrom = ~chrom
    ground_L = float(np.median(L[achrom])) if achrom.any() else float(np.median(L))

    dark = L < 50.0
    dark_chroma = float(C[dark].mean()) if dark.any() else 0.0

    blur = cv2.GaussianBlur(C, (0, 0), WORK_W / cfg["blur_divisor"])
    gx = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blur, cv2.CV_32F, 0, 1, ksize=3)
    edge_p99 = float(np.percentile(np.sqrt(gx * gx + gy * gy), 99))

    # Stops are matched on HUE alone. A wash is a tint of its stop under a paper
    # veil: the luminance and chroma move with the veil, the hue does not. A
    # full Lab distance handed every veiled indigo pixel to magenta, because the
    # indigo token is far more saturated than any pixel in a softened wash.
    share: dict[str, float] = {}
    if stops and chrom.any():
        hue = np.arctan2(b[chrom], a[chrom])
        targets = np.array([np.arctan2(_stop_lab(s)[2], _stop_lab(s)[1]) for s in stops])
        diff = np.abs(np.angle(np.exp(1j * (hue[:, None] - targets[None, :]))))
        nearest = diff.argmin(axis=1)
        for i, s in enumerate(stops):
            share[s] = float((nearest == i).mean())

    return {"ground_L": round(ground_L, 2), "chroma_frac": round(float(chrom.mean()), 4),
            "dark_chroma": round(dark_chroma, 3), "edge_p99": round(edge_p99, 3),
            "stop_share": {k: round(v, 4) for k, v in share.items()}}


def _named_stops(rule: dict) -> list[str]:
    """The stops the rule names, minus grounds: a wash is judged on its colours,
    not on the paper it sits on."""
    out = []
    for hx in rule.get("params", {}).get("stops") or []:
        L = _stop_lab(hx)[0]
        if 20.0 <= L <= 85.0:
            out.append(hx.upper())
    return out


@register("wash")
def check(img: np.ndarray, rule: dict, cfg: dict, ctx: dict) -> Finding:
    c = cfg["wash"]
    stops = _named_stops(rule)
    if not stops:
        return not_applicable(rule["id"], "wash", "the rule names no gradient stops to look for")

    m = measure(img, stops, c)
    if m["ground_L"] < c["night_below_L"]:
        return not_applicable(rule["id"], "wash",
                              f"night ground (L {m['ground_L']:.0f}): the wash bar is set on "
                              "paper only, night has no labelled frames yet")
    if m["chroma_frac"] < c["min_wash_frac"]:
        return not_applicable(rule["id"], "wash",
                              f"no wash to judge: colour covers {m['chroma_frac']:.0%} of the "
                              f"frame, under the {c['min_wash_frac']:.0%} a ground has")

    # Each axis scores 1.0 well inside the bar and slides to 0.0 at twice it,
    # so the aggregate can rank two failures. The verdict is the worst axis.
    def slide(value, limit, inverse=False):
        if inverse:  # bigger is better
            return float(np.clip(value / limit, 0.0, 1.0))
        return float(np.clip(2.0 - value / limit, 0.0, 1.0))

    reasons = []
    s_dark = slide(m["dark_chroma"], c["dark_chroma_max"])
    if m["dark_chroma"] >= c["dark_chroma_max"]:
        reasons.append(f"the darks are saturated (chroma {m['dark_chroma']:.0f}, "
                       f"a wash stays under {c['dark_chroma_max']:.0f})")
    s_edge = slide(m["edge_p99"], c["edge_max"])
    if m["edge_p99"] >= c["edge_max"]:
        reasons.append(f"the orbs separate: steepest edges {m['edge_p99']:.1f}, "
                       f"a bleed stays under {c['edge_max']:.0f}")
    weakest = min(m["stop_share"], key=m["stop_share"].get)
    s_stop = slide(m["stop_share"][weakest], c["stop_share_min"], inverse=True)
    if m["stop_share"][weakest] < c["stop_share_min"]:
        reasons.append(f"{weakest} holds {m['stop_share'][weakest]:.1%} of the wash; "
                       f"every stop needs {c['stop_share_min']:.0%}")

    score = min(s_dark, s_edge, s_stop)
    passed = not reasons
    reason = ("soft wash: darks at chroma "
              f"{m['dark_chroma']:.0f}, edges {m['edge_p99']:.1f}, every stop present"
              if passed else "; ".join(reasons))
    return Finding(rule["id"], "wash", round(score, 4), passed, reason, m)
