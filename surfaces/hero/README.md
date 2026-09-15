# The hero

One generated ground under a coded foreground, and the candidate the gate refused.

| accepted | rejected |
|---|---|
| ![the accepted hero](accepted/hero.png) | ![the refused candidate, composed anyway](rejected/hero.png) |
| ground `ground.png` | ground `ground.png` |
| ground at the gate: **pass, on-brand 0.96** | ground at the gate: **fail, on-brand 0.69** |
| composed hero: **pass, on-brand 0.99** | composed anyway: **fail, on-brand 0.86**, colour.03, gradient.03 |
| wash: soft wash: darks at chroma 34, edges 10.1, every stop present | #B44C9E holds 8.7% of the frame as a flat area, over the 4% the rule allows |
| | the darks are saturated (chroma 60, a wash stays under 45); the orbs separate: steepest edges 13.8, a bleed stays under 13 |

The ground is the only thing a model made: krea2 turbo, `hero-ground@3`, one seed each,
both rows in `runs/ledger.jsonl`. Everything on top is code. `compose.py` reads
`brand/tokens.json` into CSS variables, lays the mark, the wordmark in the text gradient,
the headline in ink and the tagline in graphite over the ground, adds the paper veil and
the grain that take T1 used, and renders it at 1600 by 900 through `lookdev/render.py`.
No colour is written in the script or the template; the template holds geometry.

The gate scored the grounds first. The refused one carries flat magenta over the 4
percent bar and separates into orbs where the rule asks for a bleed, and that is the
verdict that kept it off the site. It is also a frame the designer labelled off by hand,
"too much separation, not enough gradient", so the gate and the eye agree on this pair.
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
python -m surfaces.hero.compose --ground surfaces/_pool/<frame>.png --out surfaces/hero/accepted
python -m surfaces.hero.compose --ground <png> --out <dir> --headline "Six pieces of one thing."
```
