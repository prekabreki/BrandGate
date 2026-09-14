---
repo: BrandGate
updated: 2026-09-15
open_issues: [1,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
in_flight: []
blocked_on:
  - issue: 3
    reason: needs Pétur to label 20 calibration images and record docs/rule-edit.mp4
  - issue: 4
    reason: blocked by 3
  - issue: 10
    reason: blocked by 3
  - issue: 11
    reason: blocked by 3
---

The generator (#2) and the gate (#3) both run. #2 is closed. #3's machinery is complete and
pushed but the issue stays open on its calibration write-up, which is the deliverable that
makes it an argument: 10 of 20 images, and only take 1 carries a designer label.

Six decisions were taken 2026-09-14 and recorded in code rather than in a thread: a mark and
its wordmark are ONE gesture (pipeline/checks/motif.py), on_brand_min stays at 0.75 until
twenty labelled images exist (brand/gate.toml), open_clip arrives with #10, and the
calibration set comes from a generated batch.

Next session is two commands with ComfyUI up: `python -m pipeline.calibrate batch --count 30`
then `sheet`, which produces docs/calibration-sheet.png for Pétur to label in one sitting.
ComfyUI is currently down. Nothing is on a branch; everything is on master and pushed.
