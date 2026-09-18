import { runs } from "@/fixtures/runs";
import type { Surface, SurfaceId } from "@/fixtures/types";
import { cn } from "@/lib/utils";

export function SurfaceList({
  surfaces,
  selected,
  onSelect,
  scoreFor,
}: {
  surfaces: Surface[];
  selected: SurfaceId;
  onSelect: (id: SurfaceId) => void;
  scoreFor: (surface: Surface) => number;
}) {
  return (
    <div className="p-5">
      <h2 className="font-mono text-[11px] tracking-[0.14em] uppercase text-fg-soft">surfaces</h2>
      <ul className="mt-4 space-y-1">
        {surfaces.map((surface) => {
          const active = surface.id === selected;
          return (
            <li key={surface.id}>
              <button
                type="button"
                onClick={() => onSelect(surface.id)}
                aria-current={active}
                className={cn(
                  "flex w-full items-center gap-3 rounded-chip border-l py-2 pl-3 pr-2 text-left transition-colors",
                  active ? "border-indigo text-fg" : "border-transparent text-fg-soft hover:text-fg",
                )}
              >
                <img
                  src={surface.accepted.image}
                  alt=""
                  className="h-9 w-14 rounded-chip object-cover"
                />
                <span className="font-mono text-[11px] tracking-[0.14em] uppercase">
                  {surface.id}
                </span>
                <span className="ml-auto font-mono text-[11px] tabular-nums">
                  {scoreFor(surface).toFixed(2)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      <div className="mt-6 space-y-4 border-t border-hairline pt-5">
        {runs.map((run) => (
          <figure key={run.id}>
            <img src={run.image} alt={run.caption} className="w-full rounded-chip" />
            <figcaption className="mt-1 font-mono text-[11px] tracking-[0.14em] uppercase text-fg-soft">
              {run.caption}
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}
