"""The drift run's bookkeeping: seeds, the frames it finds, and the claims it makes.

The generation and the gating are covered elsewhere (test_pool, test_gate). What
is only testable here is the part that decides whether the run is a controlled
comparison at all, because that is a claim the figure and the scorecard make in
words, and a wrong one reads exactly like a right one.
"""
from __future__ import annotations

import json

from runs import drift


def _touch(root, model, seeds, prompt="hero-ground", tier="turbo"):
    d = root / model
    d.mkdir(parents=True, exist_ok=True)
    for s in seeds:
        (d / f"{prompt}_{tier}_{s}_abc123def456_00001_.png").write_bytes(b"")
    return d


def _rows(model, seeds, on_brand=0.9, verdict="pass", failed=()):
    return [{"model": model, "tier": "turbo", "seed": s, "image": f"{model}/{s}.png",
             "verdict": verdict, "on_brand": on_brand, "novelty": 0.4,
             "failed_rules": list(failed), "counts": {"scored": 9},
             "reasons": {f: f"{model} said so at seed {s}" for f in failed},
             "errored": []}
            for s in seeds]


def test_both_arms_are_given_the_same_seeds():
    assert drift.seeds(4, 4000) == [4000, 4001, 4002, 4003]


def test_drift_seeds_do_not_collide_with_the_pools_or_the_calibration_set():
    # A shared seed makes the ledger ambiguous: two rows, same model, same
    # tier, same seed, made to answer different questions.
    from runs import pool
    assert drift.SEED_START >= pool.SEED_START + 1000
    assert drift.SEED_START >= 4000  # calibration is the 1000s


def test_frames_are_found_by_seed_not_by_directory_order(tmp_path):
    _touch(tmp_path, "krea2", [4002, 4000, 4001])
    assert [s for s, _ in drift.frames("krea2", str(tmp_path))] == [4000, 4001, 4002]


def test_a_stray_file_in_an_arm_is_ignored_rather_than_mis_seeded(tmp_path):
    d = _touch(tmp_path, "krea2", [4000])
    (d / "notes.png").write_bytes(b"")
    (d / "hero-ground_turbo_notanumber_x_00001_.png").write_bytes(b"")
    assert [s for s, _ in drift.frames("krea2", str(tmp_path))] == [4000]


def test_the_other_tiers_frames_are_not_swept_into_the_arm(tmp_path):
    _touch(tmp_path, "krea2", [4000, 4001])
    _touch(tmp_path, "krea2", [4000, 4001], tier="raw")
    assert len(drift.frames("krea2", str(tmp_path), tier="turbo")) == 2


# The precondition. Everything the run claims rests on it.

def test_matched_arms_are_recognised_as_a_controlled_comparison():
    rows = _rows("krea2", [4000, 4001]) + _rows("flux2", [4000, 4001])
    assert drift.shared_seeds(rows) is True


def test_unmatched_arms_are_not():
    rows = _rows("krea2", [4000, 4001]) + _rows("flux2", [4002, 4003])
    assert drift.shared_seeds(rows) is False


def test_an_arm_that_lost_a_frame_to_a_refusal_is_not_matched():
    # flux2 refused one seed, so its arm is 47 frames to krea2's 48. The
    # distributions are still worth looking at, but "only the model changed"
    # is no longer true and the scorecard has to say which seed went missing.
    rows = _rows("krea2", [4000, 4001, 4002]) + _rows("flux2", [4000, 4001])
    assert drift.shared_seeds(rows) is False


def test_the_scorecard_says_so_when_the_arms_are_not_matched():
    cfg = {"verdict": {"on_brand_min": 0.75, "novelty_min": 0.12}}
    md = drift.scorecard(_rows("krea2", [4000]) + _rows("flux2", [4001]), cfg)
    assert "do not share a seed set" in md
    assert "not a drift result" in md


def test_a_matched_run_makes_no_such_disclaimer():
    cfg = {"verdict": {"on_brand_min": 0.75, "novelty_min": 0.12}}
    md = drift.scorecard(_rows("krea2", [4000]) + _rows("flux2", [4000]), cfg)
    assert "do not share a seed set" not in md


def test_the_scorecard_reports_a_rules_hit_rate_per_arm_not_a_total():
    # "gradient.03 fired 7 times" is not the finding. "7 of 7 in one arm and 0
    # of 8 in the other" is.
    cfg = {"verdict": {"on_brand_min": 0.75, "novelty_min": 0.12}}
    rows = (_rows("krea2", [4000, 4001]) +
            _rows("flux2", [4000, 4001], on_brand=0.6, verdict="fail",
                  failed=["gradient.03"]))
    md = drift.scorecard(rows, cfg)
    assert "| `gradient.03` | 0/2 | 2/2 |" in md
    assert "| pass rate | 100% | 0% |" in md


def test_the_example_reason_is_stable_across_reruns():
    cfg = {"verdict": {"on_brand_min": 0.75, "novelty_min": 0.12}}
    rows = _rows("flux2", [4001, 4000], verdict="fail", failed=["gradient.03"])
    first = drift.scorecard(rows, cfg)
    assert drift.scorecard(list(reversed(rows)), cfg) == first
    assert "at seed 4000" in first  # the lowest seed, not whichever was last


def test_the_ledger_is_read_by_model_tier_and_seed(tmp_path):
    # Not by time. A re-run of one arm appends new rows for the same seeds,
    # and the scorecard must not average a dead first attempt into the latency.
    p = tmp_path / "ledger.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in [
        {"model": "krea2", "tier": "turbo", "seed": 4000, "latency_s": 15.0},
        {"model": "krea2", "tier": "raw", "seed": 4000, "latency_s": 180.0},
        {"model": "krea2", "tier": "turbo", "seed": 9999, "latency_s": 99.0},
        {"model": "sdxl", "tier": "turbo", "seed": 4000, "latency_s": 4.0},
    ]), encoding="utf-8")
    led = drift.ledger_rows(["krea2"], [4000], "turbo", str(p))
    assert [r["latency_s"] for r in led["krea2"]] == [15.0]


def test_a_failed_generation_is_counted_but_never_averaged_into_latency():
    led = [{"latency_s": 15.0, "error": None}, {"latency_s": 900.0, "error": "timeout"}]
    s = drift.summarise(_rows("krea2", [4000]), led)
    assert s["generation_errors"] == 1
    assert s["latency_mean_s"] == 15.0


def test_an_unmetered_local_run_says_so_rather_than_reporting_zero_cost():
    cfg = {"verdict": {"on_brand_min": 0.75, "novelty_min": 0.12}}
    md = drift.scorecard(_rows("krea2", [4000]), cfg, {"krea2": [{"latency_s": 15.0}]})
    assert "local, unmetered" in md
    assert "$0.0000" not in md


def test_novelty_is_measured_against_the_accepted_grounds_not_the_arms_own_frames():
    # Within an arm, novelty answers "how varied is this model", which is a
    # different question, and it makes the two arms incomparable because each
    # would be scored against a different reference.
    assert "accepted" in drift.REFERENCE_GLOB
    assert "ground" in drift.REFERENCE_GLOB
    assert "_drift" not in drift.REFERENCE_GLOB
    found = drift.reference_paths()
    assert found, "the repo ships no accepted grounds to measure novelty against"
    assert all("accepted" in p for p in found)
