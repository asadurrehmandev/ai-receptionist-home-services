const ZONE = "America/Chicago";

export function formatWhen(iso: string | null | undefined, withWeekday = true): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("en-US", {
    timeZone: ZONE,
    weekday: withWeekday ? "short" : undefined,
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function formatDay(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: ZONE,
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(new Date(iso));
}

export function dayKey(iso: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(iso));
}

export function formatPhone(value: string | null | undefined): string {
  if (!value) return "—";
  const digits = value.replace(/\D/g, "");
  const local = digits.length === 11 && digits.startsWith("1") ? digits.slice(1) : digits;
  if (local.length !== 10) return value;
  return `(${local.slice(0, 3)}) ${local.slice(3, 6)}-${local.slice(6)}`;
}

export function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (value < 10) return `${value.toFixed(1)} ms`;
  return `${Math.round(value)} ms`;
}

export function titleCase(value: string | null | undefined): string {
  if (!value) return "Open";
  return value.replaceAll("_", " ");
}

export const OUTCOME_TONE: Record<string, string> = {
  booked: "bg-[#e5f2ea] text-[#1f6a45]",
  rescheduled: "bg-[#e5f2ea] text-[#1f6a45]",
  escalated: "bg-[#f8e4e1] text-[#9d2c2c]",
  missed: "bg-[#ece7df] text-[#5c564e]",
  spam: "bg-[#f8ecd9] text-[#8a5a12]",
  qualified: "bg-[#f3e6da] text-[#8a4b22]",
  out_of_area: "bg-[#ece7df] text-[#5c564e]",
  cancelled: "bg-[#ece7df] text-[#5c564e]",
  kept: "bg-[#e5f2ea] text-[#1f6a45]",
  open: "bg-white text-[#5c564e] border border-[#e4ddd2]",
};
