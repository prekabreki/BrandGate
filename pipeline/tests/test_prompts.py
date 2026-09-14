"""Prompt identity is what lets two ledger rows be compared at all, so the
parse and the id are pinned here."""
import pytest

from pipeline import prompts

BODY = """---
version: 3
model: krea2
tier: turbo
width: 1664
height: 944
---
a soft indigo wash over paper
"""


def _write(tmp_path, name, body):
    (tmp_path / f"{name}.md").write_text(body, encoding="utf-8")
    return str(tmp_path)


def test_loads_frontmatter_and_text(tmp_path):
    d = _write(tmp_path, "hero-ground", BODY)
    spec = prompts.load("hero-ground", d)
    assert spec.version == 3
    assert spec.model == "krea2"
    assert spec.tier == "turbo"
    assert spec.text == "a soft indigo wash over paper"
    assert spec.params == {"width": 1664, "height": 944}


def test_prompt_id_is_name_at_version(tmp_path):
    d = _write(tmp_path, "hero-ground", BODY)
    assert prompts.load("hero-ground", d).prompt_id == "hero-ground@3"


def test_prompt_id_is_stable_across_loads(tmp_path):
    d = _write(tmp_path, "hero-ground", BODY)
    first = prompts.load("hero-ground", d).prompt_id
    second = prompts.load("hero-ground", d).prompt_id
    assert first == second == "hero-ground@3"


def test_prompt_id_moves_only_when_the_author_bumps_version(tmp_path):
    d = _write(tmp_path, "hero-ground", BODY)
    before = prompts.load("hero-ground", d).prompt_id
    # Reword the text without touching version: the id deliberately holds, so
    # bumping it stays an editorial act rather than a side effect of a typo fix.
    _write(tmp_path, "hero-ground", BODY.replace("indigo", "violet"))
    assert prompts.load("hero-ground", d).prompt_id == before
    _write(tmp_path, "hero-ground", BODY.replace("version: 3", "version: 4"))
    assert prompts.load("hero-ground", d).prompt_id == "hero-ground@4"


def test_text_keeps_its_own_line_breaks(tmp_path):
    d = _write(tmp_path, "multi", "---\nversion: 1\n---\nline one\nline two\n")
    assert prompts.load("multi", d).text == "line one\nline two"


def test_defaults_when_frontmatter_is_minimal(tmp_path):
    d = _write(tmp_path, "bare", "---\nversion: 1\n---\njust words\n")
    spec = prompts.load("bare", d)
    assert (spec.model, spec.tier) == ("krea2", "turbo")


def test_crlf_frontmatter_parses(tmp_path):
    # The repo is worked from a Linux box and a Windows one.
    d = _write(tmp_path, "crlf", BODY.replace("\n", "\r\n"))
    assert prompts.load("crlf", d).version == 3


@pytest.mark.parametrize("body, match", [
    ("no fence here\n", "no frontmatter"),
    ("---\nversion: 1\nstill open\n", "never closed"),
    ("---\nversion: one\n---\nwords\n", "must be an integer"),
    ("---\nmodel: krea2\n---\nwords\n", "no version"),
    ("---\nversion: 1\n---\n\n", "no prompt text"),
    ("---\nversion: 1\nnonsense\n---\nwords\n", "not key: value"),
    ("---\nversion: 1\nwdith: 8\n---\nwords\n", "unknown frontmatter key"),
])
def test_bad_templates_are_refused_with_a_reason(tmp_path, body, match):
    d = _write(tmp_path, "bad", body)
    with pytest.raises(prompts.PromptError, match=match):
        prompts.load("bad", d)


def test_missing_template_names_the_path(tmp_path):
    with pytest.raises(prompts.PromptError, match="no prompt template at"):
        prompts.load("absent", str(tmp_path))


def test_available_lists_templates(tmp_path):
    _write(tmp_path, "b", BODY)
    _write(tmp_path, "a", BODY)
    assert prompts.available(str(tmp_path)) == ["a", "b"]
    assert prompts.available(str(tmp_path / "nope")) == []


def test_the_real_hero_ground_template_loads():
    # The one template the repo actually ships has to parse, or the command in
    # the README is a lie.
    spec = prompts.load("hero-ground")
    assert spec.prompt_id.startswith("hero-ground@")
    assert spec.text
