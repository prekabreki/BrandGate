"""The sameness sweep (#10): the parts that do not need a 200-frame pool."""
import hashlib
import json
import os

import numpy as np
import pytest

from pipeline import gate, rules
from runs import sameness

TAKES = "lookdev/archive/takes_02.png"


def test_the_table_has_five_steps_and_every_knob_tightens_monotonically():
    steps = sameness.build_steps(5)
    assert steps == sameness.STEPS
    assert steps[sameness.SHIPPED_STEP] == {
        "verdict.on_brand_min": 0.75, "palette.forbid_mass": 0.04,
        "wash.dark_chroma_max": 56.2, "wash.edge_max": 14.3,
        "wash.stop_share_min": 0.06}, "step 2 must be the shipped gate.toml"
    assert "palette.tolerance_lab" not in sameness.KNOBS, \
        "tolerance_lab tightens colour.01 and loosens colour.03; it cannot be swept"
    rising = {"verdict.on_brand_min", "wash.stop_share_min"}
    for k in sameness.KNOBS:
        seq = [s[k] for s in steps]
        assert seq == sorted(seq, reverse=k not in rising), (k, seq)
        assert len(set(seq)) == len(seq), f"{k} repeats a value, a step does nothing"


def test_the_shipped_step_matches_the_file_it_claims_to_be():
    cfg = gate.load_config()
    for dotted, value in sameness.STEPS[sameness.SHIPPED_STEP].items():
        section, key = dotted.split(".")
        assert cfg[section][key] == value, f"{dotted}: table says {value}, gate.toml says {cfg[section][key]}"


def test_other_step_counts_interpolate_between_the_ends():
    three = sameness.build_steps(3)
    assert three[0] == sameness.STEPS[0] and three[-1] == sameness.STEPS[-1]
    assert three[1]["palette.forbid_mass"] == pytest.approx(0.06)
    with pytest.raises(ValueError):
        sameness.build_steps(1)


def test_override_touches_neither_the_config_nor_the_file():
    before = hashlib.sha256(open(gate.GATE_TOML, "rb").read()).hexdigest()
    cfg = gate.load_config()
    snapshot = json.dumps(cfg, sort_keys=True)
    tight = sameness.override(cfg, sameness.STEPS[-1])
    assert tight["palette"]["forbid_mass"] == 0.02
    assert tight["palette"]["tolerance_lab"] == cfg["palette"]["tolerance_lab"]
    assert json.dumps(cfg, sort_keys=True) == snapshot, "override mutated the base config"
    img = np.full((120, 200, 3), 250, dtype=np.uint8)
    gate.score_image(img, tight, rules.load(), accepted_paths=[])
    after = hashlib.sha256(open(gate.GATE_TOML, "rb").read()).hexdigest()
    assert before == after, "the sweep wrote brand/gate.toml"


def test_override_refuses_a_key_gate_toml_does_not_have():
    with pytest.raises(KeyError):
        sameness.override(gate.load_config(), {"wash.made_up": 1.0})


def test_labelled_frames_resolve_takes_tiles_and_files(tmp_path):
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"labels": {"takes_02_t3": "on", "a_frame": "off"}}),
                      encoding="utf-8")
    (tmp_path / "a_frame.png").write_bytes(b"")
    frames = sameness.labelled_frames(str(labels), str(tmp_path),
                                      os.path.join(sameness.ROOT, TAKES))
    by_id = {f["id"]: f for f in frames}
    assert by_id["takes_02_t3"]["crop"] == "t3" and by_id["takes_02_t3"]["on"]
    assert by_id["takes_02_t3"]["path"].endswith("takes_02.png")
    assert by_id["a_frame"]["crop"] is None and not by_id["a_frame"]["on"]


def test_labelled_frames_name_what_is_missing(tmp_path):
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"labels": {"gone": "on"}}), encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="gone"):
        sameness.labelled_frames(str(labels), str(tmp_path), os.path.join(sameness.ROOT, TAKES))


def test_the_designers_takes_agree_with_the_gate_at_the_shipped_step():
    # The six takes are labelled on, and docs/calibration.md records the
    # shipped gate passing all six. Pairwise novelty needs two frames.
    doc = rules.load()
    cfg = sameness.override(gate.load_config(), sameness.STEPS[sameness.SHIPPED_STEP])
    frames = [{"id": f"takes_02_t{i}", "on": True, "crop": f"t{i}",
               "path": os.path.join(sameness.ROOT, TAKES)} for i in (1, 2)]
    d = sameness.designer_agreement(frames, cfg, doc)
    assert d["n"] == 2 and d["tp"] == 2 and d["agreement"] == 1.0, d
    assert sameness.mean_pairwise_novelty([], cfg) is None


def test_pool_acceptance_does_not_apply_the_novelty_bar(tmp_path):
    """Novelty is the sweep's measurement, so it must not also filter the pool:
    the same frame twice is accepted twice, whatever novelty_min says."""
    import shutil
    src = os.path.join(gate.ROOT, TAKES)
    tile = gate.load_image(src, "t3")
    import cv2
    for i in (1, 2):
        cv2.imwrite(str(tmp_path / f"same_{i}.png"), cv2.cvtColor(tile, cv2.COLOR_RGB2BGR))
    cfg = gate.load_config()
    cfg["verdict"]["novelty_min"] = 0.99
    rows, accepted = sameness.score_pool(sameness.pool_paths(str(tmp_path)), cfg, rules.load(),
                                         log=lambda *_: None)
    assert len(accepted) == 2, [r["verdict"] for r in rows]
    assert rows[1]["novelty"] < 0.05, "the second copy must still be MEASURED as a repeat"
    assert cfg["verdict"]["novelty_min"] == 0.99, "score_pool mutated the caller's config"
