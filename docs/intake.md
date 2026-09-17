# Intake: the guide becomes the rules

Nobody is handed `rules.md`; they are handed a brand guide. So `pipeline/intake.py` (#26)
takes the guide's PDF, hands its text to a language model with the parser's section shape
and trigger words in the prompt, and writes `brand/intake/rules.md` and `tokens.json`. The
model never sees the hand-written set, so the diff is a measurement, not a copy. It runs as
the local `claude` CLI from an empty directory with no tools, on prompt `intake@1`, and
lands as a ledger row (model `claude-cli`, tier `intake`, 44 seconds).

## First run, 2026-09-17, on `brand/guide_05.pdf`

The guide yielded 32 rules in seven sections; the hand-written set has 41 across ten. The
parser binds 18 of the guide's and 12 of the hand-written. Every colour token came back with
the right hex and role, the five flow stops with the right offsets, the type sizes exact.
`python -m pipeline.intake diff brand/intake/rules.md brand/rules.md` matches nine rules on
word overlap; the rest is the story.

**What the guide said that the hand-written set never did.** A 28 mm minimum width in print.
That every line of type on a surface shares the apex line. And one disagreement: the guide's
geometry table says the seam is 6 units, tokens and rules say 9, because the seam was widened
on 2026-09-14 and the sheet was never corrected. The intake found a stale guide.

**What the hand-written set says that the guide never did.** The night flow. The solid mark
variants. That a lone slice carries the whole flow. The glass numbers, 52 percent white and
the shadow stack. Grain at 38 percent. Every motion number: 14 px over 900 ms, the 120 ms
stagger, orbs at 26 to 38 seconds. Tone, and what Handsel is and is not. These are the rules
a gate needs stated and a guide leaves to taste. They are the tuning pass: a designer adds
them to the extracted set, or the gate never scores them.

**Where the model padded.** Motion had almost nothing to draw on, so two of its three rules
restate the mark rules and one is a caption turned into a rule. The prompt asked for fewer
bullets over padding; version 2 should allow an empty section outright.

**The parser finding, the important one.** The guide's rules bind more, 18 against 12, and
about a third of those bindings are wrong. Any Colour or Gradient sentence with a hex code
binds to the palette check, so the flow's stop list became a palette rule that would judge a
ground against colours that are not grounds. Any Mark sentence with "band" or "apex" binds to
the mark detector, so clear space and the lockup would be scored by a check that measures
neither. The hand-written set avoids this because its author knew the trigger words and wrote
around them, which is exactly what a designer handing over a guide does not know. Binding by
trigger word is fragile on prose you did not write. The fix belongs in the parser, not the
prompt: bind on what a check can measure and list the rest as manual. The extracted set is
the regression for that change (#28).

## What this changes

The script never promotes into `brand/rules.md`. Promotion is a human reading the diff,
adding what the guide left implicit, and re-running the calibration against labels that do
not move. The review UI's edit surface should be this, the extracted rules and the gaps the
diff names, not a textarea of hex codes.
