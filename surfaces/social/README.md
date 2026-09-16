# The social card set

One ground, one headline, three crops: 1080 square, 1080 by 1920 story, 1200 by 630 OG.

| square | story | OG |
|---|---|---|
| ![square](accepted/square.png) | ![story](accepted/story.png) | ![OG](accepted/og.png) |
| **pass, on-brand 0.98** | **pass, on-brand 0.99** | **pass, on-brand 0.98** |

The recipe is the hero's. What changes per size is one row in a table in `compose.py`:
mark width, the three type sizes, the veil's midpoint, and where the ground sits. The safe
margin is 5 percent of the short side everywhere. Ground `ground.png`,
which the gate passed at 0.97 before anything was laid on it.

**The gate chose the crops.** The square was scored at six horizontal positions across
the ground. From 0 to 25 percent the crop concentrates the magenta orb past the 4 percent
flat-accent bar; at 80 percent indigo leaves the frame and the wash loses a stop; 40 and
60 pass. The story is 9:16 cut from a 16:9 ground and no cover crop of it passes at all,
because every vertical slice either drops a stop or is mostly one orb. So the story carries
the ground as a horizontal band faded into the paper above and below, which is also what
the mark is: a band. Those are not taste calls written into a comment; they are the
verdicts, and the comment above the table says so.

## The one the gate refused

| square | story | OG |
|---|---|---|
| ![square, refused ground](rejected/square.png) | ![story, refused ground](rejected/story.png) | ![OG, refused ground](rejected/og.png) |
| fail, on-brand 0.85, colour.01 and gradient.03 | fail, on-brand 0.81, colour.01 and gradient.03 | fail, on-brand 0.88, gradient.03 |

Ground `ground.png`, refused at the gate for a different rule than
the hero's: **#B44C9E holds 3.2% of the wash; every stop needs 6%** The hero's candidate was refused for flat magenta; this one keeps
its palette and fails on softness alone. Composed anyway so the refusal can be seen. The square
and the OG carry the fault through: #B44C9E holds 7.6% of the frame as a flat area, over the 4% the rule allows
The story's band shrinks the ground enough that the card itself scores 0.75
and fails on motif.01, motif.02;
the ground was refused before it got there, and that is the order the pipeline runs in.

```bash
python -m surfaces.social.compose --ground surfaces/_pool/<frame>.png --out surfaces/social/accepted
python -m surfaces.social.compose --ground <png> --out <dir> --headline "..." --only og
```

Scores are from 2026-09-16 late, recomposed with the lockup rule (the type stack starts on the first apex line) on a box where every rule runs. The refused ground is the hero's refused ground, `hero-ground@6`: dull wash, mean chroma 27. Composed, the square and story also read their ground as a rose-grey no rule allows (`colour.01`), and the story loses indigo from the wash entirely.
