import { AlertCircle, Inbox } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

export function Loading({ label = "Loading the desk…" }: { label?: string }) {
  return (
    <div className="space-y-2" aria-live="polite" aria-busy="true">
      <div className="h-8 w-40 animate-pulse rounded-sm bg-muted" />
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="h-10 animate-pulse rounded-sm bg-muted" />
      ))}
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-danger/30 bg-danger-soft p-4" role="alert">
      <div className="flex items-start gap-2">
        <AlertCircle className="mt-0.5 h-4 w-4 text-danger" aria-hidden />
        <div>
          <h2 className="text-md font-semibold text-danger">The desk could not load</h2>
          <p className="mt-1 max-w-xl text-sm text-foreground">{message}</p>
          {onRetry && (
            <Button className="mt-3" variant="outline" onClick={onRetry}>
              Retry
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export function Empty({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-border px-5 py-8">
      <Inbox className="h-6 w-6 text-muted-foreground" aria-hidden />
      <h3 className="mt-3 text-md font-semibold">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{body}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
