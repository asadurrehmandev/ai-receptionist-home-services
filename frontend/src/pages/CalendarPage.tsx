import { useEffect, useMemo, useState } from "react";

import { Empty, ErrorState, Loading } from "@/components/States";
import { Badge } from "@/components/ui/badge";
import { api, type Booking } from "@/lib/api";
import { dayKey, formatPhone, formatWhen } from "@/lib/format";

function chicagoDays(count: number): { key: string; label: string }[] {
  const labelFmt = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Chicago",
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const days: { key: string; label: string }[] = [];
  const seen = new Set<string>();
  const start = Date.now();
  for (let hour = 0; days.length < count && hour < 24 * 14; hour += 1) {
    const probe = new Date(start + hour * 60 * 60 * 1000);
    const key = dayKey(probe.toISOString());
    if (seen.has(key)) continue;
    seen.add(key);
    days.push({ key, label: labelFmt.format(probe) });
  }
  return days;
}

export function CalendarPage() {
  const [bookings, setBookings] = useState<Booking[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api
      .bookings()
      .then((payload) => {
        setBookings(payload.bookings);
        setError(null);
      })
      .catch((reason: Error) => setError(reason.message));
  }

  useEffect(() => {
    load();
  }, []);

  const days = useMemo(() => chicagoDays(7), []);
  const grouped = useMemo(() => {
    const map = new Map<string, Booking[]>();
    for (const booking of bookings || []) {
      if (booking.status === "cancelled") continue;
      const key = dayKey(booking.start);
      map.set(key, [...(map.get(key) || []), booking]);
    }
    return map;
  }, [bookings]);

  if (error && !bookings) return <ErrorState message={error} onRetry={load} />;
  if (!bookings) return <Loading label="Checking the truck calendar…" />;

  const active = bookings.filter((booking) => booking.status === "booked");

  return (
    <div className="space-y-5">
      <header>
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-copper">90-minute windows</p>
        <h1 className="mt-1 font-display text-4xl">Booked jobs</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Each window is one truck. A second caller who confirms the same start time is told that window was just taken.
          {active.length === 0 ? " The week is clear." : ` ${active.length} visit${active.length === 1 ? "" : "s"} are held.`}
        </p>
      </header>
      {active.length === 0 ? (
        <Empty title="No jobs held" body="Run the drain-call scenario in the simulator. The slot shows up here and a confirmation text is logged." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {days.map((day) => {
            const items = grouped.get(day.key) || [];
            return (
              <section key={day.key} className="rounded-lg border border-border bg-card p-3">
                <h2 className="text-sm font-medium">{day.label}</h2>
                <div className="mt-3 space-y-2">
                  {items.length === 0 && <p className="text-xs text-muted-foreground">Open</p>}
                  {items.map((job) => (
                    <article key={job.id} className="rounded-md bg-[#f6f1e8] p-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-medium">{formatWhen(job.start, false)}</span>
                        <Badge tone={job.status === "booked" ? "booked" : "open"}>{job.status}</Badge>
                      </div>
                      <div className="mt-1 text-sm">{job.name}</div>
                      <div className="text-xs text-muted-foreground">{job.issue}</div>
                      <div className="text-xs text-muted-foreground">{job.address}</div>
                      <div className="text-xs text-muted-foreground">{formatPhone(job.phone)}</div>
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
