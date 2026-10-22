import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Empty, ErrorState, Loading } from "@/components/States";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { api, type CallSummary } from "@/lib/api";
import { formatMs, formatPhone, formatWhen } from "@/lib/format";

const FILTERS = ["all", "booked", "escalated", "missed", "spam", "qualified"];

export function Calls() {
  const [calls, setCalls] = useState<CallSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");

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
  if (!calls) return <Loading label="Pulling the call log…" />;

  return (
    <div className="space-y-5">
      <header>
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-copper">Transcripts</p>
        <h1 className="mt-1 font-display text-4xl">Call log</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Every turn keeps the caller’s words, Riley’s reply, and how long the brain took. Open a row for the full
          transcript and the CRM events that fired.
        </p>
      </header>
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setFilter(item)}
              className={`rounded-full px-3 py-1 text-xs capitalize ${filter === item ? "bg-ink text-paper" : "bg-card text-muted-foreground border border-border"}`}
            >
              {item.replaceAll("_", " ")}
            </button>
          ))}
        </div>
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search name, phone, or issue"
          className="md:max-w-xs"
          aria-label="Search calls"
        />
      </div>
      {visible.length === 0 ? (
        <Empty title="Nothing in this filter" body="Start a simulator call, or clear the search to see the sample log." />
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-card">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                <tr className="border-b border-border">
                  <th className="px-4 py-3 font-medium">When</th>
                  <th className="px-4 py-3 font-medium">Caller</th>
                  <th className="px-4 py-3 font-medium">Intent</th>
                  <th className="px-4 py-3 font-medium">Outcome</th>
                  <th className="px-4 py-3 font-medium">Latency</th>
                  <th className="px-4 py-3 font-medium">Channel</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((call) => (
                  <tr key={call.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-3 text-muted-foreground">{formatWhen(call.started_at)}</td>
                    <td className="px-4 py-3">
                      <Link to={`/calls/${call.id}`} className="font-medium hover:text-copper">
                        {call.caller_name || "Unknown caller"}
                      </Link>
                      <div className="text-xs text-muted-foreground">
                        {formatPhone(call.caller_phone)}
                        {call.issue ? ` · ${call.issue}` : ""}
                      </div>
                    </td>
                    <td className="px-4 py-3 capitalize text-muted-foreground">{(call.intent || "—").replaceAll("_", " ")}</td>
                    <td className="px-4 py-3">
                      <Badge tone={call.outcome || "open"}>{call.outcome || "open"}</Badge>
                    </td>
                    <td className="px-4 py-3 tabular-nums">{formatMs(call.avg_latency_ms)}</td>
                    <td className="px-4 py-3 capitalize text-muted-foreground">{call.channel}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
