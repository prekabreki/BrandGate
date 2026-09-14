"""The calibration tooling. Testable with no GPU: batch takes a stubbed backend
and the sheet is built from whatever frames exist."""
import json

import cv2
import numpy as np
import pytest

from pipeline import calibrate


class StubBackend:
    def __init__(self, fail_on=()):
        self.calls = 0
        self.fail_on = set(fail_on)

    def generate(self, graph, *, dest_dir, timeout=1800):
        import os
        from pipeline.gen import GenerationError
        self.calls += 1
        if self.calls in self.fail_on:
            raise GenerationError("model refused")
        os.makedirs(dest_dir, exist_ok=True)
        path = os.path.join(dest_dir, f"frame_{self.calls:03d}.png")
        cv2.imwrite(path, np.full((80, 140, 3), 200, np.uint8))
        return [path]


def test_plan_covers_every_model_and_tier_combination():
    # A set drawn from one model at one tier measures that corner and nothing
    # else, and its thresholds move the first time a surface comes from
    # elsewhere.
    rows = calibrate.plan(8, "hero-ground")
    assert {(r["model"], r["tier"]) for r in rows} == {
        ("krea2", "turbo"), ("krea2", "raw"),
        ("flux2", "turbo"), ("flux2", "raw")}


def test_plan_gives_every_frame_its_own_seed():
    rows = calibrate.plan(30, "hero-ground")
    assert len({r["seed"] for r in rows}) == 30


def test_a_short_run_still_covers_all_four_combinations():
    assert len({(r["model"], r["tier"]) for r in calibrate.plan(4, "x")}) == 4


def test_dry_run_generates_nothing(tmp_path, capsys):
    rows = calibrate.batch(4, "hero-ground", str(tmp_path), dry_run=True)
    assert all(r["output_path"] is None for r in rows)
    assert not list(tmp_path.iterdir())


def test_batch_writes_a_frame_per_spec(tmp_path):
    rows = calibrate.batch(4, "hero-ground", str(tmp_path), backend=StubBackend(),
                           ledger_path=str(tmp_path / "ledger.jsonl"))
    assert len(rows) == 4
    assert len(list(tmp_path.glob("*.png"))) == 4


def test_one_refused_frame_does_not_cost_the_rest(tmp_path, capsys):
    # The failure is already a ledger row; it must not end the run.
    rows = calibrate.batch(4, "hero-ground", str(tmp_path),
                           backend=StubBackend(fail_on={2}),
                           ledger_path=str(tmp_path / "ledger.jsonl"))
    assert len(rows) == 4
    assert sum(1 for r in rows if r["output_path"]) == 3


def test_sheet_is_built_from_the_frames_present(tmp_path):
    src = tmp_path / "frames"
    src.mkdir()
    for i in range(7):
        cv2.imwrite(str(src / f"f{i}.png"),
                    np.full((60, 100, 3), 30 * i % 255, np.uint8))
    out = str(tmp_path / "sheet.png")
    calibrate.sheet(str(src), out)
    img = cv2.imread(out)
    assert img is not None
    rows = (7 + calibrate.COLS - 1) // calibrate.COLS
    assert img.shape[1] == calibrate.COLS * calibrate.TILE_W + (calibrate.COLS + 1) * calibrate.PAD
    assert rows == 2


def test_sheet_refuses_an_empty_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        calibrate.sheet(str(tmp_path), str(tmp_path / "s.png"))


def test_tile_id_is_the_filename_stem():
    assert calibrate.tile_id("/a/b/hero-ground_turbo_1_abc.png") == "hero-ground_turbo_1_abc"


def test_labels_merge_rather_than_replace(tmp_path):
    # Labelling twenty images happens over more than one sitting; a partial
    # second pass must not discard the first.
    path = str(tmp_path / "labels.json")
    calibrate.write_labels({"a": "on", "b": "off"}, path)
    doc = calibrate.write_labels({"c": "on"}, path)
    assert doc["labels"] == {"a": "on", "b": "off", "c": "on"}
    assert json.load(open(path, encoding="utf-8"))["labels"]["a"] == "on"


def test_a_relabel_overwrites_that_one_entry(tmp_path):
    path = str(tmp_path / "labels.json")
    calibrate.write_labels({"a": "on"}, path)
    assert calibrate.write_labels({"a": "off"}, path)["labels"] == {"a": "off"}


def test_a_bad_verdict_is_refused_before_anything_is_written(tmp_path):
    path = str(tmp_path / "labels.json")
    with pytest.raises(ValueError, match="must be 'on' or 'off'"):
        calibrate.write_labels({"a": "maybe"}, path)
    assert not (tmp_path / "labels.json").exists()


def test_the_batch_writes_its_rows_where_it_is_told(tmp_path):
    # Without a ledger path threaded through, batch wrote into the REPO's
    # ledger during tests: sixteen junk rows carrying tmp paths and a username.
    led = tmp_path / "ledger.jsonl"
    calibrate.batch(2, "hero-ground", str(tmp_path), backend=StubBackend(),
                    ledger_path=str(led))
    from pipeline import ledger
    assert len(ledger.read(str(led))) == 2


def test_an_output_outside_the_repo_is_not_recorded_as_an_escaping_path(tmp_path):
    # `../../../../../tmp/pytest-of-<user>/...` is meaningless to any other
    # reader and carries a username into a file that ships when the repo goes
    # public.
    from pipeline import gen
    _, record = gen.generate("hero-ground", seed=1, backend=StubBackend(),
                             dest_dir=str(tmp_path),
                             ledger_path=str(tmp_path / "l.jsonl"))
    assert not record["output_path"].startswith("..")
    assert "/" not in record["output_path"]


def test_cli_sheet_reports_a_missing_directory_without_a_traceback(tmp_path, capsys):
    assert calibrate.main(["sheet", "--src", str(tmp_path / "nope"),
                           "--out", str(tmp_path / "s.png")]) == 2
    assert "ERROR" in capsys.readouterr().err
