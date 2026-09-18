"""The repo-wide re-score: what it picks up, and when it says no.

Scoring itself is tested in test_gate.py. What matters here is the part that
decides *which* files CI looks at and *whether* a run counts as green, because
both of those fail silently: a discovery rule that quietly stops matching, or a
gate that reports a pass it could not measure, leaves a permanently green check
guarding nothing.
"""
from __future__ import annotations

import json
import os

import pytest

from pipeline import recheck


def _surface(tmp_path, name, ground="ground.png", extra=()):
    d = tmp_path / "surfaces" / name / "accepted"
    d.mkdir(parents=True)
    for f in (f"{name}.png", f"{name}-foreground.png", ground, *extra):
        (d / f).write_bytes(b"")
    return d


def _found(tmp_path):
    pattern = os.path.join(str(tmp_path), "surfaces", "*", "accepted")
    return {os.path.basename(t["image"]): t for t in recheck.targets(pattern)}


def test_a_foreground_mask_is_never_itself_a_target(tmp_path):
    _surface(tmp_path, "hero")
    found = _found(tmp_path)
    assert set(found) == {"hero.png", "ground.png"}


def test_a_composed_surface_is_paired_with_its_mask_and_a_ground_is_not(tmp_path):
    d = _surface(tmp_path, "hero")
    found = _found(tmp_path)
    assert found["hero.png"]["mask"] == str(d / "hero-foreground.png")
    assert found["hero.png"]["kind"] == "surface"
    assert found["ground.png"]["mask"] is None
    assert found["ground.png"]["kind"] == "ground"


def test_html_pdf_and_json_beside_a_surface_are_not_scored(tmp_path):
    _surface(tmp_path, "print", extra=("onepager.html", "onepager.pdf", "score.json"))
    assert all(k.endswith(".png") for k in _found(tmp_path))


def test_a_new_surface_needs_no_edit_here_to_be_picked_up(tmp_path):
    # The discovery rule is a property of the files. If this test ever needs a
    # list updated, the rule has grown a list and the point has been lost.
    _surface(tmp_path, "hero")
    before = set(_found(tmp_path))
    _surface(tmp_path, "packaging")
    assert set(_found(tmp_path)) - before == {"packaging.png"}


def test_a_ground_reads_its_own_baseline_not_the_surfaces(tmp_path):
    # ground-story.png is a different ground from ground.png in the same
    # directory, and it is only the score.json that says which is which.
    d = _surface(tmp_path, "social", extra=("ground-story.png", "story.png",
                                            "story-foreground.png"))
    (d / "story.score.json").write_text(json.dumps({
        "verdict": "pass", "on_brand": 0.98, "counts": {"scored": 9},
        "ground": "surfaces/social/accepted/ground-story.png",
        "ground_verdict": {"verdict": "pass", "on_brand": 0.11,
                           "counts": {"scored": 5}},
    }), encoding="utf-8")
    found = _found(tmp_path)
    monkey = recheck.ROOT
    try:
        recheck.ROOT = str(tmp_path)
        assert recheck.baseline(found["ground-story.png"])["on_brand"] == 0.11
        assert recheck.baseline(found["story.png"])["on_brand"] == 0.98
        assert recheck.baseline(found["ground.png"]) is None
    finally:
        recheck.ROOT = monkey


# The exit code is the whole product. Everything above only decides what goes
# into these rows.

def _row(verdict="pass", on_brand=0.99, was=0.99, scored=9, was_scored=9, errored=()):
    return {"image": "surfaces/hero/accepted/hero.png", "kind": "surface",
            "verdict": verdict, "on_brand": on_brand, "novelty": 1.0,
            "failed_rules": [] if verdict == "pass" else ["gradient.03"],
            "breakdown": [{"rule": "gradient.03", "check": "band", "score": 0.4,
                           "passed": verdict == "pass", "reason": "the band is flat",
                           "detail": {}}],
            "not_applicable": [], "errored": list(errored), "manual": [],
            "missing_dependencies": sorted({e["dependency"] for e in errored
                                            if e.get("dependency")}),
            "counts": {"scored": scored, "failed": 0, "not_applicable": 0,
                       "manual": 0, "errored": len(errored)},
            "was": {"verdict": "pass", "on_brand": was, "scored": was_scored}}


def test_a_failure_names_the_file_and_the_rule_in_the_summary():
    md = recheck.table([_row(verdict="fail", on_brand=0.6)])
    assert "1 of 1 shipped surfaces no longer pass" in md
    assert "surfaces/hero/accepted/hero.png" in md
    assert "gradient.03" in md and "the band is flat" in md
    assert "something moved under it" in md


def test_a_score_that_moved_is_reported_even_though_it_still_passes():
    assert _delta_of(_row(on_brand=0.99, was=0.99)) == "same"
    assert _delta_of(_row(on_brand=0.90, was=0.99)) == "-0.0900"


def test_a_mean_over_a_different_rule_set_is_not_reported_as_drift():
    # Without cairo six rules error and every surface reads ~0.02 lower. That
    # is a smaller gate, not a moved brand, and printing a subtraction there
    # invents a drift story out of a missing package.
    d = _delta_of(_row(on_brand=0.9532, was=0.9719, scored=3, was_scored=5))
    assert d == "5->3 rules, not comparable"


def _delta_of(row):
    return recheck._delta(row)


@pytest.mark.parametrize("rows,argv,expected", [
    ([_row()], [], 0),
    ([_row(verdict="fail")], [], 1),
    # A gate missing six of its checks reports a pass it did not measure. That
    # is the #17 silence, and it is worth its own exit code: 1 is the brand,
    # 2 is this tool.
    ([_row(errored=[{"rule": "mark.01", "check": "mark", "error": "boom",
                     "dependency": "cairosvg"}])], [], 2),
    ([_row(errored=[{"rule": "mark.01", "check": "mark", "error": "boom",
                     "dependency": "cairosvg"}])], ["--allow-missing-deps"], 0),
    # The brand failure outranks the missing dependency: a red check should
    # name the surface, not the package.
    ([_row(verdict="fail", errored=[{"rule": "mark.01", "check": "mark",
                                     "error": "boom"}])], [], 1),
])
def test_exit_codes(monkeypatch, rows, argv, expected):
    monkeypatch.setattr(recheck, "targets", lambda *_, **__: [{"image": "x.png"}])
    monkeypatch.setattr(recheck, "run", lambda *_, **__: rows)
    assert recheck.main(argv) == expected


def test_no_surfaces_at_all_is_an_error_not_a_clean_run(monkeypatch):
    # A glob that stops matching would otherwise be the quietest possible way
    # to switch this check off while it keeps reporting green.
    monkeypatch.setattr(recheck, "targets", lambda *_, **__: [])
    assert recheck.main([]) == 2
