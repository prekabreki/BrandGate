/*
 * This is a lookup, not a scorer.
 *
 * The real gate is a Python pipeline that reads the same rules file and scores
 * rendered surfaces. This function is the seam where it plugs in: same input
 * (a surface id and the current rules), same output shape (a Score). Until then
 * it reproduces the rehearsed hero edit and returns the fixture for everything else.
 */

import { surfaceById } from "@/fixtures/surfaces";
import type { Rule, Score } from "@/fixtures/types";

export function rescore(surfaceId: string, rules: Rule[]): Score {
  const fixture = surfaceById(surfaceId).accepted.score;
  if (surfaceId !== "hero") return fixture;

  const line = rules.find((r) => r.id === "colour.01")?.prose.toLowerCase() ?? "";
  const hasPaper = line.includes("paper");
  const hasMist = line.includes("mist");

  if (hasPaper) return fixture;

  const replace = (patch: Partial<Score["breakdown"][number]>): Score["breakdown"] =>
    fixture.breakdown.map((f) => (f.rule === "colour.01" ? { ...f, ...patch } : f));

  if (hasMist) {
    return {
      ...fixture,
      on_brand: 0.93,
      breakdown: replace({ score: 0.79, passed: true, reason: "the ground is #ECEAF6" }),
    };
  }

  return {
    ...fixture,
    verdict: "fail",
    on_brand: 0.71,
    failed_rules: ["colour.01"],
    breakdown: replace({
      score: 0.41,
      passed: false,
      reason: "the ground #FAFAF8 is not an allowed ground",
    }),
  };
}
