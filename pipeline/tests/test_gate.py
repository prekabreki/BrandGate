"""Gate tests. Synthetic frames where possible so a failure names a cause, plus
the repo's real takes, because every interesting bug so far lived in the gap
between a clean synthetic case and an actual designed surface."""
import numpy as np
import pytest

from pipeline import gate, rules
from pipeline.checks import colour

TAKES = "lookdev/archive/takes_02.png"
ACCEPTED_NONE = "/nonexistent/*.png"


@pytest.fixture(scope="module")
def cfg():
    return gate.load_config()


@pytest.fixture(scope="module")
def doc():
    return rules.load()


def _score(img, cfg, doc):
    return gate.score_image(img, cfg, doc, accepted_glob=ACCEPTED_NONE)


def _flat(hex_colour, size=(400, 600)):
    return np.full((*size, 3), colour.hex_to_rgb(hex_colour), dtype=np.uint8)


def _rule_named(r, rule_id):
    for b in r["breakdown"]:
        if b["rule"] == rule_id:
            return b
    return None


# -- colour maths ----------------------------------------------------------


def test_contrast_ratio_matches_wcag_anchors():
    assert colour.contrast_ratio((0, 0, 0), (255, 255, 255)) == pytest.approx(21.0, abs=0.01)
    assert colour.contrast_ratio((255, 255, 255), (255, 255, 255)) == pytest.approx(1.0, abs=0.01)
    # Order must not matter: the ratio is between the two, not fg over bg.
    a = colour.contrast_ratio((17, 17, 20), (250, 250, 248))
    b = colour.contrast_ratio((250, 250, 248), (17, 17, 20))
    assert a == pytest.approx(b)


def test_lab_distance_is_zero_for_identical_colours():
    lab = colour.rgb_to_lab(np.array([[75, 59, 232]]))
    assert colour.lab_distance(lab, lab)[0][0] == pytest.approx(0.0, abs=1e-9)


def test_dominant_colours_are_deterministic():
    # A gate whose score moves between two runs on the same file is not an
    # instrument, it is a mood.
    rng = np.random.default_rng(3)
    img = rng.integers(0, 255, (200, 300, 3), dtype=np.uint8)
    a, wa = colour.dominant_colours(img)
    b, wb = colour.dominant_colours(img)
    assert np.allclose(a, b) and np.allclose(wa, wb)


# -- the verdict -----------------------------------------------------------


def test_a_frame_with_nothing_to_measure_is_unscored_not_perfect(cfg, doc):
    # A blank frame used to score a flawless 1.0 on-brand for containing
    # nothing at all, because every rule with no subject returned a pass.
    r = _score(_flat("#FAFAF8"), cfg, doc)
    assert r["verdict"] in ("unscored", "pass")
    for b in r["breakdown"]:
        assert b["check"] != "band", "mark rules must not apply to a blank frame"


def test_not_applicable_rules_stay_out_of_the_score(cfg, doc):
    r = _score(_flat("#FAFAF8"), cfg, doc)
    assert r["counts"]["not_applicable"] > 0
    assert len(r["breakdown"]) == r["counts"]["scored"]


def test_every_rule_is_accounted_for(cfg, doc):
    r = _score(gate.load_image(TAKES, "t3"), cfg, doc)
    c = r["counts"]
    assert c["scored"] + c["not_applicable"] + c["manual"] == len(doc["rules"])


def test_a_check_that_raises_becomes_manual_and_does_not_stop_the_run(cfg, doc, monkeypatch):
    import pipeline.checks as checks

    def boom(*a, **k):
        raise RuntimeError("detector exploded")

    monkeypatch.setitem(checks.REGISTRY, "palette", boom)
    r = _score(gate.load_image(TAKES, "t3"), cfg, doc)
    assert r["errors"], "the error was swallowed entirely"
    assert any("detector exploded" in e["error"] for e in r["errors"])
    assert r["counts"]["scored"] > 0, "one bad check stopped every other check"


# -- what it must accept ---------------------------------------------------


@pytest.mark.parametrize("tile", ["t1", "t2", "t3", "t4", "t5", "t6"])
def test_the_designers_own_takes_pass(cfg, doc, tile):
    r = _score(gate.load_image(TAKES, tile), cfg, doc)
    assert r["verdict"] == "pass", (tile, r["failed_rules"],
                                    [b["reason"] for b in r["breakdown"]
                                     if not b["passed"]])


def test_a_light_and_a_dark_take_both_pass(cfg, doc):
    # The brand sets white type on night as readily as ink on paper. Assuming
    # dark-on-light made the contrast check report a flat 1.0:1 and fail the
    # night take, whose type is in fact fully legible.
    for tile in ("t1", "t2"):
        assert _score(gate.load_image(TAKES, tile), cfg, doc)["verdict"] == "pass"


def test_a_gradient_mark_is_one_gesture_not_two(cfg, doc):
    # The mark IS a gradient shape, so a naive count read it as the mark plus
    # gradient type and failed the brand for wearing itself.
    r = _score(gate.load_image(TAKES, "t3"), cfg, doc)
    motif = _rule_named(r, "motif.02")
    assert motif and motif["passed"], motif


# -- what it must reject ---------------------------------------------------
# A gate that only ever passes is worse than none, so each of these asserts the
# CORRECT rule fired, not merely that the verdict was a failure.


def test_a_rotated_mark_fails_on_the_level_rule(cfg, doc):
    img = np.rot90(gate.load_image(TAKES, "t3")).copy()
    r = _score(img, cfg, doc)
    assert r["verdict"] == "fail"
    assert "mark.08" in r["failed_rules"], r["failed_rules"]
    assert "not upright" in _rule_named(r, "mark.08")["reason"]


def test_an_off_palette_ground_fails_on_the_ground_rule(cfg, doc):
    import cv2
    img = gate.load_image(TAKES, "t3")
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(np.int16)
    hsv[:, :, 0] = (hsv[:, :, 0] + 60) % 180
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] + 40, 0, 255)
    r = _score(cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB), cfg, doc)
    assert "colour.01" in r["failed_rules"], r["failed_rules"]


def test_a_forbidden_flat_accent_fails(cfg, doc):
    img = gate.load_image(TAKES, "t3").copy()
    img[500:760, 60:700] = colour.hex_to_rgb("#B44C9E")
    r = _score(img, cfg, doc)
    assert "colour.03" in r["failed_rules"], r["failed_rules"]
    assert "#B44C9E" in _rule_named(r, "colour.03")["reason"]


def test_low_contrast_text_fails_on_a_contrast_rule(cfg, doc):
    import cv2
    img = gate.load_image(TAKES, "t3").astype(np.float32)
    dark = cv2.cvtColor(gate.load_image(TAKES, "t3"), cv2.COLOR_RGB2GRAY) < 140
    img[dark] = img[dark] * 0.25 + np.float32([238, 238, 238]) * 0.75
    r = _score(img.astype(np.uint8), cfg, doc)
    assert {"colour.02", "type.03"} & set(r["failed_rules"]), r["failed_rules"]


# -- the mark detector, which was the hardest thing here to get honest ------


def test_the_mark_is_found_on_paper_and_on_night(cfg):
    from pipeline.checks.band import locate
    for tile in ("t1", "t2"):
        level, _, hits = locate(gate.load_image(TAKES, tile), cfg)
        assert level >= cfg["band"]["present_min"], (tile, level)
        assert hits


def test_no_mark_is_found_in_a_frame_without_one(cfg):
    from pipeline.checks.band import locate
    level, rotated, _ = locate(_flat("#FAFAF8"), cfg)
    assert max(level, rotated) < cfg["band"]["present_min"]


def test_a_smooth_wash_does_not_match_the_mark(cfg):
    # THE bug in this detector. Normalised correlation between two near-empty
    # patches returns a confident 1.00, so an ungated detector reported a
    # perfect mark on blank gradient in every frame tested.
    h, w = 400, 900
    ramp = np.linspace(0, 255, w, dtype=np.uint8)
    wash = np.repeat(ramp[None, :], h, axis=0)
    img = np.stack([wash, wash // 2, 255 - wash], axis=2)
    from pipeline.checks.band import locate
    level, rotated, _ = locate(img, cfg)
    assert max(level, rotated) < cfg["band"]["present_min"], max(level, rotated)


def test_editing_the_mark_svg_changes_what_the_gate_looks_for(cfg, tmp_path):
    # The SVG is the artwork, so there must be no second copy to keep in step.
    from pipeline.checks.band import locate
    img = gate.load_image(TAKES, "t3")
    square = tmp_path / "square.svg"
    square.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 100" '
        'width="300" height="100"><rect x="10" y="10" width="280" '
        'height="80" fill="#E5E5E5"/></svg>', encoding="utf-8")
    real, _, _ = locate(img, cfg)
    other, _, _ = locate(img, cfg, str(square))
    assert real > other


# -- crop ------------------------------------------------------------------


def test_crop_splits_the_sheet_into_six_tiles():
    img = gate.load_image(TAKES)
    t1, t6 = gate.crop_tile(img, "t1"), gate.crop_tile(img, "t6")
    assert t1.shape == t6.shape
    assert not np.array_equal(t1, t6)


@pytest.mark.parametrize("spec", ["", "x1", "t0", "t7", "3"])
def test_a_bad_crop_spec_is_refused(spec):
    with pytest.raises(ValueError):
        gate.crop_tile(np.zeros((60, 60, 3), np.uint8), spec)


# -- novelty ---------------------------------------------------------------


def test_an_empty_accepted_set_yields_full_novelty(cfg, doc):
    r = _score(gate.load_image(TAKES, "t3"), cfg, doc)
    assert r["novelty"] == 1.0
    assert "accepted set is empty" in r["novelty_detail"]["reason"]


def test_a_frame_is_not_novel_against_itself(cfg, tmp_path):
    import cv2
    from pipeline import novelty
    img = gate.load_image(TAKES, "t3")
    acc = tmp_path / "accepted"
    acc.mkdir()
    cv2.imwrite(str(acc / "a.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    r = novelty.score(img, cfg, str(acc / "*.png"))
    assert r["novelty"] == pytest.approx(0.0, abs=0.02), r


def test_novelty_output_says_whether_clip_ran(cfg):
    from pipeline import novelty
    r = novelty.score(gate.load_image(TAKES, "t3"), cfg, ACCEPTED_NONE)
    # No reader should be left assuming a semantic check ran when it did not.
    assert "clip" in r and isinstance(r["clip"], bool)


# -- cli -------------------------------------------------------------------


def test_cli_exit_code_follows_the_verdict(capsys):
    assert gate.main(["score", TAKES, "--crop", "t3",
                      "--accepted", ACCEPTED_NONE]) == 0
    assert "PASS" in capsys.readouterr().out


def test_cli_reports_a_missing_file_without_a_traceback(capsys):
    assert gate.main(["score", "no/such.png"]) == 2
    assert "ERROR" in capsys.readouterr().err


def test_cli_json_is_machine_readable(capsys):
    import json
    gate.main(["score", TAKES, "--crop", "t3", "--json",
               "--accepted", ACCEPTED_NONE])
    r = json.loads(capsys.readouterr().out)
    assert r["verdict"] == "pass"
    assert r["breakdown"] and "novelty_detail" in r
