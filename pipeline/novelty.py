"""How far is this frame from what has already been accepted?

Two distances. A perceptual hash catches the near-duplicate: the same
composition regenerated at a neighbouring seed. A CLIP embedding catches the
same idea rendered differently, which a hash cannot see at all. They disagree
often and usefully, so the score is their mean rather than either alone.

CLIP is optional. open_clip pulls torch, and a gate that refuses to run without
a 2.5 GB dependency is a gate that gets skipped. Without it the score is the
hash alone and `clip` reads false in the output, so no reader is left assuming
a semantic check ran when it did not.
"""
from __future__ import annotations

import functools
import glob
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCEPTED_GLOB = os.path.join(ROOT, "surfaces", "*", "accepted", "*.png")


def phash(img: np.ndarray, bits: int = 64) -> np.ndarray:
    """DCT perceptual hash. Returns a bool array of length `bits`."""
    import cv2
    side = int(round(bits ** 0.5)) * 4
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    small = cv2.resize(gray, (side, side), interpolation=cv2.INTER_AREA)
    d = cv2.dct(small.astype(np.float32))
    n = int(round(bits ** 0.5))
    low = d[:n, :n].flatten()
    # The DC term encodes overall brightness, not structure, and would make
    # every dark frame look like every other dark frame.
    return low > np.median(low[1:])


def hamming(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.count_nonzero(a != b) / len(a))


@functools.lru_cache(maxsize=1)
def _clip():
    """(model, preprocess) or None. Cached: loading torch twice is a minute."""
    try:
        import open_clip
        import torch
    except ImportError:
        return None
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k")
    model.eval()
    torch.set_grad_enabled(False)
    return model, preprocess


def clip_embedding(img: np.ndarray):
    pair = _clip()
    if pair is None:
        return None
    import torch
    from PIL import Image
    model, preprocess = pair
    t = preprocess(Image.fromarray(img)).unsqueeze(0)
    v = model.encode_image(t)[0]
    return (v / v.norm()).numpy()


def clip_available() -> bool:
    return _clip() is not None


def accepted_paths(pattern: str | None = None) -> list[str]:
    return sorted(glob.glob(pattern or ACCEPTED_GLOB))


def features_of(img: np.ndarray, bits: int) -> tuple:
    """(phash, clip embedding or None) for a frame already in memory."""
    return phash(img, bits), clip_embedding(img)


@functools.lru_cache(maxsize=4096)
def _features_cached(path: str, mtime: float, bits: int, with_clip: bool) -> tuple:
    import cv2
    img = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
    return features_of(img, bits)


def features(path: str, bits: int) -> tuple:
    """Features of a frame on disk, cached on its path and mtime. The sameness
    run compares a 200-frame set with itself at five threshold sets, and
    without this the CLIP embeddings alone would be recomputed a hundred
    thousand times."""
    return _features_cached(path, os.path.getmtime(path), bits, clip_available())


def distance(a: tuple, b: tuple, cfg: dict) -> float:
    """The gate's novelty distance between two feature tuples, 0 to 1."""
    return _distance_parts(a, b, cfg)[0]


def _distance_parts(a: tuple, b: tuple, cfg: dict) -> tuple[float, dict]:
    d_hash = hamming(a[0], b[0])
    parts = {"phash": d_hash}
    d = d_hash
    if a[1] is not None and b[1] is not None:
        d_clip = float(np.clip((1.0 - float(a[1] @ b[1])) / 2.0, 0, 1))
        w = cfg["novelty"]["clip_weight"]
        d = (1 - w) * d_hash + w * d_clip
        parts["clip"] = d_clip
    return float(d), parts


def score(img: np.ndarray, cfg: dict, pattern: str | None = None,
          paths: list[str] | None = None) -> dict:
    """Distance to the nearest accepted frame, 0 (identical) to 1 (unlike all).

    The accepted set is `paths` when given (the sameness run hands over what
    it has accepted so far), otherwise whatever matches `pattern`.
    """
    paths = accepted_paths(pattern) if paths is None else list(paths)
    if not paths:
        # Nothing has been accepted yet, so nothing can be repeated. Stated as
        # a reason rather than left as a bare 1.0 that reads like a measurement.
        return {"novelty": 1.0, "nearest": None, "compared": 0, "clip": False,
                "reason": "the accepted set is empty, so every frame is novel"}

    bits = cfg["novelty"]["phash_bits"]
    mine = features_of(img, bits)
    best, best_path, best_parts = 1.0, None, {}
    for p in paths:
        d, parts = _distance_parts(mine, features(p, bits), cfg)
        if d < best:
            best, best_path, best_parts = d, p, parts
    clip_ran = mine[1] is not None
    return {"novelty": float(best),
            "nearest": os.path.relpath(best_path, ROOT).replace(os.sep, "/"),
            "compared": len(paths), "clip": clip_ran,
            "parts": best_parts,
            "reason": (f"closest to {os.path.basename(best_path)} at "
                       f"{best:.2f}" + ("" if clip_ran else
                                        ", hash only: open_clip is not installed"))}
