import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";

import { CandidatePanel } from "@/components/handsel/CandidatePanel";
import { Glass } from "@/components/handsel/Glass";
import { Mark } from "@/components/handsel/Mark";
import { RulesPanel } from "@/components/handsel/RulesPanel";
import { SurfaceList } from "@/components/handsel/SurfaceList";
import { ThemeToggle, type Theme } from "@/components/handsel/ThemeToggle";
import { Wash } from "@/components/handsel/Wash";
import { rules as fixtureRules } from "@/fixtures/rules";
import { surfaceById, surfaces } from "@/fixtures/surfaces";
import type { Rule, Surface, SurfaceId } from "@/fixtures/types";
import { rescore } from "@/gate/rescore";

const title = "Handsel Gate, brand surface review";
const description =
  "An internal review screen for generated brand surfaces the scoring gate accepted or rejected.";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: HandselGate,
});

const surfaceIds: SurfaceId[] = ["hero", "social", "print", "motion"];

function HandselGate() {
  const [theme, setTheme] = useState<Theme>("paper");
  const [selected, setSelected] = useState<SurfaceId>("hero");
  const [rules, setRules] = useState<Rule[]>(fixtureRules);
  const [changedRule, setChangedRule] = useState<string | null>(null);
  const highlightTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Read the stored theme and the hash after mount, so the first render matches the server.
  useEffect(() => {
    const stored = localStorage.getItem("handsel-theme");
    if (stored === "paper" || stored === "night") setTheme(stored);

    const applyHash = () => {
      const id = window.location.hash.replace("#", "") as SurfaceId;
      if (surfaceIds.includes(id)) setSelected(id);
    };
    applyHash();
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "night");
  }, [theme]);

  useEffect(
    () => () => {
      if (highlightTimer.current) clearTimeout(highlightTimer.current);
    },
    [],
  );

  const selectTheme = (next: Theme) => {
    setTheme(next);
    localStorage.setItem("handsel-theme", next);
  };

  const selectSurface = (id: SurfaceId) => {
    setSelected(id);
    window.location.hash = id;
  };

  const surface = surfaceById(selected);

  const acceptedScore = useMemo(() => rescore(selected, rules), [selected, rules]);

  const listScore = (item: Surface) =>
    item.id === selected ? acceptedScore.on_brand : rescore(item.id, rules).on_brand;

  const editRule = (index: number, prose: string) => {
    const next = rules.map((rule, i) => (i === index ? { ...rule, prose } : rule));
    setRules(next);
    const id = next[index]?.id ?? null;
    setChangedRule(id);
    if (highlightTimer.current) clearTimeout(highlightTimer.current);
    highlightTimer.current = setTimeout(() => setChangedRule(null), 1400);
  };

  const resetRules = () => {
    setRules(fixtureRules);
    setChangedRule(null);
  };

  return (
    <div className="relative min-h-screen bg-ground font-body text-[17px] leading-normal text-fg">
      <Wash />

      <div className="relative mx-auto max-w-[1440px] px-5 py-8">
        <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <Mark />
            <h1 className="hg-flow-text mt-3 font-display text-[44px] font-extrabold leading-[0.9] tracking-[-0.045em]">
              Handsel Gate
            </h1>
            <p className="mt-3 max-w-[60ch] text-fg-soft">
              Review the surfaces the gate accepted and rejected. Edit a rule to see the score move.
            </p>
            {/*
              Said on the page, not just in the README. A reviewer who does not know this
              is reading fixtures as if they were a running system, and the first thing
              they will notice is the hand-typed hex codes in the reasons.
            */}
            <p className="mt-4 max-w-[62ch] rounded-chip border border-dashed border-hairline px-3 py-2 font-mono text-[11px] leading-[1.7] text-fg-soft">
              <span className="tracking-[0.14em] text-indigo uppercase">prototype</span>{" "}
              Every score here is a fixture typed by hand, hex codes and all, and the rule edit
              is a lookup that reproduces one rehearsed path. The real gate is a Python pipeline
              that measures rendered images and writes <code>score.json</code>. This screen was
              built in a weekend on Lovable to test the interaction and the brand. It is not how
              the thing would be built.
            </p>
          </div>
          <ThemeToggle theme={theme} onChange={selectTheme} />
        </header>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[240px_minmax(0,1fr)_340px]">
          <Glass delay={0} className="h-max">
            <SurfaceList
              surfaces={surfaces}
              selected={selected}
              onSelect={selectSurface}
              scoreFor={listScore}
            />
          </Glass>

          <Glass delay={120} className="h-max p-5">
            <div className="flex items-baseline justify-between font-mono text-[11px] tracking-[0.14em] uppercase text-fg-soft">
              <span>{surface.id}</span>
              <span>candidates</span>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
              <CandidatePanel
                label="accepted"
                candidate={{ image: surface.accepted.image, score: acceptedScore }}
                changedRule={changedRule}
              />
              <CandidatePanel label="rejected" candidate={surface.rejected} />
            </div>
          </Glass>

          <Glass delay={240} className="h-max">
            <RulesPanel rules={rules} onEdit={editRule} onReset={resetRules} />
          </Glass>
        </div>
      </div>
    </div>
  );
}
