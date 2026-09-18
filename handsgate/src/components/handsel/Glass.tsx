import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** A glass panel on the wash. Rises once on load, staggered by index. */
export function Glass({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <section className={cn("hg-glass hg-rise", className)} style={{ animationDelay: `${delay}ms` }}>
      {children}
    </section>
  );
}
