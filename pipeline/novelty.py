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


def accepted_paths(pattern: str | None = None) -> list[str]:
    return sorted(glob.glob(pattern or ACCEPTED_GLOB))


def score(img: np.ndarray, cfg: dict, pattern: str | None = None) -> dict:
    """Distance to the nearest accepted frame, 0 (identical) to 1 (unlike all)."""
    paths = accepted_paths(pattern)
    if not paths:
        # Nothing has been accepted yet, so nothing can be repeated. Stated as
        # a reason rather than left as a bare 1.0 that reads like a measurement.
        return {"novelty": 1.0, "nearest": None, "compared": 0, "clip": False,
                "reason": "the accepted set is empty, so every frame is novel"}

    import cv2
    h = phash(img, cfg["novelty"]["phash_bits"])
    emb = clip_embedding(img)
    best, best_path, best_parts = 1.0, None, {}
    for p in paths:
        other = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
        d_hash = hamming(h, phash(other, cfg["novelty"]["phash_bits"]))
        parts = {"phash": d_hash}
        d = d_hash
        if emb is not None:
            other_emb = clip_embedding(other)
            d_clip = float(np.clip((1.0 - float(emb @ other_emb)) / 2.0, 0, 1))
            w = cfg["novelty"]["clip_weight"]
            d = (1 - w) * d_hash + w * d_clip
            parts["clip"] = d_clip
        if d < best:
            best, best_path, best_parts = d, p, parts
    return {"novelty": float(best),
            "nearest": os.path.relpath(best_path, ROOT).replace(os.sep, "/"),
            "compared": len(paths), "clip": emb is not None,
            "parts": best_parts,
            "reason": (f"closest to {os.path.basename(best_path)} at "
                       f"{best:.2f}" + ("" if emb is not None else
                                        ", hash only: open_clip is not installed"))}
