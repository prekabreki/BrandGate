"""Small colour utilities. Lab for perceptual distance, WCAG for contrast.

Distances are CIE76 (plain Euclidean in Lab) rather than CIEDE2000. CIE76
overstates differences in saturated blues, which is exactly where this palette
lives, so the tolerance in gate.toml is set against CIE76's scale and must be
re-derived if the metric is ever changed. Said here because a silent metric
swap would move every score without moving a single threshold.
"""
from __future__ import annotations

import numpy as np


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB (0-255, ...x3) to CIE Lab under D65."""
    rgb = np.asarray(rgb, dtype=np.float64).reshape(-1, 3)
    lin = srgb_to_linear(rgb)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ m.T
    white = np.array([0.95047, 1.0, 1.08883])
    xyz = xyz / white
    eps, kappa = 216 / 24389, 24389 / 27
    f = np.where(xyz > eps, np.cbrt(xyz), (kappa * xyz + 16) / 116)
    return np.stack([116 * f[:, 1] - 16,
                     500 * (f[:, 0] - f[:, 1]),
                     200 * (f[:, 1] - f[:, 2])], axis=1)


def lab_distance(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pairwise CIE76 distance, (n,3) against (m,3), returning (n,m)."""
    a, b = np.atleast_2d(a), np.atleast_2d(b)
    return np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)


def relative_luminance(rgb) -> float:
    lin = srgb_to_linear(np.asarray(rgb, dtype=np.float64).reshape(1, 3))[0]
    return float(0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2])


def contrast_ratio(fg, bg) -> float:
    """WCAG 2.1 contrast ratio, 1.0 to 21.0."""
    a, b = relative_luminance(fg), relative_luminance(bg)
    lo, hi = sorted((a, b))
    return (hi + 0.05) / (lo + 0.05)


def dominant_colours(img: np.ndarray, k: int = 8, sample: int = 40000):
    """k dominant colours and the share of the frame each holds.

    Uses cv2's k-means on a random subsample. BOTH sources of randomness are
    seeded: the subsample here, and OpenCV's own global RNG, which drives
    k-means++ initialisation and is not covered by numpy's. Seeding only the
    subsample left the centres coming back in a different order with different
    values on every run, so the same file scored differently each time. A gate
    whose score moves between two runs is not an instrument, it is a mood.
    """
    import cv2

    cv2.setRNGSeed(0)
    px = img.reshape(-1, 3).astype(np.float32)
    if len(px) > sample:
        rng = np.random.default_rng(0)
        px = px[rng.choice(len(px), sample, replace=False)]
    k = int(min(k, max(1, len(np.unique(px, axis=0)))))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centres = cv2.kmeans(
        px, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.ravel(), minlength=k).astype(np.float64)
    weights = counts / counts.sum()
    order = np.argsort(-weights)
    return centres[order].astype(np.float64), weights[order]
