# Lovable, first prompt for the review UI (#5)

Written 2026-09-16 for the first build on Lovable. Paste the block below as the opening message.
Fixtures stand in for `surfaces/` and `runs/`; the export is wired to the repo after download.
The rule-edit re-score is a stub with the rehearsed path baked in, because the real scorer is Python
and this build has no backend. That seam is named in the prompt so the export tells us where to cut.

---

Build a single-page internal review tool called **Handsel Gate**. It is the screen a brand team uses
to review generated brand surfaces that a scoring gate has accepted or rejected. React, TypeScript,
Tailwind, Vite. No auth, no backend, no router beyond a hash for the selected surface. All data comes
from typed fixture files under `src/fixtures/` shaped exactly as described below, so the app can later
read the same JSON from disk.

## Identity, and this is the whole point

The tool is itself a Handsel surface. It must look like the brand it reviews, not like a SaaS
dashboard. Do not use shadcn defaults, default Tailwind greys, rounded-xl on everything, badge pills,
or icon buttons for their own sake. Every colour, font, radius and shadow comes from the tokens
below, defined once as CSS variables in `src/brand/tokens.css` and mapped into
`tailwind.config.ts`. No colour or font literal anywhere in a component.

Colours (hex, role):
- ink #111114, text on light, and the mono mark on light
- paper #FAFAF8, default light ground
- mist #ECEAF6, tinted light ground
- night #0D0B18, dark ground
- graphite #4A4A55, secondary text on light
- indigo #4B3BE8, the one flat accent: links, the primary button, a chip border
- deep #1E1A5C, violet #7A4FE0, magenta #B44C9E, rose #D9628A: gradient stops only, never text,
  never a flat fill

Gradients:
- flow: `linear-gradient(90deg, #1E1A5C 0%, #4B3BE8 28%, #7A4FE0 50%, #B44C9E 74%, #D9628A 100%)`
- flow on night: `linear-gradient(90deg, #6C56FF 0%, #8E63FF 45%, #C25CCB 75%, #EC56A8 100%)`
- flow text, for display type only: `linear-gradient(90deg, #111114 0%, #111114 10%, #4B3BE8 42%, #B44C9E 100%)`,
  applied with background-clip text on an element sized `width: max-content`

Type, from Google Fonts:
- Display: Archivo 800, letter-spacing -0.045em, line-height 0.9, never more than two lines
- Body: Archivo 400, 17px, line-height 1.5, measure under 75 characters
- Labels, data, code, rule ids: IBM Plex Mono 400, 10 to 13px, 0.14em tracking when set in caps

Surface:
- Ground is paper (light theme) or night (dark theme), with a soft wash: two or three large blurred
  radial orbs, indigo on the left warming through magenta to rose on the right, under a paper veil,
  with film grain at 38 percent overlay on top. Orbs drift very slowly, 26 to 38 seconds, alternate
  directions, nothing faster. This is the only ambient motion.
- Where a panel sits on the wash it is glass: `background: rgba(255,255,255,0.52)`,
  `backdrop-filter: blur(28px) saturate(180%)`, `border: 1px solid rgba(255,255,255,0.75)`,
  `box-shadow: inset 0 1px 0 rgba(255,255,255,0.95), inset 0 -1px 0 rgba(17,17,20,0.04),
  0 1px 2px rgba(17,17,20,0.04), 0 12px 28px -8px rgba(40,32,110,0.14), 0 40px 80px -32px rgba(40,32,110,0.20)`.
  On night the glass is `rgba(255,255,255,0.06)` with the same blur and a `rgba(255,255,255,0.12)` border.
- Radius 22px on glass panels, 6px on inputs and chips. Nothing else.
- One entrance on load: panels rise 14px over 900ms on a soft ease, staggered 120ms. No hover
  animations beyond a colour change. Nothing else moves without a user action.
- The mark: six pie slices in a 3:1 band, alternating apex down and apex up, one flow gradient
  across all six. I will supply the SVG; leave a `<Mark />` component that renders a placeholder
  3:1 box painted with the flow gradient, 96px wide minimum, with clear space of a third of its
  height on every side. Never rotate, mirror, outline or shadow it.
- Tone in every string: plain sentences, sentence case, present tense. No exclamation marks, no
  marketing adjectives, no emoji.

Theme switch: a small mono toggle top right, "paper" and "night", persisted in localStorage.

## Layout

Three columns on desktop, stacking on narrow screens:

1. **Surfaces** (left, narrow). A list of surface folders: hero, social, print, motion. Each row
   shows the folder name in mono caps, a small thumbnail of the accepted candidate, and the accepted
   on-brand score. The selected row carries a 1px indigo left border. Under the list, two small
   plots from the runs folder, "drift" and "sameness", rendered as images from fixtures with a
   mono caption.

2. **Candidates** (centre, wide). For the selected surface, the accepted and the rejected candidate
   side by side, each image in a glass frame with a mono label "accepted" or "rejected" and the
   verdict. Below each image its breakdown: one row per rule, columns rule id (mono), score as a
   number to two decimals, a thin score bar painted flat indigo on pass and graphite on fail, and
   the reason sentence. Rows in `failed_rules` sit first and carry a hairline graphite left border.
   `not_applicable` rules collapse under a mono disclosure "not measured (n)".

3. **Rules** (right). The brand rules as editable prose, grouped under the section headings Mark,
   Colour, Gradient, Surface, Type, Motif, Motion. Each rule is one line. Lines that the gate can
   score carry their rule id in mono to the left (colour.01, colour.03, gradient.03, and so on);
   lines it cannot score are shown in graphite with no id. Clicking a line makes it an inline
   editable textarea in the same type. On blur, call `rescore(surfaceId, rules)` and update the
   centre breakdown: the changed rule's row highlights briefly and moves to its new position if it
   now fails or passes. A mono "reset rules" link restores the original text.

## Data shapes, put these in `src/fixtures/`

```ts
type Finding = {
  rule: string;            // "colour.01"
  check: string;           // "palette" | "wash" | "contrast" | "band" | "manual"
  score: number;           // 0..1
  passed: boolean;
  reason: string;          // "the ground is #FAFAF8"
  detail: Record<string, unknown>;
};

type Score = {
  verdict: "pass" | "fail";
  on_brand: number;        // 0..1
  novelty: number;         // 0..1
  thresholds: { on_brand_min: number; novelty_min: number };  // 0.75, 0.12
  failed_rules: string[];
  breakdown: Finding[];
  not_applicable: { rule: string; check: string; reason: string }[];
};

type Candidate = { image: string; score: Score };
type Surface = { id: "hero" | "social" | "print" | "motion"; accepted: Candidate; rejected: Candidate };

type Rule = { id: string | null; section: string; prose: string; check: string };
```

Fixture content to seed: hero accepted passes at on_brand 0.9662 with colour.01 0.90
("the ground is #FAFAF8"), colour.03 1.00, gradient.03 1.00 ("soft wash: darks at chroma 56, edges
5.2, every stop present"); hero rejected fails at 0.84 with gradient.03 0.891 not passed ("the wash
is dull (mean chroma 27, a ground carries at least 30)") and colour.01 0.63 ("the ground is
#ECEAF6"). Print accepted passes at 1.00 with colour.01, colour.02, colour.03, colour.04, type.03
all 1.00 and contrast reasons like "every text region clears 4.5:1 (worst 8.4:1)". Invent social
and motion in the same shape and register. Use gradient placeholder images sized 1664x944 for hero,
1080x1350 social, 1240x1754 print, 1920x1080 motion.

Rules prose, use these lines verbatim, ids on the ones marked:

Colour
- (colour.01) Grounds are paper `#FAFAF8`, mist `#ECEAF6`, or night `#0D0B18`.
- (colour.02) Text is ink `#111114` on light grounds and white on night. Secondary text is graphite `#4A4A55`.
- (colour.03) Indigo `#4B3BE8` is the one flat accent: links, the primary button, a chip border. Magenta is never a flat accent.
- (colour.04) No gradient stop is ever used as text.

Gradient
- There is one gradient, the flow, and it runs left to right on every surface.
- The flow appears on the mark, on display type, and as a ground wash. Nothing else carries it.
- (gradient.03) As a ground it is softened: blurred orbs over paper or night, indigo at the left and magenta warming to rose at the right, bleeding into one another, with a paper veil and film grain over that. No other colour enters the wash. Never the raw ramp.
- Display type takes the text variant, which starts from ink so the first word reads as text before it turns.

Mark, Surface, Type, Motif, Motion: fill each with three or four plain one-line rules in the same
voice, drawn from the identity section above, none with an id except (type.03) "Body is Archivo 400
at 17 px, line height 1.5, under 75 characters a line."

## The rescore stub

`src/gate/rescore.ts` exports `rescore(surfaceId, rules): Score`. For now it is a lookup, not a
scorer, and the file's header comment says so: the real gate is a Python pipeline that reads the
same rules file, and this function is the seam where it plugs in. Implement exactly this behaviour
for the hero surface's accepted candidate, and return the fixture unchanged for anything else:

- If the colour.01 line no longer contains "paper" but still contains "mist": colour.01 score
  becomes 0.79, reason becomes "the ground is #ECEAF6", still passed, on_brand becomes 0.93.
- If it contains neither "paper" nor "mist": colour.01 score 0.41, passed false, reason "the ground
  #FAFAF8 is not an allowed ground", verdict "fail", failed_rules ["colour.01"], on_brand 0.71.
- Restoring the words restores the fixture.

## Acceptance

- No hex, rgb, font name, or shadow literal in any file under `src/components/`.
- Both themes read correctly, text is ink on paper and white on night, indigo is the only flat accent.
- The rehearsed edit works: delete "paper" from the colour.01 line, colour.01 drops to 0.79 and its
  reason changes; delete "mist" too and the accepted hero fails and the row moves to the top.
- At 1280px wide the three columns fit without horizontal scroll; at 420px they stack.
