import type { Candidate } from "@/fixtures/types";

import { Breakdown } from "./Breakdown";

export function CandidatePanel({
  label,
  candidate,
  changedRule,
}: {
  label: "accepted" | "rejected";
  candidate: Candidate;
  changedRule?: string | null | undefined;
}) {
  const { score } = candidate;
  return (
    <div className="hg-glass p-4">
      <div className="flex items-baseline justify-between font-mono text-[11px] tracking-[0.14em] uppercase">
        <span className="text-fg">{label}</span>
        <span className="text-fg-soft">
          {score.verdict} · {score.on_brand.toFixed(4)}
        </span>
      </div>
      <img
        src={candidate.image}
        alt={`${label} candidate`}
        className="mt-3 w-full rounded-chip object-cover"
      />
      <Breakdown score={score} changedRule={changedRule} />
    </div>
  );
}
