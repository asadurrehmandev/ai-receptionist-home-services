import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ErrorState, Loading } from "@/components/States";
import { Badge } from "@/components/ui/badge";
import { api, type CallDetail as CallDetailType } from "@/lib/api";
import { formatMs, formatPhone, formatWhen } from "@/lib/format";

export function CallDetail() {
  const { id } = useParams();
  const [call, setCall] = useState<CallDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .call(id)
      .then((payload) => {
        setCall(payload);
        setError(null);
      })
      .catch((reason: Error) => setError(reason.message));
  }, [id]);

  if (error) return <ErrorState message={error} />;
  if (!call) return <Loading label="Opening the transcript…" />;

  return (
    <div className="space-y-5">
      <Link to="/calls" className="text-sm text-copper">
        Back to the log
      </Link>
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-copper">{formatWhen(call.started_at)}</p>
          <h1 className="mt-1 font-display text-4xl">{call.caller_name || "Unknown caller"}</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {formatPhone(call.caller_phone)}
            {call.caller_address ? ` · ${call.caller_address}` : ""}
            {call.issue ? ` · ${call.issue}` : ""}
          </p>
        </div>
        <Badge tone={call.outcome || "open"}>{call.outcome || "open"}</Badge>
      </header>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(260px,0.8fr)]">
        <ol className="space-y-3 rounded-lg border border-border bg-card p-4">
          {call.turns.map((turn, index) => (
            <li key={`${turn.created_at}-${index}`} className={turn.role === "agent" ? "pl-6" : "pr-6"}>
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                {turn.role === "agent" ? "Riley" : "Caller"}
                {turn.latency_ms != null ? ` · ${formatMs(turn.latency_ms)}` : ""}
              </div>
              <p
                className={`mt-1 rounded-2xl px-3 py-2 text-sm leading-6 ${
                  turn.role === "agent" ? "bg-[#f3e6da]" : "bg-[#efeae2]"
                }`}
              >
                {turn.text}
              </p>
            </li>
          ))}
        </ol>
        <aside className="space-y-3">
          <h2 className="font-display text-2xl">What the desk did</h2>
          {call.events.length === 0 && <p className="text-sm text-muted-foreground">No booking, text, or transfer on this call.</p>}
          {call.events.map((event, index) => (
            <article key={`${event.type}-${index}`} className="rounded-lg border border-border bg-card p-3">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">{event.type}</div>
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs leading-5 text-[#3c3832]">
                {JSON.stringify(event.payload, null, 2)}
              </pre>
            </article>
          ))}
        </aside>
      </div>
    </div>
  );
}
