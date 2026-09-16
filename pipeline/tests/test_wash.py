"""The wash check: is a generated ground softened the way gradient.03 says?

Synthetic frames, each breaking exactly one thing, so a failure names the
measurement that caught it. The 27 designer-labelled frames are the other half
of this file's job and live in test_wash_calibration.py.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from pipeline import gate
from pipeline.checks import colour, wash

W, H = 640, 360
PAPER, NIGHT = "#FAFAF8", "#0D0B18"
STOPS = {"indigo": "#4B3BE8", "magenta": "#B44C9E", "rose": "#D9628A"}


@pytest.fixture(scope="module")
def cfg():
    return gate.load_config()


def _rule(stops=("indigo", "magenta", "rose")):
    return {"id": "gradient.03", "check": "wash",
            "params": {"stops": [STOPS[s] for s in stops]}}


def _orb(canvas, cx, cy, r, hex_colour, hard=False):
    """Paint one orb. Soft: a wide gaussian falloff. Hard: a flat disc."""
    yy, xx = np.mgrid[0:canvas.shape[0], 0:canvas.shape[1]]
    d2 = (xx - cx) ** 2 + (yy - cy) ** 2
    alpha = (d2 <= r * r).astype(np.float32) if hard else np.exp(-d2 / (2 * (r * 0.55) ** 2))
    col = np.array(colour.hex_to_rgb(hex_colour), dtype=np.float32)
    canvas[:] = canvas * (1 - alpha[..., None]) + col * alpha[..., None]


def _ground(stops=("indigo", "magenta", "rose"), hard=False, paper=PAPER, size=(W, H),
            dark_boost=0.0):
    w, h = size
    canvas = np.full((h, w, 3), colour.hex_to_rgb(paper), dtype=np.float32)
    xs = np.linspace(0.2, 0.8, len(stops))
    for x, s in zip(xs, stops):
        _orb(canvas, int(x * w), h // 2, int(0.22 * w), STOPS[s], hard=hard)
    # the paper veil the rule asks for: a real wash is a tint, not the raw stop
    paper_col = np.array(colour.hex_to_rgb(paper), dtype=np.float32)
    canvas = canvas * 0.45 + paper_col * 0.55
    if dark_boost:
        # the "too dark" rejects: a deep, unveiled indigo orb where the tint should be
        _orb(canvas, int(0.2 * w), h // 2, int(0.2 * w), STOPS["indigo"])
    rng = np.random.default_rng(7)
    canvas += rng.normal(0, 2.0, canvas.shape).astype(np.float32)  # film grain
    return np.clip(canvas, 0, 255).astype(np.uint8)


def test_a_soft_three_stop_wash_passes(cfg):
    f = wash.check(_ground(), _rule(), cfg, {})
    assert f.applicable and f.passed, f.reason
    assert f.detail["dark_chroma"] < cfg["wash"]["dark_chroma_max"]
    assert f.detail["edge_p99"] < cfg["wash"]["edge_max"]


def test_hard_discs_fail_on_the_edge_measure(cfg):
    f = wash.check(_ground(hard=True), _rule(), cfg, {})
    assert f.applicable and not f.passed
    assert "edge" in f.reason.lower() or "separate" in f.reason.lower(), f.reason
    assert f.detail["edge_p99"] >= cfg["wash"]["edge_max"]


def test_saturated_darks_fail_on_dark_chroma(cfg):
    soft = wash.check(_ground(), _rule(), cfg, {})
    boosted = wash.check(_ground(dark_boost=1.0), _rule(), cfg, {})
    assert boosted.detail["dark_chroma"] > soft.detail["dark_chroma"]
    assert not boosted.passed
    assert "dark" in boosted.reason.lower(), boosted.reason


def test_a_missing_stop_fails_and_is_named(cfg):
    f = wash.check(_ground(stops=("indigo", "magenta", "magenta")), _rule(), cfg, {})
    assert not f.passed
    assert "#D9628A" in f.reason or "rose" in f.reason.lower(), f.reason


def test_night_ground_is_not_applicable(cfg):
    f = wash.check(_ground(paper=NIGHT), _rule(), cfg, {})
    assert not f.applicable
    assert "night" in f.reason.lower()


def test_a_flat_surface_with_a_small_mark_is_not_applicable(cfg):
    img = np.full((H, W, 3), colour.hex_to_rgb(PAPER), dtype=np.uint8)
    cv2.rectangle(img, (40, 40), (140, 90), colour.hex_to_rgb(STOPS["indigo"]), -1)
    f = wash.check(img, _rule(), cfg, {})
    assert not f.applicable
    assert "wash" in f.reason.lower()


def test_no_stops_in_the_rule_is_not_applicable(cfg):
    f = wash.check(_ground(), {"id": "x", "check": "wash", "params": {}}, cfg, {})
    assert not f.applicable


def test_deterministic(cfg):
    img = _ground()
    a = wash.check(img, _rule(), cfg, {}).detail
    b = wash.check(img, _rule(), cfg, {}).detail
    for k in ("dark_chroma", "edge_p99", "stop_share"):
        assert a[k] == b[k]


def test_resolution_invariant(cfg):
    big = _ground(size=(1280, 720))
    small = cv2.resize(big, (640, 360), interpolation=cv2.INTER_AREA)
    a = wash.check(big, _rule(), cfg, {})
    b = wash.check(small, _rule(), cfg, {})
    assert abs(a.score - b.score) < 0.05, (a.score, b.score)
    assert a.passed == b.passed


def test_the_gate_carries_the_wash_finding(cfg):
    doc = gate.rules_mod.load()
    r = gate.score_image(_ground(), cfg, doc)
    rows = [b for b in r["breakdown"] if b["rule"] == "gradient.03"]
    assert rows and rows[0]["check"] == "wash", r["manual"]


def test_a_dark_splotch_is_measured_as_mass_not_saturation(cfg):
    """#22: the designer refused turbo 2083 for 'a big splotch of black'. dark_chroma
    measures how saturated the darks are, not how much of the frame they cover, so a
    near-black, near-grey mass sailed through. dark_mass is the share of the wash
    area sitting below the dark bar."""
    soft = wash.measure(_ground(), list(STOPS.values()), cfg["wash"])
    canvas = _ground().astype(np.float32)
    _orb(canvas, int(0.3 * W), H // 2, int(0.18 * W), "#141220")  # a near-black, unsaturated mass
    splotched = np.clip(canvas, 0, 255).astype(np.uint8)
    m = wash.measure(splotched, list(STOPS.values()), cfg["wash"])
    assert soft["dark_mass"] < 0.01, soft
    assert m["dark_mass"] > 0.03, m
    assert m["dark_chroma"] < cfg["wash"]["dark_chroma_max"],         "the splotch is grey: the existing dark_chroma bar must NOT be what catches it"
    assert 0 <= m["L_p02"] < soft["L_p02"]
