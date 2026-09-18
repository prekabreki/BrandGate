# Handsel Gate

The screen a brand team uses to review generated brand surfaces that the
scoring gate accepted or rejected. The tool is itself a Handsel surface:
it is set in the brand type, sits on the flow wash, and answers to the
same rules it reviews.

It is a static React review tool. There is no login and no backend. All
data comes from typed fixtures under `src/fixtures/`, shaped the way the
gate's own output is shaped, so the app can later read the same JSON from
disk.

## Run it

    cd handsgate
    bun install
    bun run dev

## Where things live

- `src/fixtures/surfaces.ts` — one entry per surface folder: the accepted
  candidate, the rejected candidate, and each candidate's full score.
- `src/fixtures/rules.ts` — the brand rules as editable prose, grouped
  under the section headings Mark, Colour, Gradient, Surface, Type,
  Motif, Motion.
- `src/gate/rescore.ts` — the seam. It is a lookup, not a scorer: the
  real gate is the Python pipeline in `pipeline/`, which reads the same
  rules file. When the two are wired together, this function is where
  the pipeline plugs in.
- `src/brand/tokens.css` — every colour, font, radius and shadow in the
  tool, defined once as CSS variables.

Editing a rule line in the right column calls `rescore` on blur and
updates the centre breakdown, so the rehearsed rule edits behave the way
they will once the real pipeline answers.
