import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ErrorState, Loading } from "@/components/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { api, type Booking } from "@/lib/api";
import { chicagoClock, dayKey, formatClock, formatPhone } from "@/lib/format";
import { cn } from "@/lib/utils";

const START_HOUR = 7;
const END_HOUR = 19;
const ROW_PX = 24;
const PX_PER_MIN = ROW_PX / 30;
const GRID_HEIGHT = (END_HOUR - START_HOUR) * 2 * ROW_PX;
const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function instantForKey(key: string): Date {
  const [year, month, day] = key.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day, 18));
}

function addDays(key: string, delta: number): string {
  const date = instantForKey(key);
  date.setUTCDate(date.getUTCDate() + delta);
  return dayKey(date.toISOString());
}

function todayKey(): string {
  return dayKey(new Date().toISOString());
}

function weekStart(key: string): string {
  const weekday = new Intl.DateTimeFormat("en-US", { timeZone: "America/Chicago", weekday: "short" }).format(instantForKey(key));
  const index = WEEKDAYS.indexOf(weekday);
  return addDays(key, index === -1 ? 0 : -index);
}

function dayParts(key: string) {
  const date = instantForKey(key);
  return {
    weekday: new Intl.DateTimeFormat("en-US", { timeZone: "America/Chicago", weekday: "short" }).format(date),
    dayNum: new Intl.DateTimeFormat("en-US", { timeZone: "America/Chicago", day: "numeric" }).format(date),
    label: new Intl.DateTimeFormat("en-US", { timeZone: "America/Chicago", month: "short", day: "numeric" }).format(date),
  };
}

function minutesFromOpen(iso: string): number {
  const clock = chicagoClock(iso);
  return (clock.hour - START_HOUR) * 60 + clock.minute;
}

const HOURS = Array.from({ length: (END_HOUR - START_HOUR) * 2 }, (_, index) => {
  const hour = START_HOUR + Math.floor(index / 2);
  const minute = index % 2 === 0 ? 0 : 30;
  const label = minute === 0 ? new Intl.DateTimeFormat("en-US", { hour: "numeric" }).format(new Date(2000, 0, 1, hour, 0)) : "";
  return { label, index };
});

export function CalendarPage() {
  const [bookings, setBookings] = useState<Booking[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"week" | "day">("week");
  const [anchor, setAnchor] = useState(todayKey);
  const [placed, setPlaced] = useState(false);
  const [selected, setSelected] = useState<Booking | null>(null);
  const [now, setNow] = useState(() => Date.now());

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

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 30000);
    return () => window.clearInterval(timer);
  }, []);

  const active = useMemo(() => (bookings || []).filter((booking) => booking.status !== "cancelled"), [bookings]);

  useEffect(() => {
    if (!bookings || placed) return;
    const today = todayKey();
    const start = weekStart(today);
    const week = Array.from({ length: 7 }, (_, index) => addDays(start, index));
    const keys = active.map((booking) => dayKey(booking.start)).sort();
    if (!keys.some((key) => week.includes(key))) {
      const upcoming = keys.find((key) => key >= today) || keys[0];
      if (upcoming) setAnchor(upcoming);
    }
    setPlaced(true);
  }, [bookings, active, placed]);

  const columns = useMemo(() => {
    if (mode === "day") return [anchor];
    const start = weekStart(anchor);
    return Array.from({ length: 7 }, (_, index) => addDays(start, index));
  }, [mode, anchor]);

  if (error && !bookings) return <ErrorState message={error} onRetry={load} />;
  if (!bookings) return <Loading label="Loading the calendar…" />;

  const today = todayKey();
  const rangeLabel = mode === "day" ? dayParts(anchor).label : `${dayParts(columns[0]).label} – ${dayParts(columns[columns.length - 1]).label}`;
  const nowMinutes = minutesFromOpen(new Date(now).toISOString());
  const showNow = columns.includes(today) && nowMinutes >= 0 && nowMinutes <= (END_HOUR - START_HOUR) * 60;
  const outside = active.filter((booking) => {
    const start = minutesFromOpen(booking.start);
    const end = minutesFromOpen(booking.end);
    return end <= 0 || start >= (END_HOUR - START_HOUR) * 60;
  });

  function shift(direction: number) {
    setAnchor((current) => addDays(current, mode === "week" ? direction * 7 : direction));
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1">
          <Button type="button" size="icon" variant="outline" aria-label="Previous" onClick={() => shift(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={() => setAnchor(todayKey())}>
            Today
          </Button>
          <Button type="button" size="icon" variant="outline" aria-label="Next" onClick={() => shift(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        <h2 className="text-md font-semibold tabular-nums">{rangeLabel}</h2>
        <div className="ml-auto flex rounded-md border border-border" role="group" aria-label="Calendar range">
          {(["day", "week"] as const).map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={mode === value}
              onClick={() => setMode(value)}
              className={cn(
                "h-8 px-3 text-sm font-medium capitalize focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                mode === value ? "bg-muted text-foreground" : "text-muted-foreground",
              )}
            >
              {value}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="overflow-x-auto">
          <div className={cn("min-w-[720px]", mode === "day" && "min-w-0")}>
            <div className="flex border-b border-border bg-surface">
              <div className="sticky left-0 z-10 w-14 shrink-0 bg-surface" />
              {columns.map((key) => {
                const parts = dayParts(key);
                return (
                  <div key={key} className={cn("min-w-[120px] flex-1 px-2 py-2", key === today && "bg-muted")}>
                    <div className="text-xs text-subtle">{parts.weekday}</div>
                    <div className="text-md font-semibold tabular-nums">{parts.dayNum}</div>
                  </div>
                );
              })}
            </div>
            <div className="flex" aria-label="Schedule from 7:00 to 19:00">
              <div className="sticky left-0 z-10 w-14 shrink-0 bg-card" style={{ height: GRID_HEIGHT }}>
                {HOURS.map((slot) => (
                  <div key={slot.index} className="h-6 pr-2 text-right text-xs text-subtle">
                    {slot.label}
                  </div>
                ))}
              </div>
              {columns.map((key) => {
                const items = active.filter((booking) => dayKey(booking.start) === key);
                return (
                  <div
                    key={key}
                    className={cn("relative min-w-[120px] flex-1 border-l border-border", key === today && "bg-muted/60")}
                    style={{ height: GRID_HEIGHT }}
                  >
                    {HOURS.map((slot) => (
                      <div key={slot.index} className="h-6 border-b border-border" />
                    ))}
                    {showNow && key === today && (
                      <div className="pointer-events-none absolute inset-x-0 z-20" style={{ top: nowMinutes * PX_PER_MIN }}>
                        <div className="absolute -top-4 left-1 rounded-sm bg-card px-1 text-[10px] font-medium leading-4 text-danger">
                          Now
                        </div>
                        <div className="h-px bg-danger" />
                      </div>
                    )}
                    {items.map((job) => {
                      const start = minutesFromOpen(job.start);
                      const end = minutesFromOpen(job.end);
                      if (end <= 0 || start >= (END_HOUR - START_HOUR) * 60) return null;
                      const top = Math.max(0, start) * PX_PER_MIN;
                      const height = Math.max(ROW_PX, (Math.min((END_HOUR - START_HOUR) * 60, end) - Math.max(0, start)) * PX_PER_MIN);
                      return (
                        <button
                          key={job.id}
                          type="button"
                          onClick={() => setSelected(job)}
                          className="absolute inset-x-1 z-10 overflow-hidden rounded-sm border-l-[3px] border-primary bg-primary-soft px-1.5 py-0.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          style={{ top, height }}
                          aria-label={`${job.name || "Visit"}, ${job.issue || "job"}, ${formatClock(job.start)}`}
                        >
                          <div className="truncate text-xs font-semibold">{job.name || formatPhone(job.phone)}</div>
                          {height >= 40 && <div className="truncate text-xs font-normal text-foreground">{job.issue || "–"}</div>}
                        </button>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {outside.length > 0 && (
        <ul className="text-sm text-muted-foreground">
          {outside.map((job) => (
            <li key={job.id}>
              <button type="button" className="text-primary-text" onClick={() => setSelected(job)}>
                {formatClock(job.start)} {job.name || formatPhone(job.phone)}
              </button>
              <span> is outside 7:00–19:00</span>
            </li>
          ))}
        </ul>
      )}

      <Dialog open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent>
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle>{selected.name || formatPhone(selected.phone)}</DialogTitle>
                <DialogDescription>{selected.issue || "Visit"}</DialogDescription>
              </DialogHeader>
              <dl className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">When</dt>
                  <dd className="tabular-nums">
                    {formatClock(selected.start)}–{formatClock(selected.end)}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Address</dt>
                  <dd className="text-right">{selected.address || "–"}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Phone</dt>
                  <dd className="font-mono tabular-nums">{formatPhone(selected.phone)}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd>
                    <Badge tone={selected.status}>{selected.status}</Badge>
                  </dd>
                </div>
              </dl>
              {selected.call_id && (
                <Link
                  to={`/calls/${selected.call_id}`}
                  className="mt-4 inline-flex text-sm text-primary-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  Open call
                </Link>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
