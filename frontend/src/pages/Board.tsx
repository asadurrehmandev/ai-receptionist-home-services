import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ErrorState, Loading } from "@/components/States";
import { Badge } from "@/components/ui/badge";
import { api, type Overview } from "@/lib/api";
import { formatMs, formatPhone, formatWhen } from "@/lib/format";

export function Board() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api
      .overview()
      .then((payload) => {
        setData(payload);
        setError(null);
      })
      .catch((reason: Error) => setError(reason.message));
  }

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 8000);
    return () => window.clearInterval(timer);
  }, []);

  if (error && !data) return <ErrorState message={error} onRetry={load} />;
  if (!data) return <Loading />;

  const booked = data.counts.booked || 0;
  const escalated = data.counts.escalated || 0;
  const missed = data.counts.missed || 0;
  const metrics = [
    { label: "Calls handled", value: String(data.total_calls), note: "Simulator and phone" },
    { label: "Jobs booked", value: String(booked), note: "On the mock calendar" },
    { label: "Escalated", value: String(escalated), note: `To ${data.on_call.name}` },
    { label: "Median reply", value: formatMs(data.metrics.p50_ms), note: `p95 ${formatMs(data.metrics.p95_ms)}` },
  ];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-copper">
            {data.business.city} · {data.business.trade}
          </p>
          <h1 className="mt-1 font-display text-4xl leading-none text-ink">The line is covered.</h1>
          <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground">
            {data.business.agent_name} answers {data.business.name}, qualifies the job, and either books a 90-minute
            window or puts {data.on_call.name} on the call. Missed calls after close used to walk out the door.
          </p>
        </div>
        <div className="text-right text-sm text-muted-foreground">
          <div>{data.business.phone_display}</div>
          <div>{missed === 0 ? "No abandoned calls in this sample." : `${missed} caller${missed === 1 ? "" : "s"} hung up early.`}</div>
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((item) => (
          <article key={item.label} className="rounded-lg border border-border bg-card px-4 py-4">
            <div className="text-xs uppercase tracking-[0.14em] text-muted-foreground">{item.label}</div>
            <div className="mt-2 font-display text-4xl leading-none">{item.value}</div>
            <div className="mt-2 text-xs text-muted-foreground">{item.note}</div>
          </article>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(280px,0.9fr)]">
        <div className="overflow-hidden rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between px-4 py-3">
            <h2 className="font-display text-2xl">Recent calls</h2>
            <Link to="/calls" className="text-sm text-copper">
              Full log
            </Link>
          </div>
          {data.recent_calls.length === 0 ? (
            <p className="px-4 pb-4 text-sm text-muted-foreground">No calls yet. Open the simulator and book a job.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                  <tr className="border-y border-border">
                    <th className="px-4 py-2 font-medium">Caller</th>
                    <th className="px-4 py-2 font-medium">Issue</th>
                    <th className="px-4 py-2 font-medium">Outcome</th>
                    <th className="px-4 py-2 font-medium">Reply</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_calls.map((call) => (
                    <tr key={call.id} className="border-b border-border last:border-0">
                      <td className="px-4 py-3">
                        <Link to={`/calls/${call.id}`} className="font-medium hover:text-copper">
                          {call.caller_name || "Unknown caller"}
                        </Link>
                        <div className="text-xs text-muted-foreground">{formatWhen(call.started_at)}</div>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{call.issue || call.summary || "—"}</td>
                      <td className="px-4 py-3">
                        <Badge tone={call.outcome || "open"}>{call.outcome || "open"}</Badge>
                      </td>
                      <td className="px-4 py-3 tabular-nums">{formatMs(call.avg_latency_ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border border-border bg-card p-4">
            <h2 className="font-display text-2xl">On the board</h2>
            <ul className="mt-3 space-y-3">
              {data.upcoming.length === 0 && (
                <li className="text-sm text-muted-foreground">No upcoming visits. The calendar opens up after a booking.</li>
              )}
              {data.upcoming.map((job) => (
                <li key={job.id} className="border-t border-border pt-3 first:border-0 first:pt-0">
                  <div className="text-sm font-medium">{formatWhen(job.start)}</div>
                  <div className="text-sm">{job.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {job.issue} · {job.address}
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-lg bg-[#14241c] p-4 text-[#f4efe6]">
            <div className="text-xs uppercase tracking-[0.16em] text-[#e7a27a]">Why shops buy this</div>
            <p className="mt-2 font-display text-2xl leading-tight">A missed evening call is a job for the next company in the search results.</p>
            <p className="mt-3 text-sm leading-6 text-[#d5ddd6]">
              This sample answered {data.total_calls} calls. {escalated} went to a human. {booked} landed on the calendar
              with a confirmation text logged for the CRM.
            </p>
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card p-4">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="font-display text-2xl">CRM handoff</h2>
          <Link to="/leads" className="text-sm text-copper">
            Webhook log
          </Link>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          Each booking, escalation, and qualified lead is posted as JSON. With no URL configured, delivery is logged
          locally so n8n or GoHighLevel can be pointed at it later.
        </p>
        <ul className="mt-3 grid gap-2 md:grid-cols-2">
          {data.webhooks.slice(0, 4).map((hook) => {
            const payload = hook.payload as { event?: string; contact?: { name?: string }; delivery?: { status?: string } };
            return (
              <li key={hook.id} className="rounded-md border border-border px-3 py-2 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{payload.event}</span>
                  <Badge tone={payload.delivery?.status === "mock" ? "open" : "booked"}>{payload.delivery?.status || hook.status || "logged"}</Badge>
                </div>
                <div className="text-xs text-muted-foreground">
                  {payload.contact?.name || "No contact yet"} · {formatPhone((payload.contact as { phone?: string } | undefined)?.phone)}
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
