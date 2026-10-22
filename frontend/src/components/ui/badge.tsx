import type { ReactNode } from "react";

import { OUTCOME_TONE, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

export function Badge({
  children,
  className,
  tone,
}: {
  children: ReactNode;
  className?: string;
  tone?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        tone ? OUTCOME_TONE[tone] || OUTCOME_TONE.open : "bg-muted text-foreground",
        className,
      )}
    >
      {typeof children === "string" ? titleCase(children) : children}
    </span>
  );
}
