import { AlertCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { CallerName } from "@/components/CallerName";
import { CallsTable } from "@/components/CallsTable";
import { Empty, ErrorState, Loading } from "@/components/States";
import { Button } from "@/components/ui/button";
import { api, type Overview } from "@/lib/api";
import { dayKey, formatClock, formatPhone } from "@/lib/format";

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

  const today = dayKey(new Date().toISOString());
  const todayJobs = data.upcoming.filter((job) => dayKey(job.start) === today);
  const schedule = todayJobs.length > 0 ? todayJobs : data.upcoming.slice(0, 6);
  const scheduleLabel = todayJobs.length > 0 ? "Today" : "Upcoming";
  const missedTransfers = (data.leads || []).filter((lead) => lead.status === "missed_transfer");
  const stats = [
    { label: "Calls", value: data.total_calls },
    { label: "Booked", value: data.counts.booked || 0 },
    { label: "Escalated", value: data.counts.escalated || 0 },
    { label: "Missed", value: data.counts.missed || 0 },
  ];
  const hasCalls = data.recent_calls.length > 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
        {stats.map((item) => (
          <div key={item.label}>
            <div className="text-xs font-medium text-muted-foreground">{item.label}</div>
            <div className="text-xl font-semibold tabular-nums">{item.value}</div>
          </div>
        ))}
        {hasCalls && (
          <Button asChild className="ml-auto">
            <Link to="/simulator">Open simulator</Link>
          </Button>
        )}
      </div>

      {missedTransfers.length > 0 && (
        <div className="flex gap-2 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger" role="status">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <div>
            <p className="font-medium">Missed transfer. The office still owes a callback.</p>
            <ul className="mt-1 space-y-0.5">
              {missedTransfers.map((lead) => (
                <li key={lead.id}>
                  <CallerName name={lead.name} phone={lead.phone} />
                  {lead.phone ? <span className="text-foreground"> {formatPhone(lead.phone)}</span> : null}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(260px,0.7fr)]">
        <section aria-label="Recent calls">
          <div className="mb-2 flex items-baseline justify-between">
            <h2 className="text-md font-semibold">Recent calls</h2>
            <Link to="/calls" className="text-sm text-primary-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              All calls
            </Link>
          </div>
          {hasCalls ? (
            <CallsTable calls={data.recent_calls} />
          ) : (
            <Empty
              title="No calls yet"
              body="Try the simulator to place a test call. Booked jobs show up in this table."
              action={
                <Button asChild>
                  <Link to="/simulator">Open simulator</Link>
                </Button>
              }
            />
          )}
        </section>

        <section aria-label={scheduleLabel} className="rounded-lg border border-border bg-card">
          <div className="flex items-baseline justify-between border-b border-border px-3 py-2">
            <h2 className="text-md font-semibold">{scheduleLabel}</h2>
            <Link to="/calendar" className="text-sm text-primary-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              Calendar
            </Link>
          </div>
          {schedule.length === 0 ? (
            <p className="px-3 py-4 text-sm text-muted-foreground">No visits today.</p>
          ) : (
            <ul>
              {schedule.map((job) => (
                <li key={job.id} className="border-b border-border last:border-0">
                  <Link
                    to={job.call_id ? `/calls/${job.call_id}` : "/calendar"}
                    className="flex items-start gap-3 px-3 py-2 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
                  >
                    <span className="w-16 shrink-0 pt-0.5 font-mono text-xs tabular-nums text-subtle">{formatClock(job.start)}</span>
                    <span className="min-w-0 border-l-[3px] border-primary pl-2">
                      <span className="block truncate text-xs font-semibold">{job.name || formatPhone(job.phone)}</span>
                      <span className="block truncate text-xs text-muted-foreground">{job.issue || "–"}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
