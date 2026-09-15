"""Does the frame's colour sit on the palette the rule names?

Scored on mass, not on presence. A single off-palette pixel is a compression
artefact; a fifth of the frame in a colour nobody chose is a brand problem. So
the score is the share of the frame that lands within tolerance of an allowed
colour, and the reason names the worst offender in a way a person can act on.

A rule can carry both a permission and a prohibition, because a designer writes
them in one breath: "Indigo is the one flat accent. Magenta is never a flat
accent." Both halves are checked, and the prohibition is checked first, because
it is the one with a specific failure a person can go and fix.
"""
from __future__ import annotations

import numpy as np

from pipeline.checks import Finding, not_applicable, register
from pipeline.checks.colour import (dominant_colours, hex_to_rgb, lab_distance,
                                    rgb_to_lab)


def _nearest(centres_lab, allowed_lab):
    d = lab_distance(centres_lab, allowed_lab)
    return d.min(axis=1), d.argmin(axis=1)


def _forbidden_mass(centres, weights, heavy, forbid_hex, tol):
    """Share of the frame held by a forbidden colour, and which one."""
    lab = rgb_to_lab(np.array([hex_to_rgb(h) for h in forbid_hex]))
    dist, idx = _nearest(rgb_to_lab(centres), lab)
    near = (dist <= tol) & heavy
    if not near.any():
        return 0.0, None
    return float(weights[near].sum()), forbid_hex[int(idx[near.argmax()])]


@register("palette")
def check(img: np.ndarray, rule: dict, cfg: dict, ctx: dict) -> Finding:
    params = rule["params"]
    allow = params.get("allow") or params.get("hex") or []
    forbid = params.get("forbid_hex") or []
    if not allow and not forbid:
        return not_applicable(rule["id"], "palette",
                              "no colours named in the rule, nothing to compare")

    c = cfg["palette"]
    tol, min_mass = c["tolerance_lab"], c["min_mass"]
    centres, weights = dominant_colours(img)
    heavy = weights >= min_mass
    if not heavy.any():
        return not_applicable(rule["id"], "palette",
                              "no colour holds enough of the frame to judge")

    if forbid:
        # The prohibition has its own tolerance, in the opposite sense to the
        # permission's: shrinking tolerance_lab tightens "the ground is paper"
        # but LOOSENS "magenta is never flat", because fewer pixels then count
        # as magenta. One knob served both until three labelled frames flipped
        # from fail to pass at a tighter setting (#19).
        mass, which = _forbidden_mass(centres, weights, heavy, forbid,
                                      c["forbid_tolerance_lab"])
        limit = c["forbid_mass"]
        if mass >= limit:
            return Finding(
                rule["id"], "palette", 0.0, False,
                f"{which} holds {mass:.1%} of the frame as a flat area, over "
                f"the {limit:.0%} the rule allows",
                {"forbidden": which, "mass": mass, "limit": limit})
        # A prohibition that is not breached is simply satisfied. It used to
        # score a fraction of its headroom, which quietly dragged the on-brand
        # mean down for a rule nothing had violated.
        return Finding(rule["id"], "palette", 1.0, True,
                       f"no forbidden colour holds a flat area "
                       f"({', '.join(forbid)} under {limit:.0%})",
                       {"mass": mass, "limit": limit})

    if params.get("role") == "accent":
        # "Indigo is the one flat accent" is a rule about FLAT regions, and v1
        # cannot separate a flat accent from a stop of the gradient: both are
        # saturated clusters of similar mass. Scoring it with the generic
        # palette branch demanded the whole frame be indigo and failed every
        # correct surface, including all six of the designer's own takes. The
        # honest answer is that this half needs an eye, not a worse check.
        return not_applicable(
            rule["id"], "palette",
            "a flat accent is not separable from a gradient stop in v1, so the "
            "permission half of this rule is left to a person")

    allowed = rgb_to_lab(np.array([hex_to_rgb(h) for h in allow]))
    dist, idx = _nearest(rgb_to_lab(centres), allowed)

    if params.get("role") == "ground":
        # "Grounds are paper, mist, or night" is a rule about the ground, which
        # is the colour holding most of the frame. Judging every dominant
        # colour against it would fail any surface carrying a wash or a mark,
        # which is every surface the brand actually has.
        g = int(np.argmax(weights))
        d = float(dist[g])
        r, gg, b = (int(v) for v in centres[g])
        return Finding(
            rule["id"], "palette", float(max(0.0, 1.0 - d / (2 * tol))), d <= tol,
            (f"the ground is {allow[int(idx[g])]}" if d <= tol else
             f"the ground is #{r:02X}{gg:02X}{b:02X}, {d:.0f} from the nearest "
             f"allowed ground {allow[int(idx[g])]}"),
            {"ground_rgb": [r, gg, b], "distance": d, "tolerance_lab": tol})

    on = (dist <= tol) & heavy
    score = float(weights[on].sum() / weights[heavy].sum())
    off = heavy & ~on
    detail = {"tolerance_lab": tol,
              "off_palette": [{"rgb": [int(v) for v in centres[i]],
                               "mass": float(weights[i]),
                               "nearest": allow[int(idx[i])],
                               "distance": float(dist[i])}
                              for i in np.where(off)[0]]}
    if off.any():
        w = int(np.argmax(np.where(off, weights, -1)))
        r, g, b = (int(v) for v in centres[w])
        reason = (f"#{r:02X}{g:02X}{b:02X} holds {weights[w]:.1%} of the frame "
                  f"and is {dist[w]:.0f} from {allow[int(idx[w])]}, past the "
                  f"{tol:.0f} tolerance")
    else:
        reason = "every dominant colour sits on the palette"
    return Finding(rule["id"], "palette", score, score >= 0.75, reason, detail)
