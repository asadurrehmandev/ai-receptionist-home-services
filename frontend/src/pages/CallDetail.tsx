import { ArrowLeft, Check } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { CallerName, LiveMark } from "@/components/CallerName";
import { ErrorState, Loading } from "@/components/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type CallDetail as CallDetailType } from "@/lib/api";
import { formatDuration, formatMs, formatPhone, formatWhen, isLiveCall, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

export function CallDetail() {
  const { id } = useParams();
  const [call, setCall] = useState<CallDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showTimings, setShowTimings] = useState(false);

  function load() {
    if (!id) return;
    api
      .call(id)
      .then((payload) => {
        setCall(payload);
        setError(null);
      })
      .catch((reason: Error) => setError(reason.message));
  }

  useEffect(() => {
    load();
  }, [id]);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!call) return <Loading label="Loading the transcript…" />;

  const live = isLiveCall(call);
  const fields = [
    { label: "Issue", value: call.issue },
    { label: "Intent", value: call.intent ? titleCase(call.intent) : null },
    { label: "Phone", value: call.caller_phone ? formatPhone(call.caller_phone) : null, mono: true },
    { label: "Address", value: call.caller_address },
    { label: "Channel", value: titleCase(call.channel) },
    { label: "Duration", value: live ? null : formatDuration(call.started_at, call.ended_at) },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          to="/calls"
          className="inline-flex h-8 items-center gap-1 rounded-md px-2 text-sm text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Calls
        </Link>
        <h2 className="text-lg font-semibold">
          <CallerName name={call.caller_name} phone={call.caller_phone} />
        </h2>
        {live ? <LiveMark /> : <Badge tone={call.outcome || "open"}>{call.outcome || "open"}</Badge>}
        <span className="text-xs tabular-nums text-subtle">{formatWhen(call.started_at)}</span>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="ml-auto"
          aria-pressed={showTimings}
          onClick={() => setShowTimings((value) => !value)}
        >
          {showTimings ? "Hide timings" : "Show timings"}
        </Button>
      </div>
      {showTimings && <p className="text-xs text-subtle">Rule engine response time (demo). This is not voice latency.</p>}

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
        <section aria-label="Transcript" className="rounded-lg border border-border bg-card">
          <ol className="space-y-4 p-4" aria-live="polite">
            {call.turns.map((turn, index) => (
              <li key={`${turn.created_at}-${index}`} className={turn.role === "agent" ? "mr-10" : "ml-10"}>
                <div className="mb-1 flex items-baseline justify-between gap-3 text-xs text-subtle">
                  <span>{turn.role === "agent" ? "Riley" : "Caller"}</span>
                  <span className="tabular-nums">
                    {formatWhen(turn.created_at, false)}
                    {showTimings && turn.latency_ms != null ? (
                      <span className="ml-2 font-mono" title="Rule engine response time (demo)">
                        {formatMs(turn.latency_ms)}
                      </span>
                    ) : null}
                  </span>
                </div>
                <p
                  className={cn(
                    "rounded-lg px-3 py-2 text-base",
                    turn.role === "agent" ? "border border-border bg-background" : "bg-muted",
                  )}
                >
                  {turn.text}
                </p>
              </li>
            ))}
          </ol>
          {call.events.length > 0 && (
            <div className="space-y-2 border-t border-border p-4">
              {call.events.map((event, index) => (
                <details key={`${event.type}-${index}`} className="rounded-md border border-border px-3 py-2">
                  <summary className="flex cursor-pointer items-center gap-1 text-sm font-medium">
                    Tool call: {event.type.replaceAll("_", " ")}
                    <Check className="h-3.5 w-3.5 text-success" aria-hidden />
                  </summary>
                  <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-5 text-muted-foreground">
                    {JSON.stringify(event.payload, null, 2)}
                  </pre>
                </details>
              ))}
            </div>
          )}
        </section>

        <aside aria-label="Extracted fields" className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-md font-semibold">Details</h3>
          <dl className="mt-3">
            {fields.map((field) => (
              <div key={field.label} className="flex items-start justify-between gap-3 border-b border-border py-2 last:border-0">
                <dt className="text-sm text-muted-foreground">{field.label}</dt>
                <dd className={cn("text-right text-sm", field.mono && "font-mono tabular-nums", !field.value && "text-subtle")}>
                  {field.label === "Duration" && live ? <LiveMark /> : field.value || "–"}
                </dd>
              </div>
            ))}
          </dl>
        </aside>
      </div>
    </div>
  );
}
