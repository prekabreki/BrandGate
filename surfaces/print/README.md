# The print one-pager

A4, flat. Paper with a hairline border, no glass, no grain, the generated ground as a banner
band and not full bleed. Type in points, body 10.5 pt Archivo. `onepager.pdf` is the print
file; `onepager.png` is the same page at 2x for the gate.

| accepted | refused ground |
|---|---|
| ![the one-pager](accepted/onepager.png) | ![the one-pager on the refused ground](rejected/onepager.png) |
| ground `ground.png`, at the gate **pass, on-brand 0.96** | ground `ground.png`, at the gate **fail, on-brand 0.76** |
| page: **pass, on-brand 1.00** | page: **pass, on-brand 1.00** |
| | #B44C9E holds 5.4% of the frame as a flat area, over the 4% the rule allows |

The three figures at the foot of the page are read from `runs/sameness/results.json` and
`docs/calibration-labels.json` when the page is composed, not typed, so the sheet cannot
drift from the run it describes.

**What the refused column shows.** Print confines the ground to a band, so a ground the gate
refused for flat magenta leaves the composed page scoring 1.00: the magenta
is a sliver of an A4 sheet. That is not the gate being lenient, it is the order the pipeline
runs in. The ground is judged first and this one did not get through; the page is here to
show what the band recipe does to a fault, which is shrink it, not remove it.

```bash
python -m surfaces.print.compose --ground surfaces/_pool/<frame>.png --out surfaces/print/accepted
```
