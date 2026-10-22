import { formatPhone } from "@/lib/format";

export function CallerName({ name, phone }: { name?: string | null; phone?: string | null }) {
  if (name) return <span className="font-medium text-foreground">{name}</span>;
  if (phone) return <span className="font-mono text-sm tabular-nums">{formatPhone(phone)}</span>;
  return <span className="text-subtle">–</span>;
}

export function LiveMark() {
  return <span className="text-xs font-medium text-muted-foreground">In call</span>;
}
