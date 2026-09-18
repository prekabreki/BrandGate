"""Generate the review UI's rule list from the brand's own parsed rules.

    python handsgate/scripts/rules-to-fixtures.py

Reads `brand/rules.json`, the file the gate itself scores against, and writes
`handsgate/src/fixtures/rules.ts`.

This exists because the first Lovable build invented its rule prose. It read
plausibly and it was wrong: "the mark keeps clear space of a third of its height",
"the recurring motif is the band". A tool whose whole claim is that the rules are
the sentences a designer wrote cannot paraphrase them in its own shop window. Every
line the panel shows is now the sentence in `brand/rules.md`, carried through the
parser, with the id and the bound check the gate actually uses.

The sections the panel shows are the scoreable ones. `what-handsel-is`,
`what-handsel-is-not` and `tone` are positioning prose in the same file: real rules,
but not ones a check can measure, so they stay out of a panel about scoring.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RULES = os.path.join(ROOT, "brand", "rules.json")
OUT = os.path.join(ROOT, "handsgate", "src", "fixtures", "rules.ts")

# The panel's order, and the label each section slug shows under.
SECTIONS = [("mark", "Mark"), ("colour", "Colour"), ("gradient", "Gradient"),
            ("surface", "Surface"), ("type", "Type"), ("motif", "Motif"),
            ("motion", "Motion")]

HEADER = '''/*
 * GENERATED FILE. Do not edit.
 *
 * Written by handsgate/scripts/rules-to-fixtures.py from brand/rules.json, which
 * the gate scores against. Every sentence below is the designer's, not a paraphrase:
 * the build that paraphrased them was wrong about the mark's clear space and invented
 * a motif rule outright. Change brand/rules.md, rebuild rules.json, run the script.
 */

import type { Rule } from "./types";

'''


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build(rules: list[dict]) -> str:
    by_section: dict[str, list[dict]] = {}
    for r in rules:
        by_section.setdefault(r.get("section", ""), []).append(r)

    out = [HEADER, "export const rules: Rule[] = ["]
    for slug, label in SECTIONS:
        items = by_section.get(slug, [])
        if not items:
            continue
        out.append(f"  // {label}")
        for r in items:
            check = r.get("check") or "manual"
            # An id is only meaningful when a check is bound to it: an unbound rule
            # has nothing to score, and showing an id beside it implies otherwise.
            rid = f'"{r["id"]}"' if check != "manual" else "null"
            out.append("  {")
            out.append(f"    id: {rid},")
            out.append(f'    section: "{label}",')
            out.append(f'    prose: "{esc(r["prose"])}",')
            out.append(f'    check: "{check}",')
            out.append("  },")
        out.append("")
    out.append("];")
    out.append("")
    labels = ", ".join(f'"{lbl}"' for _, lbl in SECTIONS)
    out.append(f"export const ruleSections = [{labels}];")
    out.append("")
    return "\n".join(out)


def main() -> int:
    with open(RULES, encoding="utf-8") as fh:
        doc = json.load(fh)
    rules = doc["rules"]
    ts = build(rules)
    shown = sum(1 for r in rules if r.get("section") in {s for s, _ in SECTIONS})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(ts)
    print(f"wrote handsgate/src/fixtures/rules.ts  "
          f"({shown} scoreable rules of {len(rules)} in brand/rules.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
