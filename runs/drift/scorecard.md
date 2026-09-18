# Drift: the same prompt and the same seeds, through two models

96 frames, 2 models, 48 seeds (4000..4047), tier turbo. The gate passes a frame at on-brand 0.75 and novelty 0.12.

| | krea2 | flux2 |
|---|---|---|
| frames scored | 48 | 48 |
| pass rate | 96% | 54% |
| on-brand mean | 0.9751 | 0.9511 |
| on-brand spread (sd) | 0.0010 | 0.0565 |
| on-brand range | 0.9728 to 0.9772 | 0.7212 to 0.9816 |
| novelty mean | 0.188 | 0.273 |
| median latency | 16 s | 36 s |
| mean latency | 16 s | 38 s |
| generation errors | 0 | 0 |
| cost per frame | local, unmetered | local, unmetered |

## Which rules fired

| rule | krea2 | flux2 | one frame's reason |
|---|---|---|---|
| `colour.02` | 0/48 | 3/48 | a text region at 428,1 sits at 2.1:1 against its ground, under the 4.5:1 bar |
| `colour.04` | 0/48 | 3/48 | a text region at 428,1 sits at 2.1:1 against its ground, under the 4.5:1 bar |
| `gradient.03` | 2/48 | 21/48 | the orbs separate: steepest edges 15.2, a bleed stays under 14 |
| `type.03` | 0/48 | 3/48 | a text region at 428,1 sits at 2.1:1 against its ground, under the 4.5:1 bar |

