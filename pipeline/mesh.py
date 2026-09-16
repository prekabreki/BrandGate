"""The procedural ground: a band of colour fading into paper, made by code, not a model.

    python -m pipeline.mesh --seed 2
    python -m pipeline.mesh --seed 2 --out surfaces/_calibration
    python -m pipeline.mesh --count 40 --seed-start 1 --out surfaces/_pool-mesh

Where this came from (#22, 2026-09-16, docs/process/2026-09-16-*.html): four prompt
versions in one day, each correcting the last, and the designer's favourite frame at the
end of it (krea2 turbo, hero-ground@7, seed 6002) was a smooth mesh gradient with grain,
which is a thing code does exactly. The generator below was fitted to that frame by
measurement, not by eye: the eight stops are its pixels left to right, the paper is its
paper, the vertical falloff of chroma and lightness match its column profiles within a
few points, and the designer ruled the fifth iteration had reached it.

The design of the band, each part answering one of his notes:

- one flow of colour along the top, stops interpolated in OKLab so no seam passes
  through grey ("v6 looks muddy");
- no control points or blobs, so nothing can draw a line ("a dark line going through
  them diagonally", "a large solid blob of purple");
- lightness lifts from the very top while chroma holds, then a gaussian tail with no
  corner, chroma letting go later than lightness ("the seam between white and the
  gradient is too visible", "a very gradual falloff");
- the paper keeps a tenth of the colour above it, so it stays warm;
- one long edge wave across the width ("two big waves, not 3-4");
- film grain heaviest across the falloff, so the last of the colour dissolves into
  grain ("eventually film grained").

The stops and paper live in brand/tokens.json under gradient.ground, so a designer can
move them without opening this file. Every frame is a ledger row (model "mesh"), so a
procedural ground has the same provenance as a generated one and the gate treats both
alike.

The seed moves only what a seed should: the phase of the edge wave, a slow drift in
where each stop sits, and the grain. Two seeds are two frames of one ground, not two
grounds, which is the sameness the brand rule asks for.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKENS = os.path.join(ROOT, "brand", "tokens.json")
SCRATCH = os.path.join(ROOT, "surfaces", "_scratch")
VERSION = 1
W, H = 1664, 944

# sRGB <-> OKLab (Björn Ottosson's matrices). OKLab because a straight line between two
# stops in it stays a colour of about the right lightness the whole way, where the same
# line in linear light dips to grey at the midpoint: that dip was v6's "muddy".
_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]])
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]])
_M1I, _M2I = np.linalg.inv(_M1), np.linalg.inv(_M2)


def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0.0, None)
    return np.clip(np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055), 0, 1) * 255


def hex_to_oklab(h: str) -> np.ndarray:
    return np.cbrt(srgb_to_lin(hex_rgb(h)) @ _M1.T) @ _M2.T


def oklab_to_srgb(o: np.ndarray) -> np.ndarray:
    return lin_to_srgb(((o @ _M2I.T) ** 3) @ _M1I.T)


def load_ground_tokens(path: str = TOKENS) -> dict:
    with open(path, encoding="utf-8") as fh:
        tokens = json.load(fh)
    g = tokens["gradient"]["ground"]
    return {"stops": [s["color"] for s in g["stops"]], "paper": g["paper"],
            "shape": g["shape"]}


def _wave(rng: np.random.Generator, n: int, cycles: float) -> np.ndarray:
    """One slow sine across the width with a random phase: the edge's single long wave."""
    t = np.linspace(0.0, 1.0, n)
    return np.sin(2 * np.pi * (t * cycles + rng.uniform(0, 1)))


def render(seed: int, stops: list[str], paper: str, shape: dict,
           size: tuple[int, int] = (W, H)) -> np.ndarray:
    """One frame as uint8 RGB. Pure function of its arguments."""
    w, h = size
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    xn, yn = xx / w, yy / h

    ok = np.array([hex_to_oklab(s) for s in stops])
    paper_ok = hex_to_oklab(paper)

    # The flow along x. A slow drift per seed so the stops do not sit at the same pixel
    # every frame, plus a slight lean so the flow follows the sweep rather than the frame.
    drift = shape["flow_drift"] * _wave(rng, w, 0.9)[None, :]
    pos = np.clip(xn + drift + shape["flow_lean"] * (yn - 0.3), 0.0, 1.0)
    idx = pos * (len(stops) - 1)
    i0 = np.clip(np.floor(idx).astype(int), 0, len(stops) - 2)
    f = (idx - i0)[..., None]
    colour = ok[i0] * (1 - f) + ok[i0 + 1] * f

    # The edge where paper takes over: a line from edge_left at x=0 falling to the right,
    # carrying one long wave.
    edge = (shape["edge_left"] + shape["edge_slope"] * xn
            + shape["wave"] * _wave(rng, w, shape["wave_cycles"])[None, :])

    # t: 0 in the band, 1 in paper. A gaussian tail starting a little above the edge,
    # so there is no corner anywhere and the last of the colour trails on.
    u = (yn - edge) / shape["falloff"]
    t = 1.0 - np.exp(-np.clip(u + shape["tail_lead"], 0.0, None) ** 2 * shape["tail_rate"])

    # Lightness lifts from the very top (6002 does: L 0.24 at y=0 to 0.45 by y=0.4 at the
    # left), chroma holds to the edge and lets go later than lightness.
    tL = np.clip(yn / (edge + shape["falloff"]), 0.0, 1.0) ** shape["light_ease"]
    L = colour[..., 0] * (1 - tL) + paper_ok[0] * tL
    tc = (t ** shape["chroma_lag"])[..., None]
    target_ab = paper_ok[1:] + shape["tint_floor"] * colour[..., 1:]
    ab = colour[..., 1:] * (1 - tc) + target_ab * tc

    img = oklab_to_srgb(np.concatenate([L[..., None], ab], axis=-1))

    # Film grain, luminance only, heaviest across the falloff.
    weight = shape["grain_floor"] + shape["grain_peak"] * (4.0 * t * (1.0 - t))
    g = rng.normal(0.0, 1.0, (h, w)) * 255.0 * shape["grain"] * weight
    return np.clip(img + g[..., None], 0, 255).astype(np.uint8)


def _repo_relative(path: str) -> str:
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    return os.path.basename(path) if rel.startswith("../") else rel


def generate(seed: int, *, dest_dir: str | None = None, tokens_path: str = TOKENS,
             ledger_path: str | None = None, size: tuple[int, int] = (W, H)) -> tuple[str, dict]:
    """Render one frame, write it, append one ledger row. Returns (path, record)."""
    from pipeline import ledger

    g = load_ground_tokens(tokens_path)
    dest_dir = dest_dir or SCRATCH
    os.makedirs(dest_dir, exist_ok=True)
    run_id = ledger.new_run_id()
    t0 = time.time()
    frame = render(seed, g["stops"], g["paper"], g["shape"], size)
    # Named by seed and generator version, not by run id: the frame is a pure function of
    # those two, so the same seed on another machine writes the same file, and a label in
    # docs/calibration-labels.json keyed on this name finds it there too. The run id
    # lives in the ledger row.
    tag = "" if tuple(size) == (W, H) else f"_{size[0]}x{size[1]}"
    path = os.path.join(dest_dir, f"ground_mesh_{seed}_v{VERSION}{tag}.png")
    Image.fromarray(frame).save(path)
    record = ledger.row(
        run_id=run_id, model="mesh", tier="procedural", prompt_id=f"ground-mesh@{VERSION}",
        prompt_text=json.dumps({"stops": g["stops"], "paper": g["paper"], "shape": g["shape"]},
                               sort_keys=True),
        params={"width": size[0], "height": size[1]}, seed=seed,
        output_path=_repo_relative(path), latency_s=time.time() - t0)
    ledger.append(record, ledger_path)
    return path, record


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m pipeline.mesh",
                                description="Render the procedural ground.")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--count", type=int, default=1, help="render this many seeds from --seed-start")
    p.add_argument("--seed-start", type=int, default=None)
    p.add_argument("--out", default=SCRATCH)
    p.add_argument("--size", default=f"{W}x{H}",
                   help="WxH. The ground is procedural, so a portrait surface gets a portrait "
                        "ground with the whole flow in it rather than a crop of the wide one (#22)")
    a = p.parse_args(argv)
    size = tuple(int(v) for v in a.size.lower().split("x"))
    start = a.seed if a.seed_start is None else a.seed_start
    for s in range(start, start + a.count):
        path, rec = generate(s, dest_dir=a.out, size=size)
        print(f"seed {s}  {rec['latency_s']}s  {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, ROOT)
    raise SystemExit(main())
