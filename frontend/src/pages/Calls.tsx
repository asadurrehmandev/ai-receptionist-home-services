import { useEffect, useMemo, useState } from "react";

import { CallsTable } from "@/components/CallsTable";
import { Empty, ErrorState, Loading } from "@/components/States";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, type CallSummary } from "@/lib/api";
import { cn } from "@/lib/utils";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "booked", label: "Booked" },
  { id: "escalated", label: "Escalated" },
  { id: "missed", label: "Missed" },
  { id: "spam", label: "Spam" },
  { id: "qualified", label: "Qualified" },
];

export function Calls() {
  const [calls, setCalls] = useState<CallSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [showTimings, setShowTimings] = useState(false);

  function load() {
    api
      .calls()
      .then((payload) => {
        setCalls(payload.calls);
        setError(null);
      })
      .catch((reason: Error) => setError(reason.message));
  }

  useEffect(() => {
    load();
  }, []);

  const visible = useMemo(() => {
    if (!calls) return [];
    return calls.filter((call) => {
      const outcome = call.outcome || "open";
      if (filter !== "all" && outcome !== filter) return false;
      const haystack = `${call.caller_name || ""} ${call.issue || ""} ${call.caller_phone || ""}`.toLowerCase();
      return haystack.includes(query.trim().toLowerCase());
    });
  }, [calls, filter, query]);

  if (error && !calls) return <ErrorState message={error} onRetry={load} />;
  if (!calls) return <Loading label="Loading calls…" />;

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Filter calls">
          {FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={filter === item.id}
              onClick={() => setFilter(item.id)}
              className={cn(
                "h-8 rounded-md px-2.5 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                filter === item.id ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search name, phone, or issue"
            className="w-full sm:w-64"
            aria-label="Search calls"
          />
          <Button type="button" size="sm" variant="outline" aria-pressed={showTimings} onClick={() => setShowTimings((value) => !value)}>
            {showTimings ? "Hide timings" : "Show timings"}
          </Button>
        </div>
      </div>
      {showTimings && (
        <p className="text-xs text-subtle">Rule engine response time (demo). This is not voice latency.</p>
      )}
      {visible.length === 0 ? (
        <Empty title="No calls in this view" body="Clear the search, or place a test call in the simulator." />
      ) : (
        <CallsTable calls={visible} showTimings={showTimings} channel />
      )}
    </div>
  );
}
