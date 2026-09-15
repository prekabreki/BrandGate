# The hero

One generated ground under a coded foreground, and the candidate the gate refused.

| accepted | rejected |
|---|---|
| ![the accepted hero](accepted/hero.png) | ![the refused candidate, composed anyway](rejected/hero.png) |
| ground `hero-ground_turbo_2083_033d4aebd9d4_00001_.png` | ground `hero-ground_turbo_2005_bd922599fd22_00001_.png` |
| ground at the gate: **pass, on-brand 0.96** | ground at the gate: **fail, on-brand 0.74** |
| composed hero: **pass, on-brand 0.99** | composed anyway, to show what the gate kept off the site |
| wash: soft wash: darks at chroma 31, edges 7.9, every stop present | #B44C9E holds 6.8% of the frame as a flat area, over the 4% the rule allows |
| | the orbs separate: steepest edges 14.0, a bleed stays under 13 |

The ground is the only thing a model made: krea2 turbo, `hero-ground@3`, one seed each,
both rows in `runs/ledger.jsonl`. Everything on top is code. `compose.py` reads
`brand/tokens.json` into CSS variables, lays the mark, the wordmark in the text gradient,
the headline in ink and the tagline in graphite over the ground, adds the paper veil and
the grain that take T1 used, and renders it at 1600 by 900 through `lookdev/render.py`.
No colour is written in the script or the template; the template holds geometry.

The gate scored the grounds first. The refused one carries flat magenta over the 4
percent bar and separates into orbs where the rule asks for a bleed, and that is the
verdict that kept it off the site. It is composed here anyway because a refusal you
cannot see is a claim, and side by side the difference is the whole argument: the same
type, the same mark, the same veil, and one of them is Handsel.

The composed hero was scored too, with one thing declared. The composer renders the
same page a second time with the ground hidden and hands the gate the foreground as a
mask, so the wash is judged on the wash and not on the wordmark's edges. Before that
existed the hero failed the wash its own ground had passed, on the steepness of its own
letters. `accepted/foreground.png` is that mask; `accepted/score.json` is the verdict.

```bash
python -m surfaces.hero.compose --ground surfaces/_pool/<frame>.png --out surfaces/hero/accepted
python -m surfaces.hero.compose --ground <png> --out <dir> --headline "Six pieces of one thing."
```
