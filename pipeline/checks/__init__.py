"""Every check is pure: an image and a rule go in, a Finding comes out.

A check never raises into the gate. If one fails, the gate records that rule as
`errored` with the exception attached, because a gate that crashes on an odd
frame gets switched off, and a gate that is switched off scores nothing at all.

Errored is not the same as not-applicable. Not-applicable is a rule with nothing
to measure in this frame. Errored is a rule the gate could not run, and it has
to say so: on 2026-09-15 a missing cairo DLL made every mark rule read as
not-applicable and 27 frames were scored with the mark detector dead (#17).
"""
from __future__ import annotations

from dataclasses import dataclass, field

REGISTRY: dict = {}


class CheckDependencyError(RuntimeError):
    """A check's library failed to import or load. Raised by the check so the
    gate can name the dependency instead of reporting a quiet non-result."""

    def __init__(self, dependency: str, cause: BaseException):
        super().__init__(f"{dependency} could not be loaded: {cause}")
        self.dependency = dependency


@dataclass
class Finding:
    rule_id: str
    check: str
    score: float          # 0 to 1, higher is more on-brand
    passed: bool
    reason: str           # one sentence, written for a person
    detail: dict = field(default_factory=dict)
    # A rule with nothing to measure in this frame. It is neither a pass nor a
    # failure, and it must stay out of the on-brand mean: a frame with no type
    # and no mark would otherwise score a perfect 1.0 for containing nothing.
    applicable: bool = True


def not_applicable(rule_id, check, reason) -> "Finding":
    return Finding(rule_id, check, 1.0, True, reason, applicable=False)


def _freeze(value):
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def memo(ctx: dict, name: str, depends_on, compute):
    """A measurement shared between checks, computed once per frame.

    `ctx` is the per-frame scratch dict the gate hands every check. The key
    carries `depends_on` (the config section the measurement read), so a caller
    holding one ctx across threshold sets gets a fresh measurement the moment
    the section it depends on changes, and a stale one never.

    This exists because `ctx.setdefault("band", locate(img, cfg))` evaluates
    `locate` BEFORE setdefault looks at the dict: the six band and motif rules
    each ran the mark detector in full, and nothing was memoised at all.
    """
    key = (name, _freeze(depends_on))
    if key not in ctx:
        ctx[key] = compute()
    return ctx[key]


def register(name):
    def wrap(fn):
        REGISTRY[name] = fn
        return fn
    return wrap


def get(name):
    return REGISTRY.get(name)


from pipeline.checks import band, contrast, motif, palette, wash  # noqa: E402,F401
