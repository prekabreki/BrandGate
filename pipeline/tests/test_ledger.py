"""The ledger row is the unit the gate, the drift run and the scorecard all
read later, so its shape is tested rather than assumed."""
import json
import os

import pytest

from pipeline import ledger


def _row(**over):
    base = dict(run_id="abc123", model="krea2", tier="turbo",
                prompt_id="hero-ground@1", prompt_text="a wash",
                params={"width": 8, "height": 8}, seed=1)
    base.update(over)
    return ledger.row(**base)


def test_row_carries_every_field_in_order():
    r = _row()
    assert tuple(r) == ledger.FIELDS


def test_local_run_records_no_cost():
    # Not an oversight and not a stub: local generation has no per-frame price,
    # and an invented one would poison the model scorecard #9 builds on.
    assert _row()["cost_usd"] is None


def test_latency_is_rounded_and_optional():
    assert _row(latency_s=12.3456)["latency_s"] == 12.3
    assert _row()["latency_s"] is None


def test_lora_is_always_a_list():
    assert _row()["lora"] == []
    assert _row(lora=("a.safetensors",))["lora"] == ["a.safetensors"]


def test_failure_row_keeps_the_error_and_drops_the_path(tmp_path):
    path = tmp_path / "ledger.jsonl"
    r = _row(error="server refused", output_path=None)
    assert ledger.append(r, str(path))
    rows = ledger.read(str(path))
    assert len(rows) == 1
    assert rows[0]["error"] == "server refused"
    assert rows[0]["output_path"] is None


def test_append_is_append_only(tmp_path):
    path = str(tmp_path / "ledger.jsonl")
    ledger.append(_row(run_id="one"), path)
    ledger.append(_row(run_id="two"), path)
    assert [r["run_id"] for r in ledger.read(path)] == ["one", "two"]


def test_append_creates_the_runs_directory(tmp_path):
    path = str(tmp_path / "runs" / "ledger.jsonl")
    assert ledger.append(_row(), path)
    assert os.path.exists(path)


def test_append_never_raises_into_the_caller(tmp_path):
    # A directory where the file should be. Losing a row must not cost a render
    # that has already been paid for in GPU time.
    bad = tmp_path / "ledger.jsonl"
    bad.mkdir()
    assert ledger.append(_row(), str(bad)) is False


def test_rows_survive_a_round_trip_as_utf8(tmp_path):
    path = str(tmp_path / "ledger.jsonl")
    ledger.append(_row(prompt_text="ljós, skuggi, hlýja"), path)
    assert ledger.read(path)[0]["prompt_text"] == "ljós, skuggi, hlýja"
    with open(path, "rb") as fh:
        assert b"\r\n" not in fh.read()


def test_corrupt_line_raises_rather_than_being_skipped(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_text('{"run_id": "ok"}\nnot json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="corrupt ledger line"):
        ledger.read(str(path))


def test_missing_ledger_reads_as_empty(tmp_path):
    assert ledger.read(str(tmp_path / "nope.jsonl")) == []


def test_read_skips_blank_lines(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_text(json.dumps(_row()) + "\n\n", encoding="utf-8")
    assert len(ledger.read(str(path))) == 1
