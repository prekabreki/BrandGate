import { cn } from "@/lib/utils";

export type Theme = "paper" | "night";

export function ThemeToggle({
  theme,
  onChange,
}: {
  theme: Theme;
  onChange: (next: Theme) => void;
}) {
  return (
    <div className="flex items-center gap-1 rounded-chip border border-hairline px-1 py-1 font-mono text-[11px] tracking-[0.14em] uppercase">
      {(["paper", "night"] as Theme[]).map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          aria-pressed={theme === option}
          className={cn(
            "rounded-chip px-2 py-1 transition-colors",
            theme === option ? "text-indigo" : "text-fg-soft hover:text-fg",
          )}
        >
          {option}
        </button>
      ))}
    </div>
  );
}
