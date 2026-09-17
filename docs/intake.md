# Intake: the guide becomes the rules

The realistic first stage of this pipeline is not someone writing `rules.md`. It is someone
being handed a brand guide. So `pipeline/intake.py` (#26) takes the guide's PDF, hands its
text to a language model with the parser's section shape and trigger words in the prompt,
and writes `brand/intake/rules.md` and `brand/intake/tokens.json`. The model never sees the
hand-written set, so the diff below is a measurement, not a copy. The model is the local
`claude` CLI on the subscription, run from an empty directory with no tools; the prompt is
`brand/prompts/intake.md` at version 1; the run is a ledger row, model `claude-cli`, tier
`intake`, 44 seconds.

## First run, 2026-09-17, on `brand/guide_05.pdf`

The guide yielded 32 rules in the seven sections; the hand-written set has 41 across ten.
The parser binds 18 of the guide's rules to a check and 12 of the hand-written set. Every
colour token came back with the right hex and role, the flow's five stops with the right
offsets, the type sizes and the body line rule exact. The diff (`python -m pipeline.intake
diff brand/intake/rules.md brand/rules.md`) matches nine rules across the two sets on word
overlap and the rest is where the story is.

**What the guide said that the hand-written set never did.** A 28 mm minimum width in print.
That the wordmark and every line of type share the apex line on a surface, which the
hand-written set states only for type beside the mark. And a fact the two disagree on: the
guide's geometry table says the seam is 6 units, the tokens and the hand-written rules say 9,
because the seam was widened on 2026-09-14 and the guide sheet was never corrected. The intake
found a stale guide, which is the job.

**What the hand-written set says that the guide never did.** The night flow for the mark on
dark grounds. The solid mark variants. That a lone slice carries the whole flow, never a cut
of the band. The glass recipe's numbers, 52 percent white and the shadow stack. Film grain at
38 percent. Every motion number: the 14 px rise over 900 ms, the 120 ms stagger, orbs drifting
26 to 38 seconds. Tone, and what Handsel is and is not. These are the rules a gate needs
stated explicitly and a guide sheet leaves to taste, and they are the tuning pass: a designer
reading the extracted set adds them, or the gate never scores them.

**Where the model padded.** The Motion section had almost nothing to draw on, so two of its
three rules restate the mark rules and one is a caption from the type spread turned into a
rule. Fewer bullets would have been the honest output; the prompt says so and the model did
it anyway. Version 2 of the prompt should let a section be empty.

**The parser finding, and it is the important one.** The guide's rules bind more than the
hand-written ones, 18 against 12, and about a third of those bindings are wrong. Any Colour or
Gradient sentence carrying a hex code binds to the palette check, so the flow's stop list and
"display type starts from ink" became palette rules that would judge a ground against colours
that are not grounds. Any Mark sentence with "band" or "apex" in it binds to the mark
detector, so clear space and the lockup would be scored by a check that measures neither. The
hand-written set avoids this because its author knew the trigger words and wrote around them,
which is exactly the knowledge a designer handing over a guide does not have. Binding by
trigger word is fragile on prose you did not write. The fix is not in the prompt: the parser
should bind on what a check can measure (a ground rule names grounds, a transform rule names
transforms) and list everything else as manual, and the extracted set is the regression for
that change.

## What this changes

Intake output is never promoted into `brand/rules.md` by the script. Promotion is a human
reading the diff, adding what the guide left implicit, and re-running the calibration; the
labels do not move, so the extracted set can be scored against them like any other version of
the gate. The review UI's edit surface should be this: the extracted rules, the gaps the diff
names, and the designer filling them, not a textarea full of hex codes.
