# The hero

One generated ground under a coded foreground, and the candidate the gate refused.

| accepted | rejected |
|---|---|
| ![the accepted hero](accepted/hero.png) | ![the refused candidate, composed anyway](rejected/hero.png) |
| ground `ground.png`: the procedural band, `ground_mesh_2_v1` | ground `ground.png`: krea2 turbo, `hero-ground@6` seed 5000 |
| ground at the gate: **pass, on-brand 0.95** | ground at the gate: **fail, on-brand 0.91**, gradient.03 |
| composed hero: **pass, on-brand 0.97** | composed anyway: **fail, on-brand 0.84**, gradient.03 |
| wash: soft wash: darks at chroma 56, edges 5.2, every stop present | the wash is dull (mean chroma 27, a ground carries at least 30) |

The accepted ground is code: `pipeline/mesh.py`, fitted by measurement to the frame the
designer liked best out of four prompt versions in one day (krea2 turbo, `hero-ground@7`,
seed 6002), after he asked whether an image model was the right tool for a gradient at
all. The refused ground is that model's `hero-ground@6`, the version he called muddy, and
the gate refuses it for the same thing: the wash is dull. Both are rows in
`runs/ledger.jsonl`, one with model `mesh`. Everything on top of either is code. The
whole day is in `docs/process/2026-09-16-*.html`. `compose.py` reads
`brand/tokens.json` into CSS variables, lays the mark, the wordmark in the text gradient,
the headline in ink and the tagline in graphite over the ground, adds the paper veil and
the grain that take T1 used, and renders it at 1600 by 900 through `lookdev/render.py`.
No colour is written in the script or the template; the template holds geometry.

The gate scored the grounds first. The refused one is a haze, mean chroma 27 where every
ground the designer has accepted sits at 32 and up, and that is the verdict that kept it
off the site. It is also the frame the designer refused by hand, "muddy", so the gate
and the eye agree on this pair.
The first pair did not: the designer refused the ground the gate had accepted and liked
the one it refused, both now in the calibration set (`docs/calibration.md`). It is composed here anyway because a refusal you
cannot see is a claim, and side by side the difference is the whole argument: the same
type, the same mark, the same veil, and one of them is Handsel.

The composed hero was scored too, with one thing declared. The composer renders the
same page a second time with the ground hidden and hands the gate the foreground as a
mask, so the wash is judged on the wash and not on the wordmark's edges. Before that
existed the hero failed the wash its own ground had passed, on the steepness of its own
letters. `accepted/hero-foreground.png` is that mask; `accepted/score.json` is the verdict.

```bash
python -m pipeline.mesh --seed 2 --out surfaces/_calibration
python -m surfaces.hero.compose --ground surfaces/_calibration/ground_mesh_2_v1.png --out surfaces/hero/accepted
python -m surfaces.hero.compose --ground <png> --out <dir> --headline "Six pieces of one thing."
```
