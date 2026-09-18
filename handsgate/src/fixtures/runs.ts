import driftPlot from "./images/run-drift.svg";
import samenessPlot from "./images/run-sameness.svg";
import type { RunPlot } from "./types";

export const runs: RunPlot[] = [
  { id: "drift", image: driftPlot, caption: "drift, last 24 runs" },
  { id: "sameness", image: samenessPlot, caption: "sameness, last 24 runs" },
];
