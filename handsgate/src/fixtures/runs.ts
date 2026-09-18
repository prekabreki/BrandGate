import type { RunPlot } from "./types";

/*
 * The sameness figure is the real one, runs/sameness/plot.png, copied in by
 * scripts/tokens-to-tailwind.py.
 *
 * The drift plot has no image because the drift run has not been made. The first
 * build drew a sine wave and captioned it "drift, last 24 runs". On a tool whose
 * whole subject is catching drift, a decorative curve presented as a measurement is
 * the one defect that would matter, so it is an empty state until the run exists.
 */
export const runs: RunPlot[] = [
  {
    id: "sameness",
    image: "/runs/sameness.png",
    caption: "sameness, 5 threshold steps",
  },
  {
    id: "drift",
    image: null,
    caption: "drift",
    note: "specified, not yet run",
  },
];
