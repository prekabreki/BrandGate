import { useState } from "react";

import type { Score } from "@/fixtures/types";
import { cn } from "@/lib/utils";

function ScoreBar({ value, passed }: { value: number; passed: boolean }) {
  return (
    <div className="h-[3px] w-full bg-hairline/40">
      <div
        className={cn("h-full", passed ? "bg-indigo" : "bg-graphite")}
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  );
}

export function Breakdown({
  score,
  changedRule,
}: {
  score: Score;
  changedRule?: string | null | undefined;
}) {
  const [open, setOpen] = useState(false);

  const failedFirst = [...score.breakdown].sort((a, b) => {
    const af = score.failed_rules.includes(a.rule) ? 0 : 1;
    const bf = score.failed_rules.includes(b.rule) ? 0 : 1;
    return af - bf;
  });

  return (
    <div className="mt-4">
      <ul>
        {failedFirst.map((finding) => {
          const failed = score.failed_rules.includes(finding.rule);
          return (
            <li
              key={finding.rule}
              className={cn(
                "border-l py-3 pl-3",
                failed ? "border-graphite" : "border-transparent",
                changedRule === finding.rule && "hg-row-changed",
              )}
            >
              <div className="flex items-baseline gap-3">
                <span className="font-mono text-[11px] tracking-[0.14em] text-fg">
                  {finding.rule}
                </span>
                <span className="font-mono text-[11px] tabular-nums text-fg-soft">
                  {finding.score.toFixed(2)}
                </span>
              </div>
              <div className="mt-2">
                <ScoreBar value={finding.score} passed={finding.passed} />
              </div>
              <p className="mt-2 text-[15px] leading-normal text-fg-soft">{finding.reason}</p>
            </li>
          );
        })}
      </ul>

      {score.not_applicable.length > 0 && (
        <div className="mt-3 border-t border-hairline pt-3">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="font-mono text-[11px] tracking-[0.14em] uppercase text-fg-soft transition-colors hover:text-indigo"
          >
            not measured ({score.not_applicable.length})
          </button>
          {open && (
            <ul className="mt-2 space-y-2">
              {score.not_applicable.map((item) => (
                <li key={item.rule} className="flex gap-3">
                  <span className="font-mono text-[11px] tracking-[0.14em] text-fg-soft">
                    {item.rule}
                  </span>
                  <span className="text-[15px] leading-normal text-fg-soft">{item.reason}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
