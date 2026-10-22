import { Button } from "@/components/ui/button";

export function Loading({ label = "Loading the desk…" }: { label?: string }) {
  return (
    <div className="space-y-3" aria-live="polite">
      <div className="h-8 w-48 animate-pulse rounded-md bg-[#e7e0d4]" />
      <div className="grid gap-3 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-24 animate-pulse rounded-lg bg-[#e7e0d4]" />
        ))}
      </div>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-[#e7c8c4] bg-[#fbf6f4] p-5">
      <h2 className="font-display text-2xl">The desk didn’t answer</h2>
      <p className="mt-2 max-w-xl text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <Button className="mt-4" variant="outline" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-card px-5 py-8">
      <h3 className="font-display text-xl">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">{body}</p>
    </div>
  );
}
