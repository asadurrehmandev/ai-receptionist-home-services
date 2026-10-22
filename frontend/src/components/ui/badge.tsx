import type { ReactNode } from "react";

import { titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

const TONE: Record<string, string> = {
  booked: "bg-success-soft text-success",
  rescheduled: "bg-success-soft text-success",
  kept: "bg-success-soft text-success",
  escalated: "bg-danger-soft text-danger",
  missed_transfer: "bg-danger-soft text-danger",
  callback: "bg-warning-soft text-warning",
  spam: "bg-warning-soft text-warning",
  qualified: "bg-info-soft text-info",
  in_progress: "bg-info-soft text-info",
  missed: "bg-muted text-foreground",
  out_of_area: "bg-muted text-foreground",
  cancelled: "bg-muted text-foreground",
  open: "bg-muted text-foreground",
  mock: "bg-muted text-foreground",
  live: "bg-primary-soft text-primary-text",
};

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
        "inline-flex h-5 items-center gap-1 rounded-sm px-1.5 text-xs font-medium capitalize",
        tone ? TONE[tone] || TONE.open : "bg-muted text-foreground",
        className,
      )}
    >
      {typeof children === "string" ? titleCase(children) : children}
    </span>
  );
}
