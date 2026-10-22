import { useNavigate } from "react-router-dom";

import { CallerName, LiveMark } from "@/components/CallerName";
import { Badge } from "@/components/ui/badge";
import type { CallSummary } from "@/lib/api";
import { formatDuration, formatMs, formatWhen, isLiveCall, titleCase } from "@/lib/format";

function issueText(call: CallSummary): string {
  if (call.issue) return call.issue;
  const summary = (call.summary || "").trim();
  const outcome = (call.outcome || "").replaceAll("_", " ").trim().toLowerCase();
  if (!summary || summary.toLowerCase() === outcome || summary.toLowerCase().startsWith(`${outcome} ·`)) return "–";
  return summary;
}

export function CallsTable({
  calls,
  showTimings = false,
  channel = false,
}: {
  calls: CallSummary[];
  showTimings?: boolean;
  channel?: boolean;
}) {
  const navigate = useNavigate();

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <ul className="sm:hidden">
        {calls.map((call) => {
          const live = isLiveCall(call);
          const who = call.caller_name || call.caller_phone || "caller";
          return (
            <li key={call.id} className="border-b border-border last:border-0">
              <button
                type="button"
                className="flex w-full items-start justify-between gap-3 px-3 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                onClick={() => navigate(`/calls/${call.id}`)}
                aria-label={`Open call from ${who}`}
              >
                <span className="min-w-0">
                  <CallerName name={call.caller_name} phone={call.caller_phone} />
                  <span className="mt-0.5 block truncate text-sm text-muted-foreground">{issueText(call)}</span>
                  <span className="mt-0.5 block text-xs tabular-nums text-subtle">{formatWhen(call.started_at, false)}</span>
                </span>
                <span className="shrink-0">
                  {live ? (
                    <Badge tone="in_progress">In progress</Badge>
                  ) : (
                    <Badge tone={call.outcome || "open"}>{call.outcome || "open"}</Badge>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <div className="hidden overflow-x-auto sm:block">
        <table className="w-full min-w-[680px] border-collapse text-left text-sm">
          <thead className="bg-surface text-xs font-medium text-muted-foreground">
            <tr className="h-9 border-b border-border">
              <th className="sticky left-0 z-10 bg-surface px-3 font-medium">Time</th>
              <th className="px-3 font-medium">Caller</th>
              <th className="px-3 font-medium">Issue</th>
              <th className="px-3 font-medium">Outcome</th>
              <th className="px-3 text-right font-medium">Duration</th>
              {channel && <th className="px-3 font-medium">Channel</th>}
              {showTimings && (
                <th className="px-3 text-right font-medium" title="Rule engine response time (demo)">
                  Rule engine
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {calls.map((call) => {
              const live = isLiveCall(call);
              const who = call.caller_name || call.caller_phone || "caller";
              return (
                <tr
                  key={call.id}
                  tabIndex={0}
                  aria-label={`Open call from ${who}`}
                  className="group h-10 cursor-pointer border-b border-border last:border-0 hover:bg-muted focus-visible:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                  onClick={() => navigate(`/calls/${call.id}`)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") navigate(`/calls/${call.id}`);
                  }}
                >
                  <td className="sticky left-0 z-10 whitespace-nowrap bg-card px-3 tabular-nums text-subtle group-hover:bg-muted group-focus-visible:bg-muted">
                    {formatWhen(call.started_at, false)}
                  </td>
                  <td className="max-w-[180px] truncate px-3">
                    <CallerName name={call.caller_name} phone={call.caller_phone} />
                  </td>
                  <td className="max-w-[240px] truncate px-3 text-muted-foreground">{issueText(call)}</td>
                  <td className="px-3">
                    {live ? (
                      <Badge tone="in_progress">In progress</Badge>
                    ) : (
                      <Badge tone={call.outcome || "open"}>{call.outcome || "open"}</Badge>
                    )}
                  </td>
                  <td className="px-3 text-right tabular-nums">
                    {live ? <LiveMark /> : formatDuration(call.started_at, call.ended_at) || "–"}
                  </td>
                  {channel && <td className="px-3 text-muted-foreground">{titleCase(call.channel)}</td>}
                  {showTimings && (
                    <td className="px-3 text-right font-mono text-xs tabular-nums text-subtle" title="Rule engine response time (demo)">
                      {live ? "–" : formatMs(call.avg_latency_ms)}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
