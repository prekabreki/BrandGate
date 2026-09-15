"""Every check is pure: an image and a rule go in, a Finding comes out.

A check never raises into the gate. If one fails, the gate records that rule as
`manual` with the error attached, because a gate that crashes on an odd frame
gets switched off, and a gate that is switched off scores nothing at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field

REGISTRY: dict = {}


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


def register(name):
    def wrap(fn):
        REGISTRY[name] = fn
        return fn
    return wrap


def get(name):
    return REGISTRY.get(name)


from pipeline.checks import band, contrast, motif, palette, wash  # noqa: E402,F401
