import { useState } from "react";

import { ruleSections } from "@/fixtures/rules";
import type { Rule } from "@/fixtures/types";
import { cn } from "@/lib/utils";

function RuleLine({
  rule,
  onCommit,
}: {
  rule: Rule;
  onCommit: (prose: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(rule.prose);

  if (editing) {
    return (
      <textarea
        autoFocus
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={() => {
          setEditing(false);
          if (draft !== rule.prose) onCommit(draft);
        }}
        rows={Math.max(2, Math.ceil(draft.length / 60))}
        className="w-full resize-none rounded-chip border border-indigo bg-transparent p-2 text-[15px] leading-normal text-fg outline-none"
      />
    );
  }

  return (
    <button
      type="button"
      onClick={() => {
        setDraft(rule.prose);
        setEditing(true);
      }}
      className={cn(
        "block w-full rounded-chip p-2 text-left text-[15px] leading-normal transition-colors hover:text-fg",
        rule.id ? "text-fg" : "text-fg-soft",
      )}
    >
      {rule.id && (
        <span className="mr-2 font-mono text-[11px] tracking-[0.14em] text-fg-soft">{rule.id}</span>
      )}
      {rule.prose}
    </button>
  );
}

export function RulesPanel({
  rules,
  onEdit,
  onReset,
}: {
  rules: Rule[];
  onEdit: (index: number, prose: string) => void;
  onReset: () => void;
}) {
  return (
    <div className="p-5">
      <div className="flex items-baseline justify-between">
        <h2 className="font-mono text-[11px] tracking-[0.14em] uppercase text-fg-soft">rules</h2>
        <button
          type="button"
          onClick={onReset}
          className="font-mono text-[11px] tracking-[0.14em] uppercase text-indigo transition-colors hover:text-fg"
        >
          reset rules
        </button>
      </div>

      <div className="mt-4 space-y-6">
        {ruleSections.map((section) => (
          <div key={section}>
            <h3 className="font-mono text-[11px] tracking-[0.14em] uppercase text-fg-soft">
              {section}
            </h3>
            <div className="mt-2 space-y-1">
              {rules.map((rule, index) =>
                rule.section === section ? (
                  <RuleLine
                    key={`${section}-${index}`}
                    rule={rule}
                    onCommit={(prose) => onEdit(index, prose)}
                  />
                ) : null,
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
