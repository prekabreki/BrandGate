# BrandGate, the proposal

One invented brand, a pipeline that generates against it, and a gate that decides what may
carry the name. Built for the Lovable Brand Engineer application, submit 2 October 2026.

## The claim

A brand run through this setup stays consistent across every surface it lands on and still
stays alive. Consistency alone is a photocopier. Freedom alone drifts off-brand within a dozen
generations. The gate scores both, on-brand and novelty, and targets the corner that is both.

## The brand

The object under test is one invented maker identity. Direction A from the look-dev canvas
(`lookdev/`): light ground, one soft chromatic gradient, glass, tight display type, one gesture
per screen. Name, palette, type, tone, motifs, reference set and written rules live in `brand/`
as editable files. The rules are what the gate reads, so changing a rule and rerunning is a
first-class demo move, the same shape as a brand book a designer edits without a deploy.

Brand decisions still open with Pétur, 14 Sep: what the identity is for, the feeling in a few
words, what it is not, and whether HANDSEL from the canvas stays.

## The showcase: a matrix, not a gallery

The brand rendered across the surfaces Lovable names in its own listing, each one generated or
assembled through the pipeline and each one scored:

| Surface | Why it is here |
|---|---|
| Marketing hero | the listing names the marketing site |
| Social card set: square, story, OG | the everyday brand-team job |
| Product UI: the gate's own review screen wears the brand | "internal apps for the brand team", dogfooded |
| Print piece: poster or one-pager | proves the system survives leaving the screen |
| Slack-sized snippets: avatar, banner, reaction set | the listing names Slack |
| Generated imagery through `gen.py` | the image-API pipeline half of the role |
| **Brand motion: a generated ident, 5 to 10 seconds** | the wow moment, see below |

Surfaces are the flexible part if time runs short. The two runs and the motion piece are not.

## The two runs that carry the pitch

**Drift run.** Swap the generation model, hold prompt, params and seed, and plot the on-brand
score distribution moving. Nobody demos drift. Everybody demos generation.

**Sameness run.** Tighten the gate until novelty flatlines and everything passes. The outputs
look identical and the brand is dead. Showing that an over-tight gate is its own failure mode is
the part no other applicant will show.

Both plots ship in the README and in the review UI.

## Brand motion

A short ident, the brand moving. Generated, not hand-animated, so it belongs to the pipeline
and gets scored like everything else. Two routes, pick during build week after one test of each:

- **Model route:** a video generation API (Krea's video models, or whichever wins the
  evaluation) driven from the brand's reference set and rules. Highest wow, least control.
- **Code route:** the brand's own gradient, type and motifs animated with anime.js, rendered
  headless to mp4. Full control, and the same engine that later animates the marketing hero.

The honest version is probably both: a model-generated background with code-driven type over
it, gated frame by frame. That also makes the drift plot work on video.

## The pipeline

`gen.py` carved out of vibe-comfyUI: Krea with Turbo and Raw tiers, `runs.jsonl` provenance,
tested. Every output is versioned by model, prompt, params, LoRA and seed. Scoring is a judge
that is itself calibrated and written up, because a validated judge is not a validated gate,
and the calibration write-up is part of the deliverable, not an appendix.

## Layout

```
brand/      the package: palette, type, tone, motifs, references, rules.md
lookdev/    the six directions canvas that produced Direction A
pipeline/   gen.py extract, scoring, gate, run ledger
surfaces/   one folder per surface, outputs and scores
runs/       drift and sameness runs, plots
ui/         the review screen
```

## Schedule

Every day from 14 Sep. Brand package and decisions first, since it seeds everything else.
Pipeline and gate from 22 Sep. Surfaces, the two runs and the motion piece through 28 Sep.
Public flip end of that week, owner at the keyboard, commit 1 rebuilt from the tracked set.
Polish and write-up to 1 Oct.
