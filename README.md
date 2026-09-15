# BrandGate

[![ci](https://github.com/prekabreki/BrandGate/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/prekabreki/BrandGate/actions/workflows/ci.yml)

A designed brand and the pipeline that keeps generated output on it.

Under construction, September 2026.

## The generator

`pipeline/` generates the grounds every surface sits on. A prompt template goes
in, a PNG and one ledger row come out.

```bash
python -m pipeline.gen --prompt hero-ground --seed 1
python -m pipeline.gen --prompt hero-ground --seed 1 --dry-run
python -m pipeline.gen --prompt hero-ground --seed 1 --model flux2 --tier raw
uv run --with pytest python -m pytest pipeline/tests -q
```

The backend is a local ComfyUI, pointed at by `COMFY_SERVER` and defaulting to
`http://127.0.0.1:8188`. Models are Krea-2 and Flux.2, each in a turbo tier for
hunting and a raw tier for finals.

### Where it came from

This started as a personal script for driving a local ComfyUI: one file, a
growing pile of argparse flags, and a provenance log that wrote two lines per
run so a power cut still left the recipe on disk. It knew a lot about one
person's habits. It could do depth exports, region-masked detail passes,
img2img at half a dozen scales and six model families, because each of those
was needed once on a Tuesday and never removed. It also assumed it was living
inside the ComfyUI checkout, which is how it could get away with never
answering the question of where a frame should land.

Three things changed to make it a module. It was carved down rather than
copied: only text-to-image survived, and only the two model families the brand
actually uses, because a generator with six backends and no reason for any of
them is not a pipeline, it is a drawer. The frames are now pulled back over the
server's HTTP API and written into this repo, so the pipeline and the weights
no longer have to live in the same directory and the path in a ledger row is a
path that exists here. And the prompt moved out of the command line into
`brand/prompts/*.md`, versioned, so that the words that produced a frame are a
thing you can cite rather than a thing you have to remember typing.

### What the ledger is for

Every run appends one line to `runs/ledger.jsonl`: the model, the tier, the
prompt at its exact version, the seed, the resolved sampler parameters, the
output path, the latency. One row per logical run, including the failures,
which carry an `error` and no path. A run that is retried after a timeout keeps
its id and still writes one row, because the question the file answers later is
"what did it take to get this frame", and a retry is part of that answer rather
than a second frame.

It exists because every later claim in this repo is a claim about a
distribution. The gate can only be calibrated against frames whose scores are
recorded next to the prompt version that produced them. The drift run holds a
prompt and a seed still and swaps the model underneath, which is only legible
if the row proves that nothing else moved. And the sameness run needs to show
novelty flattening over many generations, which is a shape you can only plot
from a file that was being written before anyone thought to look at it.

`cost_usd` is null on every row here, and that is a recorded fact rather than a
missing feature: generation runs on hardware already owned, so there is no
per-frame price, and estimating one would quietly turn the scorecard into
fiction. The column exists so a metered backend can fill it without reshaping
the file.

## The sameness run

![Tightening the gate on a fixed pool of 200 grounds](runs/sameness/plot.png)

"Reliably" cuts both ways. A gate can be tightened until nothing new survives,
and no pass rate will ever show it, because a gate that only accepts near-copies
of what it already knows can be tuned to accept them every time. That is a
brand that has stopped moving, and it is the failure this run exists to make
visible. Two hundred grounds from one prompt were generated once, on the same
model and tier, and re-scored at five threshold sets from loose to tight. The
novelty bar was switched off for the pool while this ran: novelty is the thing
being measured here, so it is neither a knob nor a filter. Three lines come
out. The pass rate falls, from 165 accepted to three. The mean pairwise novelty
of what survives holds around 0.16 for four steps and then halves at the last,
which is the flat line arriving: the three survivors are alike, if still
tellable apart by eye. And the third line, agreement with the designer's 27
labelled frames, peaks one step looser than the shipped gate and falls from
there. That third line is the point of the figure. Past the peak, every notch
tighter buys a smaller, samer accepted set and a gate that agrees with its
designer less. A tighter gate is not a better one.

The bar stays where it ships, at step 2 (ruled 2026-09-15). Step 1 agrees with
the labels on one more frame, and the difference is a single bar, the share of
a frame that may be flat magenta, at 6 percent instead of 4. One frame in 27 is
not evidence to move a threshold on, and the shipped value was set from the
same 27 frames by a written procedure; the next labelled batch decides it.
What did move is the sweep itself: its first table stepped the wash bars past
the pool's own range and accepted nothing at the two tight steps, which is a
badly chosen sweep and not a result. The pool's edge softness sits between 10
and 11 and its dark chroma between 38 and 40, and the table in
`runs/sameness/steps.md` now walks through that range instead of over it.

![The accepted set at the loosest and the tightest step](runs/sameness/sheets.png)

```bash
python -m runs.pool --count 200                     # the pool, on the 4080
python -m runs.sameness --pool surfaces/_pool --steps 5
```
