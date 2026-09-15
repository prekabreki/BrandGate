# Calibration

The judge is an instrument, and this is its datasheet.

**Status: 27 designer-labelled images, 2026-09-15. The gate agrees with the
designer on 19 of them.** 21 are generated grounds from `hero-ground@2` across
two models and two tiers, 6 are the designer's own takes. The 8 disagreements
are written up below, one line each, in the designer's words. The headline is
not the agreement rate. It is that the seven false passes all fail on
qualities no check measures, so the bar cannot be fixed by moving a threshold.

The ten-image wiring check that preceded this set is kept below as
[Set 0](#set-0-the-wiring-check). It measured whether the checks were connected.
This set measures whether the gate agrees with a designer, which is a different
question, and the answer is: on the easy frames, and not on the ones that matter.

## The labelled set

30 grounds were generated from the plan in `pipeline/calibrate.py`: seeds 1000
to 1029, round-robin over krea2 and flux2, turbo and raw, so every combination
has seven or eight frames. 27 were labelled in one sitting on a Lavish page that
showed each frame beside the gate's verdict; four Flux.2 frames that landed
mid-session were skipped. The six takes from `takes_02` were labelled in the
same pass. The designer's note is verbatim. Card numbers are the page's, kept
because the notes refer to them.

**Before a single label: the prompt was off-brand.** Every v1 frame ended the
wash in sky blue at the right. Rule 30 read "orbs in indigo, magenta and sky",
which gave a faint 40% undertone from `guide_03` equal billing with the flow's
two real stops, and the prompt then promoted it to the endpoint. The designer
caught it at a glance. Rule 30 was reworded to the guide (indigo left, magenta
warming to rose right, sky at most a low undertone on paper, none on night),
the prompt bumped to `hero-ground@2`, and all 30 regenerated. The v1 set is
parked under `surfaces/_calibration-v1-skyright` and its ledger rows stand.
Lesson for the gate: nothing in it could have caught this, because every check
reads the rules, and the rules were wrong.

| # | image | model / tier | label | gate | on-brand | rule fired | agreed | designer's note |
|---|---|---|---|---|---|---|---|---|
| 1 | raw 1001 | krea2 raw | off | fail | 0.69 | `colour.03` | yes | too much separation between colours, not enough bleed |
| 2 | raw 1003 | flux2 raw | off | **pass** | 0.93 | `--` | **no** | too dark, too few colours |
| 3 | raw 1005 | krea2 raw | off | fail | 0.57 | `colour.02, colour.03, colour.04, type.03` | yes* | not enough bleed, too dark, too much magenta. Weird dark lilac spot |
| 4 | raw 1007 | flux2 raw | off | **pass** | 0.95 | `--` | **no** | muddy, dark, wrong colours |
| 5 | raw 1009 | krea2 raw | off | **pass** | 0.95 | `--` | **no** | not enough bleed and smudge |
| 7 | raw 1013 | krea2 raw | off | fail | 0.70 | `colour.03` | yes | too much separation, not enough gradient |
| 9 | raw 1017 | krea2 raw | off | fail | 0.70 | `colour.03` | yes | not enough bleed. far left isnt dark enough |
| 10 | raw 1021 | krea2 raw | off | fail | 0.70 | `colour.03` | yes | not enough bleed, not enough colours, too saturated |
| 11 | raw 1025 | krea2 raw | off | fail | 0.70 | `colour.03` | yes | too separated, not enough bleed |
| 12 | raw 1029 | krea2 raw | off | fail | 0.70 | `colour.03` | yes | not enough bleed or colour variation |
| 13 | turbo 1000 | krea2 turbo | off | **pass** | 0.95 | `--` | **no** | close, the bleed between purple and red is good. Too much separation between red and rose. Too much dark on the left. |
| 14 | turbo 1002 | flux2 turbo | off | fail | 0.72 | `colour.02, colour.04, type.03` | yes* | no bleed, strong outlines, wrong colours |
| 15 | turbo 1004 | krea2 turbo | **on** | **fail** | 0.70 | `colour.03` | **no** | (none) |
| 17 | turbo 1008 | krea2 turbo | on | pass | 0.94 | `--` | yes | a better version of 15 |
| 18 | turbo 1010 | flux2 turbo | off | **pass** | 0.90 | `--` | **no** | same as 14 and 16 |
| 19 | turbo 1012 | krea2 turbo | off | fail | 0.69 | `colour.03` | yes | not enough bleed, pink and red blobs too far apart. Too much dark on far left. |
| 20 | turbo 1014 | flux2 turbo | off | **pass** | 0.93 | `--` | **no** | same as 14,16,18 |
| 21 | turbo 1016 | krea2 turbo | on | pass | 0.95 | `--` | yes | close to failing. A lot of dark and not a lot of bleed. |
| 23 | turbo 1020 | krea2 turbo | on | pass | 0.94 | `--` | yes | a better 21 |
| 24 | turbo 1024 | krea2 turbo | off | **pass** | 0.94 | `--` | **no** | (none) |
| 25 | turbo 1028 | krea2 turbo | off | fail | 0.72 | `colour.02, colour.04, type.03` | yes* | too dark, too much separation. |
| 26-31 | takes_02 t1 to t6 | designer | on | pass | 0.99-1.00 | `--` | yes | (six rows, all agreed; t1 ruled 09-14, t2 to t6 labelled today) |

Full ids are in `calibration-labels.json`; the frame name carries tier and seed.

**Caveat on the scores in this table: the mark checks did not run.** They were
computed on the Windows work box, where `cairosvg` cannot load `libcairo-2.dll`,
so `band.locate` returns -1.0 and every `mark.*` rule reports *not applicable*
rather than *errored*. For grounds that changes nothing, a ground has no mark to
find. For the six takes it means their 0.99 to 1.00 rests on four rules instead
of seven, and Set 0's mark results (from Linux) are the ones to trust there.
The real finding is that the gate degraded silently: `counts.errored` stayed at
0 while a dependency was missing. A missing library has to surface as an error,
not vanish into n/a. Filed as #17.

**Confusion matrix, generated frames (21):**

| | designer: on | designer: off |
|---|---|---|
| gate: pass | 3 | **7** |
| gate: fail | **1** | 10 |

Agreed 13 of 21. With the six takes, 19 of 27. Precision of a pass is 3 of 10:
when the gate says on-brand, the designer agrees less than a third of the time.
Recall of a fail is 10 of 17. **The gate is lenient, and lenient in one
direction**: it lets through frames the designer rejects.

**The starred rows fired for the wrong reason.** Three frames failed on
`colour.02` / `type.03`, the contrast checks, which found "a text region" in a
frame that contains no text. MSER read a hard-edged blob as a glyph. The
verdict matched the designer, the reason did not, and by this document's own
standard (see Set 0) a fail for the wrong reason is worth nothing. Counting
those as misses, honest agreement on generated frames is 10 of 21.

## The eight disagreements, and what they say

**Seven false passes, one cause.** Every frame the gate passed and the designer
rejected was rejected for the same family of reasons: *too dark*, *not enough
bleed*, *too much separation*, *muddy*. Read the notes for rows 2, 4, 5, 13, 18,
20, 24. None of the eleven bound checks measures any of that. `colour.01` asks
whether the ground is paper. `colour.03` asks whether magenta sits as a flat
area over 4%. `motif.*` count gestures. Not one asks how much of the frame is
dark, or how smoothly one stop becomes the next. The designer's judgement of a
wash is almost entirely about those two things, so the gate cannot see the
thing being judged. **This is not a threshold problem.** The false passes
score 0.90 to 0.95 and the true passes score 0.94 to 0.95. Between 0.90 and
0.95 sit three frames the designer accepted and seven the designer rejected; no bar
separates them. Moving `on_brand_min` anywhere changes nothing here.

**One false fail, one cause.** Row 15, turbo 1004: the designer's on-brand,
the gate's fail on `colour.03`, 5.4% of the frame as flat magenta. The designer
wrote nothing here, but row 17's note calls that frame "a better version of 15",
and 17 was accepted by both. So `colour.03` fired on a soft orb the designer
reads as part of the flow, not as a flat accent. The 4% limit is doing the
work, and 4% is one of the hand-picked numbers this document warned about.
Every krea2 raw frame that failed did so on the same rule at 4.8% to 9.6%, and
the designer agreed with all of those, so the rule is right about *something*;
it is the boundary that is guessed. Between 5.4% (accepted) and 4.8% (rejected)
the rule is not measuring what the designer is.

**Where the notes point.** Two checks would cover the seven false passes, and
both are cheap:

1. **Bleed.** A gradient-smoothness measure: the fraction of the frame where
   the luminance or chroma gradient exceeds a soft threshold. "Strong outlines"
   and "too much separation" are high-gradient rings around an orb. The
   designer's accepted frames are the ones where orbs dissolve into each other.
2. **Dark mass.** The fraction of the frame below a luminance floor. "Too dark"
   and "too much dark on the left" recur in six notes. The guide's wash is
   paper with light on it; a frame that is a third ink is not that.

Both bind to rule 30 as written today ("blurred orbs ... bleeding into one
another"). Neither needs a model. Once they exist, re-score the same 27 files;
the labels do not move, so this table is the held-out set for the next version
of the gate. That is the point of writing labels down.

**A generator finding, not a gate finding.** Of 10 raw-tier frames the designer
accepted none; of 11 turbo frames, four. Of the five Flux.2 frames labelled,
none. Raw tiers separate the orbs into hard discs, which is the
opposite of what the wash wants, and the extra steps buy detail the brand never
asked for. Recommendation for the surfaces: **krea2 turbo only**, and the drift
run (#9) should treat flux2 as the "different model" it is meant to test, not
as a source of grounds.

## Set 0: the wiring check

The ten-image set below was built before the labelled set and is kept because
it answers a different question: whether the checks are connected to the rules
they claim to test.

## What the gate scores

40 rules parse out of `brand/rules.md`. 11 bind to a check, 29 are `manual`.
That ratio is the honest headline: roughly a quarter of what the designer wrote
is machine-checkable today, and the rest is listed in `brand/rules.json` with
`"check": "manual"` so the gap stays visible in the artifact.

A twelfth rule, `colour.03`'s permission half, is bound but returns
not-applicable: see the known limits below.

## The set, and the confusion matrix

Six on-brand images are the designer's own takes from `lookdev/archive/takes_02.png`,
scored a tile at a time with `--crop`. Four off-brand images are deliberate
mutations of take 3, each breaking exactly one rule, so that a failure can be
attributed rather than guessed at.

| image | label | verdict | on-brand | rule that fired | agreed |
|---|---|---|---|---|---|
| takes_02 t1 | on-brand | **pass** | 1.00 | `--` | yes |
| takes_02 t2 | on-brand | **pass** | 0.99 | `--` | yes |
| takes_02 t3 | on-brand | **pass** | 1.00 | `--` | yes |
| takes_02 t4 | on-brand | **pass** | 1.00 | `--` | yes |
| takes_02 t5 | on-brand | **pass** | 1.00 | `--` | yes |
| takes_02 t6 | on-brand | **pass** | 1.00 | `--` | yes |
| t3 rotated 90 | off-brand | **fail** | 0.77 | `mark.08` | yes |
| t3 hue +60 | off-brand | **fail** | 0.95 | `colour.01` | yes |
| t3 ink lifted | off-brand | **fail** | 0.81 | `colour.02, colour.04, type.03` | yes |
| t3 magenta block | off-brand | **fail** | 0.90 | `colour.03` | yes |

caught 4/4 off-brand, passed 6/6 on-brand, 0 false failures, 0 misses

Ten for ten, and every failure fired on the rule the mutation actually broke.
That last clause is the only part worth anything. A gate can reach a perfect
confusion matrix by failing everything for the wrong reason, so the column that
matters is the rule name, not the verdict.

## What that number is not

**It is not accuracy.** Four of the ten images were built by the same person
who built the checks, breaking exactly the rules the checks look for. That
measures whether the wiring is connected, not whether the gate agrees with a
designer. Three of those four mutations are also far past any reasonable
threshold: a 90 degree rotation and a 25 percent magenta block are not the
marginal cases a real gate has to judge.

**The thresholds in `brand/gate.toml` are unvalidated, and stay that way on
purpose.** Every one was set by hand before this set existed. `tolerance_lab = 22` and `on_brand_min = 0.75`
were not derived from anything; they were picked, and then the set passed. With
ten images and six thresholds there is nothing to overfit to and no way to tell
whether any of them is right. The issue's own warning about overfitting twenty
images applies twice as hard to ten.

**The aggregate separates, but its bar is in the wrong place, deliberately.**
Passing takes score 0.99 to 1.00 and every failure scores 0.95 or below, so the
aggregate does discriminate on this set: a bar at 0.97 would bite. It sits at
0.75 and never fires, and all four catches came from the per-rule verdict.

Moving it to 0.97 would be fitting a threshold to ten images, six thresholds
and no held-out data, which is the overfitting this document exists to be
honest about. **Decided 2026-09-14: leave the bar at 0.75 and let the per-rule
verdict carry the verdict until twenty labelled images exist**, then set it
from that data. A clean separation on ten points is not evidence.

## Known limits, each found by testing rather than reasoning

- **A flat accent is not separable from a gradient stop.** `colour.03`'s
  permission half, "indigo is the one flat accent", needs to know whether a
  saturated region is flat colour or part of the flow. Dominant-colour
  clustering cannot tell them apart, so the permission returns not-applicable
  and only the prohibition is scored. Scoring it with the generic palette
  branch demanded the whole frame be indigo and failed all six of the
  designer's takes.
- **Rotation is only tested at 90 degrees.** A mark tilted five degrees passes
  the level rule. The cheap test is the one that is implemented.
- **The mark check confirms the artwork, not the geometry.** `mark.01` says six
  slices in a 3:1 band; the check confirms the frame contains something
  matching `slice-mark-blank.svg`, which is a proxy. A five-slice mark drawn
  from a different file would not be caught.
- **Text regions are found, not read.** MSER returns glyph-shaped blobs, and
  anything else glyph-shaped comes with them. There is no OCR, so "under 75
  characters a line" in `type.03` is unchecked even though the rule binds to a
  contrast check.
- **Novelty is hash-only here.** `open_clip` is not installed, so the semantic
  half did not run. Every novelty figure above is 1.00 because the accepted set
  is empty, which is a statement about the corpus and not a measurement.
  Decided 2026-09-14: install it before the sameness run (#10), which is the
  first thing that genuinely needs it. A hash-only novelty would flatline there
  for the wrong reason, measuring composition rather than idea.

## Three bugs worth recording, because each one passed its tests first

**A smooth wash matched the mark at 1.00.** Normalised cross-correlation
between two near-empty patches returns a confident perfect score. The
unguarded detector reported a mark in blank gradient in every frame tested, and
pointed at the caption strip rather than the mark. The fix is an edge-energy
floor on each candidate window: a window carrying far less structure than the
template cannot contain it. Separation went from noise to 0.79-0.97 for real
marks against 0.30 for a frame with none, and the reported locations became
correct.

**The gate scored a stale parse.** `rules.json` derives from three inputs: the
prose, the parser, and `tokens.json`. Invalidation checked only the prose, so a
corrected parser was written, its tests passed, and the gate went on scoring
against the previous parse. It cost an hour chasing a check that was already
right. `rules.json` now carries a fingerprint of the parser and the tokens, and
rebuilds when either moves.

**Dominant colours were not deterministic.** The subsample RNG was seeded;
OpenCV's own global RNG, which drives k-means++ initialisation, was not. The
same file scored differently on consecutive runs. A gate whose score moves
between two runs is not an instrument.

Two more of the same shape: a two-sentence rule, "Indigo is the one flat
accent. Magenta is never a flat accent", had its polarity read as a whole and
made the gate treat indigo as forbidden; and the contrast check took a blob's
darkest quartile as the ink, which on a night surface is the ground, so it
reported a flat 1.0:1 and failed a take whose type is fully legible.

## To finish this

1. ~~Ten more images, all twenty labelled by the designer.~~ **Done 2026-09-15:
   27 labelled, table above.** Six Flux.2 frames from the same plan are on disk
   and unlabelled (seeds 1006, 1011, 1015, 1018, 1019, 1023, 1027); they can join
   the set any time, the labels file merges.
2. ~~One disagreement written up per row.~~ **Done, eight rows.**
3. ~~A decision on take 1.~~ **Ruled 2026-09-14: one gesture.**
4. **`docs/rule-edit.mp4`.** Still to record. The behaviour works: deleting
   paper from the grounds rule takes take 3's `colour.01` from 0.95 to 0.79 and
   the reason from "the ground is #FAFAF8" to "the ground is #ECEAF6". Deleting
   mist as well pushes it to a failure, which is the more legible ten seconds.
5. **Two new checks, bleed and dark mass**, bound to rule 30, then re-score the
   27 labelled files against the table above. That is the next version of the
   gate and the first time a threshold here can be set from data rather than
   picked. Filed separately; the labels are the fixture.
6. **Fix the contrast false reasons.** `colour.02` / `type.03` should not find
   text in a frame with none. Gate the MSER pass on a glyph-shaped aspect and
   stroke width, or skip it when `motif.*` reports zero gestures.

The labelling page itself is worth a line: `lookdev/tuning.png` is a screenshot
of it mid-pass, gate verdict beside designer verdict, the disagreement in the
designer's words. That picture is the whole argument of this document in one
frame, and it belongs in the README (#12).
