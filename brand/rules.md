# Handsel, the rules the gate reads

Exploration 02, 2026-09-14.
Decided: the name is Handsel, the mark is the six slices, the palette and gravity are Direction A.
Every line here is a check something can score.

## Mark

- Six pie slices in a 3:1 band, alternating apex down and apex up, the geometry in `tokens.json` under `mark`.
- One gradient flows through all six left to right, deep indigo to rose.
- Solid variants are ink on light ground and white on dark ground.
- On night the gradient mark uses the lifted night flow, indigo 6C56FF to pink EC56A8; the paper flow starts too deep to read on black.
- A lone slice always carries the whole flow across its own width, never a cut of the band.
- Clear space is one slice radius on every side.
- Minimum width is 96 px on screen.
- The mark is never rotated, mirrored, outlined, or shown with a drop shadow.
- A single slice may stand alone as the avatar or favicon unit.

## Colour

- Grounds are paper `#FAFAF8`, mist `#ECEAF6`, or night `#0D0B18`.
- Text is ink `#111114` on light grounds and white on night. Secondary text is graphite `#4A4A55`.
- Indigo `#4B3BE8` is the one flat accent: links, the primary button, a chip border. Magenta is never a flat accent.
- No gradient stop is ever used as text.

## Gradient

- There is one gradient, the flow, and it runs left to right on every surface.
- The flow appears on the mark, on display type, and as a ground wash. Nothing else carries it.
- As a ground it is softened: three blurred orbs in indigo, magenta and sky over paper or night, with a paper veil and film grain over that. Never the raw ramp.
- Display type takes the text variant, which starts from ink so the first word reads as text before it turns.

## Surface

- Where there is depth, cards are glass: white at 52 percent, backdrop blur, a one pixel inset specular, the Direction A shadow stack.
- Where the surface must survive as a flat PNG, cards are paper with a hairline border and no shadow.
- Film grain at 38 percent overlay on every ground with a wash. None on flat surfaces.

## Type

- Display is Archivo 800, tracking -0.045 em, line height 0.9, two lines or fewer.
- The wordmark is Handsel in Archivo 800, title case, in the text gradient or in ink.
- Body is Archivo 400 at 17 px, line height 1.5, under 75 characters a line.
- IBM Plex Mono 400 carries labels, code and data, at 10 to 13 px with 0.14 em tracking when set in caps.

## Motif

- The slice is the only motif. No other geometric shape is used decoratively.
- One gesture per surface: the mark, or gradient type, or a slice field. Not two.

## Motion

- One orchestrated entrance per surface, a rise of 14 px over 900 ms on a soft curve, staggered by 120 ms.
- Ground orbs drift for 26 to 38 seconds, alternate, and never faster.
- Nothing else moves without a user action.

## What Handsel is

- A one-person software studio that builds tools for its own work and keeps them in public.
- The word means a gift given at the start of something. Every public tool is one.
- The audience is other makers who would rather read the code than a pitch.
- The proof is the repos themselves: ColdRead, the ck3 chronicler, the rest of the public set. The brand exists to make them read as one studio.

## What Handsel is not

- Not a SaaS, a platform, or a product with a pricing page.
- Not a team, an agency, or a company that hires.
- Not enterprise, not compliance, not a dashboard for buyers.
- Not playful for its own sake. The colour carries the energy, the words stay plain.

## Tone

- Plain sentences, sentence case, present tense.
- Says what the thing does and why it was built. No adjectives about itself.
- "Tools built for one person, kept in public."
