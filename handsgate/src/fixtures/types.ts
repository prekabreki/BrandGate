export type Finding = {
  rule: string; // "colour.01"
  check: string; // "palette" | "wash" | "contrast" | "band" | "manual"
  score: number; // 0..1
  passed: boolean;
  reason: string; // "the ground is #FAFAF8"
  detail: Record<string, unknown>;
};

export type Score = {
  verdict: "pass" | "fail";
  on_brand: number; // 0..1
  novelty: number; // 0..1
  thresholds: { on_brand_min: number; novelty_min: number };
  failed_rules: string[];
  breakdown: Finding[];
  not_applicable: { rule: string; check: string; reason: string }[];
};

export type Candidate = { image: string; score: Score };

export type SurfaceId = "hero" | "social" | "print" | "motion";

export type Surface = { id: SurfaceId; accepted: Candidate; rejected: Candidate };

export type Rule = { id: string | null; section: string; prose: string; check: string };

export type RunPlot = {
  id: "drift" | "sameness";
  caption: string;
  // null when the run has not been made. The panel says so rather than drawing
  // a shape: this tool is about not shipping things that were never measured.
  image: string | null;
  note?: string;
};
