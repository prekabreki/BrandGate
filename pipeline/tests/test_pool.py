"""runs.pool: the pool directory and the prompt version are pinned together (#22)."""
import os

import pytest

from runs import pool

PROMPT = """---
version: 4
model: krea2
tier: turbo
---
one continuous wash
"""


@pytest.fixture
def prompt_dir(tmp_path):
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "hero-ground.md").write_text(PROMPT, encoding="utf-8")
    return str(d)


def test_a_matching_version_runs(prompt_dir, tmp_path):
    rows = pool.fill(2, "hero-ground", "krea2", "turbo", str(tmp_path / "out"),
                     seed_start=3000, dry_run=True, prompt_version=4, prompt_dir=prompt_dir)
    assert [r["seed"] for r in rows] == [3000, 3001]


def test_the_wrong_version_refuses_before_touching_the_pool(prompt_dir, tmp_path):
    dest = tmp_path / "out"
    with pytest.raises(pool.PromptVersionMismatch, match="version 4, this pool is for version 3"):
        pool.fill(2, "hero-ground", "krea2", "turbo", str(dest),
                  dry_run=True, prompt_version=3, prompt_dir=prompt_dir)
    assert not os.path.exists(dest)


def test_no_version_means_no_check(prompt_dir, tmp_path):
    rows = pool.fill(1, "hero-ground", "krea2", "turbo", str(tmp_path / "out"),
                     dry_run=True, prompt_dir=prompt_dir)
    assert len(rows) == 1


def test_the_flag_reaches_fill_from_the_command_line(tmp_path, capsys):
    # The real prompt on disk is v4; asking for v3 must refuse, asking for v4 runs dry.
    with pytest.raises(pool.PromptVersionMismatch):
        pool.main(["--count", "1", "--dry-run", "--prompt-version", "3", "--out", str(tmp_path / "a")])
    assert pool.main(["--count", "1", "--dry-run", "--prompt-version", "4", "--out", str(tmp_path / "b")]) == 0
    assert "would generate" in capsys.readouterr().out
