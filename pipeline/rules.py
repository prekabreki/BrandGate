"""brand/rules.md is the source of truth. This turns it into brand/rules.json.

The prose a designer wrote is the input, not a restatement of it. Every rule
keeps the sentence it came from, and every check reads its parameters out of
that sentence rather than out of a constant in this file. That is the whole
point: editing "Indigo `#4B3BE8` is the one flat accent" in the markdown and
regenerating changes what the palette check compares against. If the numbers
lived in code, rules.md would be documentation pretending to be a spec.

A rule the pipeline cannot check is not dropped. It is listed as `manual`, so
the gap between what a designer can say and what a machine can score stays
visible in the artifact instead of quietly disappearing.
"""
from __future__ import annotations

import json
import os
import re
import functools
import hashlib
from dataclasses import asdict, dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_MD = os.path.join(ROOT, "brand", "rules.md")
RULES_JSON = os.path.join(ROOT, "brand", "rules.json")

HEX = re.compile(r"#([0-9A-Fa-f]{6})\b")
SENTENCE = re.compile(r"(?<=[.;:])\s+")
NEGATIVE = re.compile(r"\bnever\b|\bno\b(?!\w)|\bnot\b|\bavoid\b", re.I)
PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*percent")
PX = re.compile(r"(\d+(?:\.\d+)?)\s*px\b")

# Section heading -> the check family that section's rules can bind to. A rule
# only ever binds to a check from its own section, so a stray hex code in a
# sentence about type cannot silently become a palette rule.
SECTION_CHECKS = {
    "colour": "palette",
    "gradient": "wash",
    "mark": "band",
    "motif": "motif",
    "type": "contrast",
    "surface": "contrast",
}

# A rule binds to a check only when its prose carries the evidence that check
# needs. Everything else is manual, deliberately.
# Order matters. Contrast is tried before palette because a rule about text
# also names the colours the text and its ground are drawn in, so palette would
# otherwise claim every text rule on the strength of its hex codes and the
# contrast check would bind to nothing at all.
BINDINGS = (
    # The softened-ground rule binds to the wash check on its own words; it
    # names its stops by token name, never by hex, so palette would never claim it.
    ("wash", {"gradient"}, lambda t: _mentions(t, ("softened", "bleeding into"))),
    ("contrast", {"type", "surface", "colour"},
     lambda t: _mentions(t, ("text is", "as text", "secondary text",
                             "text on", "body is"))),
    ("palette", {"colour", "gradient"}, lambda t: bool(HEX.search(t))),
    ("band", {"mark"}, lambda t: _mentions(t, ("rotated", "mirrored", "outlined",
                                               "apex", "band", "minimum width"))),
    ("motif", {"motif"}, lambda t: _mentions(t, ("one gesture", "only motif",
                                                 "no other geometric"))),
)


def _mentions(text: str, needles) -> bool:
    low = text.lower()
    return any(n in low for n in needles)


@functools.lru_cache(maxsize=1)
def _token_colours() -> tuple:
    """Colour name -> hex, from brand/tokens.json.

    A designer writes "Magenta is never a flat accent" without repeating the
    hex, so a parser that only reads hex codes silently drops the prohibition.
    The names resolve against the token file the palette is actually defined
    in, which means renaming a token there changes what the rules bind to.
    """
    path = os.path.join(ROOT, "brand", "tokens.json")
    try:
        with open(path, encoding="utf-8") as fh:
            tokens = json.load(fh)
        return tuple((name.lower(), v["hex"].upper())
                     for name, v in tokens.get("color", {}).items()
                     if isinstance(v, dict) and "hex" in v)
    except Exception:
        return ()


def _colours_in(sentence: str) -> list[str]:
    """Every colour the sentence names, by hex or by token name."""
    found = ["#" + h.upper() for h in HEX.findall(sentence)]
    low = sentence.lower()
    for name, hexv in _token_colours():
        if re.search(rf"\b{re.escape(name)}\b", low) and hexv not in found:
            found.append(hexv)
    return found


def _sentences(prose: str) -> list[str]:
    return [s for s in SENTENCE.split(prose.strip()) if s.strip()]


@dataclass
class Rule:
    id: str
    section: str
    prose: str
    check: str  # a check name, or "manual"
    params: dict = field(default_factory=dict)


def _slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", heading.strip().lower()).strip("-")


def _params_for(check: str, prose: str) -> dict:
    """Pull the check's parameters out of the sentence itself.

    Polarity is resolved per SENTENCE, not per bullet. "Indigo #4B3BE8 is the
    one flat accent: links, the primary button, a chip border. Magenta is never
    a flat accent." is one bullet holding a permission and a prohibition, and
    reading its polarity as a whole made the gate treat INDIGO, the brand's
    only accent, as the forbidden colour.
    """
    p: dict = {}
    hexes = ["#" + h.upper() for h in HEX.findall(prose)]
    if hexes:
        p["hex"] = hexes
    if check == "palette":
        low = prose.lower()
        p["role"] = ("ground" if "ground" in low else
                     "accent" if "accent" in low else
                     "text" if "text" in low else "stop")
        allow, forbid = [], []
        for sentence in _sentences(prose):
            bucket = forbid if NEGATIVE.search(sentence) else allow
            for c in _colours_in(sentence):
                if c not in bucket:
                    bucket.append(c)
        # A colour both permitted and forbidden across two sentences is a
        # permission with an exception; the permission wins and the exception
        # is left to a human.
        forbid = [c for c in forbid if c not in allow]
        p["allow"] = allow
        p["forbid_hex"] = forbid
        p["forbid"] = bool(forbid) and not allow
    if check == "contrast":
        low = prose.lower()
        p["forbid"] = "as text" in low and bool(re.search(r"\bnever\b|\bno\b(?!\w)", low))
        pct = PERCENT.findall(prose)
        if pct:
            p["percent"] = [float(x) for x in pct]
    if check == "wash":
        # every colour the sentence names is a stop the wash must carry;
        # grounds (paper, night) are filtered out by the check on luminance
        p["stops"] = [c for sentence in _sentences(prose) for c in _colours_in(sentence)]
    if check == "band":
        px = PX.findall(prose)
        if px:
            p["min_px"] = min(float(x) for x in px)
        low = prose.lower()
        p["forbid_transforms"] = [w for w in ("rotated", "mirrored", "outlined",
                                              "drop shadow") if w in low]
    return p


def parse(path: str | None = None) -> list[Rule]:
    """Every bullet under every `##` heading becomes one rule."""
    with open(path or RULES_MD, encoding="utf-8") as fh:
        lines = fh.read().replace("\r\n", "\n").split("\n")

    rules: list[Rule] = []
    section = "preamble"
    n = 0
    for line in lines:
        if line.startswith("## "):
            section = _slug(line[3:])
            n = 0
            continue
        if not line.startswith("- "):
            continue
        prose = line[2:].strip()
        if not prose:
            continue
        n += 1
        check = "manual"
        for name, sections, signal in BINDINGS:
            if section in sections and signal(prose):
                check = name
                break
        rules.append(Rule(id=f"{section}.{n:02d}", section=section, prose=prose,
                          check=check, params=_params_for(check, prose)))
    return rules


def parser_fingerprint() -> str:
    """Hash of the parser and the tokens it resolves names against.

    rules.json is derived from three things, not one: the prose, this parser,
    and brand/tokens.json. Invalidating on the prose alone meant a fix to the
    parser was written, the tests were run, and the GATE went on scoring
    against the previous parse. It cost an hour chasing a check that was
    correct, so the fingerprint covers every input.

    Line endings are normalised before hashing: the same commit checked out on
    the Windows box and the Linux box gave two fingerprints, so every gate run
    rewrote rules.json with the other machine's hash.
    """
    h = hashlib.sha256()
    for path in (os.path.abspath(__file__),
                 os.path.join(ROOT, "brand", "tokens.json")):
        try:
            with open(path, "rb") as fh:
                h.update(fh.read().replace(b"\r\n", b"\n"))
        except OSError:
            h.update(b"missing")
    return h.hexdigest()[:16]


def build(src: str | None = None, dest: str | None = None) -> dict:
    rules = parse(src)
    doc = {
        "source": os.path.relpath(src or RULES_MD, ROOT).replace(os.sep, "/"),
        "generated_from_prose": True,
        "parser": parser_fingerprint(),
        "counts": {
            "total": len(rules),
            "checked": sum(1 for r in rules if r.check != "manual"),
            "manual": sum(1 for r in rules if r.check == "manual"),
        },
        "rules": [asdict(r) for r in rules],
    }
    target = dest or RULES_JSON
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return doc


def load(path: str | None = None) -> dict:
    """Read rules.json, rebuilding it if rules.md is newer.

    The generated file is tracked so a reader can see it, but a stale one is a
    lie about what the gate scored. Rebuilding on drift costs milliseconds and
    removes a whole class of "I edited the rules and nothing changed".
    """
    target = path or RULES_JSON
    if (not os.path.exists(target)
            or os.path.getmtime(RULES_MD) > os.path.getmtime(target)):
        return build(dest=target)
    with open(target, encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("parser") != parser_fingerprint():
        return build(dest=target)
    return doc


def main(argv=None):
    doc = build()
    c = doc["counts"]
    print(f"{doc['source']} -> brand/rules.json: {c['total']} rules, "
          f"{c['checked']} checked, {c['manual']} manual")
    for r in doc["rules"]:
        if r["check"] != "manual":
            print(f"  {r['id']:<14} {r['check']:<9} {r['prose'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
