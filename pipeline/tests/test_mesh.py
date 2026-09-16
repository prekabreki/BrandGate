"""pipeline.mesh: the procedural ground (#22)."""
from __future__ import annotations

import json
import os

import numpy as np
import pytest

from pipeline import ledger, mesh

SMALL = (416, 236)  # same aspect as the real frame, a sixteenth of the pixels


@pytest.fixture(scope="module")
def g():
    return mesh.load_ground_tokens()


def test_tokens_carry_the_ground(g):
    assert len(g["stops"]) == 8 and all(s.startswith("#") for s in g["stops"])
    assert g["paper"].startswith("#")
    for k in ("edge_left", "falloff", "wave", "grain", "tint_floor", "chroma_lag"):
        assert k in g["shape"], k


def test_deterministic_for_a_seed(g):
    a = mesh.render(7, g["stops"], g["paper"], g["shape"], SMALL)
    b = mesh.render(7, g["stops"], g["paper"], g["shape"], SMALL)
    assert a.shape == (SMALL[1], SMALL[0], 3) and a.dtype == np.uint8
    assert np.array_equal(a, b)


def test_a_seed_moves_the_edge_not_the_colour(g):
    """Two seeds are two frames of ONE ground: the top-left stays the first stop's colour
    and the bottom-right stays paper, whatever the seed does to the edge in between."""
    a = mesh.render(1, g["stops"], g["paper"], g["shape"], SMALL).astype(int)
    b = mesh.render(2, g["stops"], g["paper"], g["shape"], SMALL).astype(int)
    assert not np.array_equal(a, b)
    h, w = a.shape[:2]
    tl = lambda im: im[: h // 12, : w // 12].reshape(-1, 3).mean(axis=0)  # noqa: E731
    br = lambda im: im[-h // 6:, -w // 4:].reshape(-1, 3).mean(axis=0)  # noqa: E731
    assert np.abs(tl(a) - tl(b)).max() < 6
    assert np.abs(br(a) - br(b)).max() < 6
    paper = mesh.hex_rgb(g["paper"])
    assert np.abs(br(a) - paper).max() < 14, (br(a), paper)


def test_the_falloff_is_long_and_has_no_corner(g):
    """The designer's two notes on A3/A4: the fade must run over about half the frame
    and its second derivative must stay small (no seam). Measured on the OKLab chroma
    of the leftmost column band."""
    im = mesh.render(3, g["stops"], g["paper"], g["shape"], SMALL).astype(np.float64)
    ok = np.cbrt(mesh.srgb_to_lin(im) @ mesh._M1.T) @ mesh._M2.T
    C = np.hypot(ok[..., 1], ok[..., 2])
    col = C[:, : SMALL[0] // 20].mean(axis=1)
    # smooth the grain out before differentiating
    k = 9
    col = np.convolve(col, np.ones(k) / k, mode="valid")
    top = col[:10].mean()
    rel = col / top
    below_half = np.argmax(rel < 0.5) / len(rel)
    near_floor = np.argmax(rel < 0.15) / len(rel)
    assert 0.35 < below_half < 0.7, below_half
    assert near_floor - below_half > 0.15, "the tail is too short"
    d2 = np.abs(np.diff(col, 2))
    assert d2.max() < 0.02 * top, "a corner in the falloff"


def test_generate_writes_a_frame_and_one_ledger_row(tmp_path, g):
    led = tmp_path / "ledger.jsonl"
    path, rec = mesh.generate(11, dest_dir=str(tmp_path / "out"), ledger_path=str(led), size=SMALL)
    # a non-default size is named into the file, so a portrait ground never overwrites the wide one
    assert os.path.exists(path) and os.path.basename(path) == f"ground_mesh_11_v{mesh.VERSION}_{SMALL[0]}x{SMALL[1]}.png"
    rows = [json.loads(line) for line in led.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    r = rows[0]
    assert r["model"] == "mesh" and r["tier"] == "procedural" and r["seed"] == 11
    assert r["prompt_id"] == f"ground-mesh@{mesh.VERSION}"
    assert json.loads(r["prompt_text"])["stops"] == g["stops"]
    assert r["error"] is None
    assert set(r) == set(ledger.row(run_id="x", model="m", tier="t", prompt_id="p",
                                    prompt_text="", params={}, seed=0))
