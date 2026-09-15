# Sameness run: the five threshold sets

Pool: `surfaces/_pool`, 200 frames, scored in filename order. Novelty: perceptual hash and CLIP (ViT-B-32). Every other key in `brand/gate.toml` stayed at its shipped value. `verdict.novelty_min` was set to 0 for pool acceptance: novelty is what this run measures, so it is neither a knob nor a filter here. Each frame's novelty against the accepted set is still in `results.json`.

Reproduce: `python -m runs.pool --count 200` on the 4080, then `python -m runs.sameness --pool surfaces/_pool --steps 5`.

## Thresholds, verbatim

| step | `verdict.on_brand_min` | `palette.forbid_mass` | `wash.dark_chroma_max` | `wash.edge_max` | `wash.stop_share_min` |
|---|---|---|---|---|---|
| 0 | 0.6 | 0.1 | 60.0 | 20.0 | 0.02 |
| 1 | 0.7 | 0.06 | 52.0 | 16.0 | 0.04 |
| 2 (shipped) | 0.75 | 0.04 | 45.0 | 13.0 | 0.06 |
| 3 | 0.85 | 0.025 | 40.0 | 11.5 | 0.08 |
| 4 | 0.9 | 0.02 | 38.0 | 11.0 | 0.09 |

## What each step did

| step | accepted | pass rate | mean pairwise novelty of accepted | designer agreement (of 27) | false passes | false fails |
|---|---|---|---|---|---|---|
| 0 | 165 of 200 | 82% | 0.162 | 18 (67%) | 9 | 0 |
| 1 | 145 of 200 | 72% | 0.160 | 25 (93%) | 2 | 0 |
| 2 | 79 of 200 | 40% | 0.155 | 24 (89%) | 2 | 1 |
| 3 | 20 of 200 | 10% | 0.164 | 23 (85%) | 2 | 2 |
| 4 | 3 of 200 | 2% | 0.084 | 22 (81%) | 1 | 4 |
