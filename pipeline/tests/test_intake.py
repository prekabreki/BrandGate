"""The intake (#26) is a model call wrapped in bookkeeping, and the bookkeeping is
what these test: output parsing, the diff, the ledger row, and that a bad result
never lands under the final name. No test calls the claude CLI."""
import json
import os

import pytest

from pipeline import intake, ledger

GOOD = """Here you go.

```markdown
# Handsel, the rules the gate reads

## Mark
- The mark is never rotated, mirrored, or outlined.
- Minimum width is 96 px on screen.

## Colour
- Grounds are paper `#FAFAF8`, mist `#ECEAF6`, or night `#0D0B18`.
- Text is ink `#111114` on light grounds and white on night.

## Gradient
- As a ground the flow is softened into blurred orbs, indigo bleeding into magenta and rose.

## Surface
- Film grain sits at 38 percent over every wash.

## Type
- Body is Archivo 400 at 17 px, line height 1.5.

## Motif
- The slice is the only motif.

## Motion
- One entrance per surface.
```

```json
{"name": "Handsel", "color": {"paper": {"hex": "#FAFAF8", "role": "default ground"}}}
```
"""


def test_parse_output_ignores_preamble_and_checks_sections():
    md, tokens = intake.parse_output(GOOD)
    assert md.startswith("# Handsel")
    assert tokens["color"]["paper"]["hex"] == "#FAFAF8"


def test_parse_output_refuses_a_missing_section():
    broken = GOOD.replace("## Motion\n- One entrance per surface.\n", "")
    with pytest.raises(intake.IntakeError, match="Motion"):
        intake.parse_output(broken)


def test_parse_output_refuses_an_em_dash():
    with pytest.raises(intake.IntakeError, match="em dash"):
        intake.parse_output(GOOD.replace("only motif.", "only motif — nothing else."))


def test_parse_output_refuses_bad_json():
    with pytest.raises(intake.IntakeError, match="JSON"):
        intake.parse_output(GOOD.replace('{"name": "Handsel"', '{"name": Handsel'))


def _write(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return str(p)


def _prompt(tmp_path):
    return _write(tmp_path, "intake.md", "---\nversion: 9\nmodel: claude-cli\ntier: intake\n---\nRules please.\n\n<<GUIDE>>\n")


def test_run_writes_files_and_a_ledger_row(tmp_path):
    guide = _write(tmp_path, "guide.txt", "Paper #FAFAF8 is the ground.")
    led = str(tmp_path / "ledger.jsonl")
    seen = {}

    def fake(prompt):
        seen["prompt"] = prompt
        return GOOD

    rec = intake.run(guide, str(tmp_path / "out"), prompt_path=_prompt(tmp_path), ledger_path=led, call=fake)
    assert "Paper #FAFAF8 is the ground." in seen["prompt"]
    assert (tmp_path / "out" / "rules.md").exists() and (tmp_path / "out" / "tokens.json").exists()
    assert tuple(rec) == ledger.FIELDS
    assert rec["model"] == "claude-cli" and rec["tier"] == "intake" and rec["prompt_id"] == "intake@9"
    assert rec["error"] is None and rec["output_path"].endswith("rules.md")
    rows = ledger.read(led)
    assert len(rows) == 1 and rows[0]["run_id"] == rec["run_id"]


def test_run_on_a_bad_result_writes_an_error_row_and_no_rules_file(tmp_path):
    guide = _write(tmp_path, "guide.txt", "x")
    led = str(tmp_path / "ledger.jsonl")
    with pytest.raises(intake.IntakeError):
        intake.run(guide, str(tmp_path / "out"), prompt_path=_prompt(tmp_path), ledger_path=led, call=lambda p: "sorry, no fences")
    assert not (tmp_path / "out" / "rules.md").exists()
    assert not (tmp_path / "out" / "rules.md.partial").exists()
    rows = ledger.read(led)
    assert len(rows) == 1 and rows[0]["error"] and rows[0]["output_path"] is None


def test_run_is_idempotent_without_force(tmp_path):
    guide = _write(tmp_path, "guide.txt", "x")
    out = tmp_path / "out"; out.mkdir(); (out / "rules.md").write_text("old", encoding="utf-8")
    calls = []
    rec = intake.run(guide, str(out), prompt_path=_prompt(tmp_path), ledger_path=str(tmp_path / "l.jsonl"),
                     call=lambda p: calls.append(p) or GOOD)
    assert rec == {} and calls == []
    rec = intake.run(guide, str(out), force=True, prompt_path=_prompt(tmp_path), ledger_path=str(tmp_path / "l.jsonl"),
                     call=lambda p: calls.append(p) or GOOD)
    assert len(calls) == 1 and rec["error"] is None


def test_diff_matches_by_overlap_one_to_one(tmp_path):
    a = _write(tmp_path, "a.md", "# A\n\n## Colour\n- Grounds are paper `#FAFAF8`, mist `#ECEAF6`, or night `#0D0B18`.\n- Text is ink `#111114` on light grounds.\n\n## Motif\n- The slice is the only motif.\n")
    b = _write(tmp_path, "b.md", "# B\n\n## Colour\n- Grounds are paper `#FAFAF8`, mist `#ECEAF6`, or night `#0D0B18`.\n- Indigo `#4B3BE8` is the one flat accent.\n\n## Motion\n- Nothing moves without a user action.\n")
    d = intake.diff(a, b)
    col = d["sections"]["colour"]
    assert [p["hand"] for p in col["both"]] == ["colour.01"]
    assert [r["id"] for r in col["guide_only"]] == ["colour.02"]
    assert [r["id"] for r in col["hand_only"]] == ["colour.02"]
    assert d["sections"]["motif"]["guide_only"] and d["sections"]["motion"]["hand_only"]
    assert d["bound"]["guide"] == 3  # palette, contrast and motif bind; the parser decides, not the diff
    text = intake.format_diff(d)
    assert "colour.01 ~ colour.01" in text
