"""The ident renderer keeps a frame only when the page's readiness marker is black.

The first cut trusted that a screenshot on disk was a finished picture; four of 180
frames were captured before the anime.js module had run and the mark blinked out for
133 ms in the clip. render_frame reads the two-row marker under the frame, renders
again while it is white, and refuses after TRIES rather than keep a blind frame.
"""
import pytest
from PIL import Image

from surfaces.motion import render as R


def _fake_renderer(monkeypatch, marker_colours):
    """Stand in for lookdev.render.render: writes a 1920 by 1082 image whose marker
    rows take the next colour from marker_colours on each call."""
    calls = []
    colours = list(marker_colours)

    def fake(html, out, w, h, binary, wait_ms, query=""):
        calls.append(query)
        im = Image.new("RGB", (w, h), (200, 120, 160))
        im.paste(colours.pop(0) if colours else colours_last, (0, R.H, w, h))
        Image.Image.save(im, out)

    colours_last = marker_colours[-1]
    monkeypatch.setattr(R.renderer, "render", fake)
    return calls


def test_ready_frame_is_cropped_to_the_frame(tmp_path, monkeypatch):
    calls = _fake_renderer(monkeypatch, [(0, 0, 0)])
    out = tmp_path / "f.png"
    R.render_frame(str(out), "chrome", 10, "?t=766")
    im = Image.open(out)
    assert im.size == (R.W, R.H), "the marker rows must be cropped off"
    assert im.getpixel((5, R.H - 1)) == (200, 120, 160), "the last kept row is picture, not marker"
    assert len(calls) == 1


def test_white_marker_renders_again_then_keeps(tmp_path, monkeypatch):
    calls = _fake_renderer(monkeypatch, [(255, 255, 255), (255, 255, 255), (0, 0, 0)])
    out = tmp_path / "f.png"
    R.render_frame(str(out), "chrome", 10, "?t=766")
    assert len(calls) == 3
    assert Image.open(out).size == (R.W, R.H)


def test_never_ready_refuses_rather_than_keep_a_blind_frame(tmp_path, monkeypatch):
    _fake_renderer(monkeypatch, [(255, 255, 255)] * R.TRIES)
    out = tmp_path / "f.png"
    with pytest.raises(SystemExit, match="never reported ready"):
        R.render_frame(str(out), "chrome", 10, "?t=766")
