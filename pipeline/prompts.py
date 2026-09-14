"""Prompt templates, versioned on disk so a ledger row can name the exact text
that produced a frame.

A template is a markdown file under brand/prompts/ with YAML-ish frontmatter:

    ---
    version: 3
    model: krea2
    tier: turbo
    width: 1664
    height: 944
    ---
    the prompt text, as many lines as it needs

The frontmatter is parsed by hand rather than with PyYAML: the grammar is flat
scalars and nothing else, and the pipeline stays stdlib-only. Anything more
structured than `key: value` is a template that has outgrown this format.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_DIR = os.path.join(ROOT, "brand", "prompts")

# Frontmatter keys the generator understands. A key outside this set is a typo
# often enough that guessing is worse than refusing.
KNOWN_KEYS = {"version", "model", "tier", "width", "height", "negative", "note"}
INT_KEYS = {"version", "width", "height"}


class PromptError(ValueError):
    """A template that cannot be read as a prompt spec."""


@dataclass(frozen=True)
class PromptSpec:
    name: str
    version: int
    text: str
    model: str
    tier: str
    params: dict = field(default_factory=dict)

    @property
    def prompt_id(self) -> str:
        """Ledger identity: name@version. Stable for a given file content, and
        it changes only when the author bumps `version`, which is the point:
        two rows with the same prompt_id used the same words."""
        return f"{self.name}@{self.version}"


def _split_frontmatter(raw: str, name: str) -> tuple[dict, str]:
    lines = raw.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise PromptError(f"{name}: no frontmatter, expected a --- fence on line 1")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise PromptError(f"{name}: frontmatter fence is never closed") from None

    meta: dict = {}
    for lineno, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise PromptError(f"{name}:{lineno}: frontmatter line is not key: value")
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key not in KNOWN_KEYS:
            raise PromptError(
                f"{name}:{lineno}: unknown frontmatter key {key!r} "
                f"(known: {', '.join(sorted(KNOWN_KEYS))})")
        if key in INT_KEYS:
            try:
                meta[key] = int(value)
            except ValueError:
                raise PromptError(f"{name}:{lineno}: {key} must be an integer, got {value!r}") from None
        else:
            meta[key] = value

    return meta, "\n".join(lines[end + 1:]).strip()


def load(name: str, prompt_dir: str | None = None) -> PromptSpec:
    """Read brand/prompts/<name>.md into a PromptSpec."""
    path = os.path.join(prompt_dir or PROMPT_DIR, f"{name}.md")
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
    except FileNotFoundError:
        raise PromptError(f"no prompt template at {path}") from None

    meta, text = _split_frontmatter(raw, name)
    if "version" not in meta:
        raise PromptError(f"{name}: frontmatter has no version")
    if not text:
        raise PromptError(f"{name}: template has frontmatter but no prompt text")

    params = {k: v for k, v in meta.items()
              if k not in ("version", "model", "tier", "note")}
    return PromptSpec(
        name=name,
        version=meta["version"],
        text=text,
        model=meta.get("model", "krea2"),
        tier=meta.get("tier", "turbo"),
        params=params,
    )


def available(prompt_dir: str | None = None) -> list[str]:
    d = prompt_dir or PROMPT_DIR
    if not os.path.isdir(d):
        return []
    return sorted(f[:-3] for f in os.listdir(d) if f.endswith(".md"))
