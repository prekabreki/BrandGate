---
version: 1
model: claude-cli
tier: intake
note: v1 2026-09-17 (#26). The first prompt for turning a brand guide's text into the rules file the gate reads. It names the parser's section headings and the trigger words a scorable rule must carry, and it never sees the hand-written rules.md, or the diff would measure a copy.
---
You are turning a brand guide into a rules file for an automated brand gate. The gate
scores generated images against these rules, so every line must be something a check
could measure or a reviewer could verify by eye. Write for a designer reading the file
back, not for a machine: plain sentences, sentence case, present tense.

Below is the full text of the guide, extracted from its PDF. Layout is lost, so labels
and values may sit on separate lines. Read the whole thing before writing.

Return exactly two fenced blocks and nothing else, no preamble, no commentary.

The first block is fenced as ```markdown and holds the rules file:

- Start with a single line `# <brand name>, the rules the gate reads`.
- Then exactly these seven `##` sections, in this order, each holding three to six
  bullets: Mark, Colour, Gradient, Surface, Type, Motif, Motion.
- Every bullet is ONE rule, one to two sentences, and states a fact the guide supports.
  Do not invent rules the guide does not give. If a section has little in the guide,
  write fewer bullets rather than padding it.
- Where the guide gives a colour's hex code, write the colour's name and its hex in
  backticks, like `#FAFAF8`, in the same sentence. The gate binds colour rules on hex.
- Where the guide forbids something, use the word "never" or "no" in that sentence,
  and keep a permission and a prohibition in separate sentences.
- Scorable rules must carry the words the gate looks for. In Colour: name grounds
  with the word "ground", accents with "accent", and any rule about text with "text is"
  or "as text". In Gradient: the rule about the gradient as a background must contain
  the words "softened" and "bleeding into" and name the colour stops by name. In Mark:
  rules about transforms must use the words "rotated", "mirrored", "outlined"; the
  size rule must say "minimum width" with a px value. In Motif: use the phrase "one
  gesture" or "only motif". In Type: the body rule must start "Body is".
- Percentages are written as "38 percent", pixel sizes as "96 px".
- No em dashes anywhere. Use commas, colons or full stops.

The second block is fenced as ```json and holds the tokens the guide states, in this
shape, with only the entries the guide actually gives values for:

{
  "name": "<brand name>",
  "tagline": "<tagline if stated>",
  "color": { "<lowercase name>": { "hex": "#RRGGBB", "role": "<role in the guide's words>" } },
  "type": { "display": { "family": "", "weight": 0 }, "body": { "family": "", "weight": 0, "size_px": 0, "line_height": 0 }, "mono": { "family": "" } },
  "gradient": { "flow": { "stops": [ { "offset": 0.0, "color": "#RRGGBB" } ] } }
}

Guide text follows.

<<GUIDE>>
