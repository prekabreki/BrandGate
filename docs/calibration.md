# Calibration

The judge is an instrument, and this is its datasheet.

**Status: partial, 10 of the 20 images the issue asks for, and none of them
labelled by the designer.** What follows is a real measurement of a real gate,
but it is not yet the calibration the write-up is supposed to be. The gap is
named at the bottom rather than papered over, because a datasheet that
overstates its own coverage is worse than none.

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

**The thresholds in `brand/gate.toml` are unvalidated.** Every one was set by
hand before this set existed. `tolerance_lab = 22` and `on_brand_min = 0.75`
were not derived from anything; they were picked, and then the set passed. With
ten images and six thresholds there is nothing to overfit to and no way to tell
whether any of them is right. The issue's own warning about overfitting twenty
images applies twice as hard to ten.

**The on-brand scores barely separate.** Passing takes score 0.99 to 1.00 and
three of the four failures still score 0.77 to 0.95, above the 0.75 bar. They
fail on the per-rule verdict, not on the aggregate. So `on_brand_min` is
currently doing almost no work, and the mean is a weak summary of a breakdown
that is doing all of it. Worth deciding whether the aggregate should exist at
all, or whether the verdict is simply "did every applicable rule pass".

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

1. **Ten more images, and all twenty labelled by the designer.** The label has
   to come from the person whose taste the gate is impersonating, and the
   interesting ten are marginal, not obvious: a mark slightly too small, a wash
   slightly too saturated, two gestures where one was intended.
2. **One disagreement written up per row.** The format above has the column;
   there is nothing in it yet because the gate has not yet disagreed with
   anybody.
3. **A decision on take 1.** It carries the mark and the wordmark in the flow,
   which is two gestures by a literal reading of `motif.02`. The gate passes it
   only because the mark and the type are counted as one gesture when they
   overlap. Whether that is correct is a taste call, and it is the first real
   question the gate has put to its designer.
4. **`docs/rule-edit.mp4`.** The behaviour works: deleting paper from the
   grounds rule takes take 3's `colour.01` from 0.95 to 0.79 and the reason
   from "the ground is #FAFAF8" to "the ground is #ECEAF6". Deleting mist as
   well pushes it to a failure, which is the more legible ten seconds to record.
