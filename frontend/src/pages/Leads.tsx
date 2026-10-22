import { AlertCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { CallerName } from "@/components/CallerName";
import { Empty, ErrorState, Loading } from "@/components/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, type DeskEvent, type Lead } from "@/lib/api";
import { formatPhone, formatWhen } from "@/lib/format";
import { cn } from "@/lib/utils";

export function Leads() {
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [events, setEvents] = useState<DeskEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [replay, setReplay] = useState<string | null>(null);

  function load() {
    Promise.all([api.leads(), api.events()])
      .then(([leadPayload, eventPayload]) => {
        setLeads(leadPayload.leads);
        setEvents(eventPayload.events);
        setError(null);
      })
      .catch((reason: Error) => setError(reason.message));
  }

  useEffect(() => {
    load();
  }, []);

  if (error && !leads) return <ErrorState message={error} onRetry={load} />;
  if (!leads || !events) return <Loading label="Loading leads…" />;

  const texts = events.filter((event) => event.type === "sms");
  const hooks = events.filter((event) => event.type === "webhook");
  const activeHook = hooks.find((event) => event.id === selected) || hooks[0];

  return (
    <div className="space-y-4">
      <p className="max-w-2xl text-sm text-muted-foreground">
        Bookings and escalations post JSON to a CRM webhook. With no URL configured, delivery is logged here and marked Mock.
      </p>
      <Tabs defaultValue="leads">
        <TabsList>
          <TabsTrigger value="leads">Leads</TabsTrigger>
          <TabsTrigger value="texts">Texts</TabsTrigger>
          <TabsTrigger value="hooks">Webhooks</TabsTrigger>
        </TabsList>
        <TabsContent value="leads">
          {leads.some((lead) => lead.status === "missed_transfer") && (
            <div className="mb-3 flex gap-2 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger" role="status">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              <p>A transfer was missed. These callers are waiting on a callback from the office.</p>
            </div>
          )}
          {leads.length === 0 ? (
            <Empty title="No leads yet" body="A booked job or an escalation creates one." />
          ) : (
            <div className="overflow-hidden rounded-lg border border-border bg-card">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="bg-surface text-xs font-medium text-muted-foreground">
                    <tr className="h-9 border-b border-border">
                      <th className="sticky left-0 bg-surface px-3 font-medium">Contact</th>
                      <th className="px-3 font-medium">Issue</th>
                      <th className="px-3 font-medium">Status</th>
                      <th className="px-3 font-medium">When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map((lead) => (
                      <tr key={lead.id} className="h-10 border-b border-border last:border-0">
                        <td className="sticky left-0 bg-card px-3">
                          <CallerName name={lead.name} phone={lead.phone} />
                          {lead.name && lead.phone ? (
                            <div className="font-mono text-xs tabular-nums text-subtle">{formatPhone(lead.phone)}</div>
                          ) : null}
                        </td>
                        <td className="px-3 text-muted-foreground">{lead.issue || "–"}</td>
                        <td className="px-3">
                          <Badge tone={lead.status || "open"}>{lead.status || "open"}</Badge>
                        </td>
                        <td className="whitespace-nowrap px-3 tabular-nums text-subtle">{formatWhen(lead.created_at, false)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </TabsContent>
        <TabsContent value="texts">
          {texts.length === 0 ? (
            <Empty title="No texts logged" body="A booking keeps the message we would send. Nothing is texted until Twilio accepts it." />
          ) : (
            <ul className="divide-y divide-border rounded-lg border border-border bg-card">
              {texts.map((event) => {
                const payload = event.payload as { to?: string; body?: string; delivery?: string };
                const sent = payload.delivery === "sent";
                return (
                  <li key={event.id} className="px-3 py-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs tabular-nums text-subtle">{formatPhone(payload.to)}</span>
                      <Badge tone={sent ? "booked" : "mock"}>{sent ? "Sent" : "Mock"}</Badge>
                    </div>
                    <p className="mt-1 text-sm">{payload.body}</p>
                  </li>
                );
              })}
            </ul>
          )}
        </TabsContent>
        <TabsContent value="hooks">
          {hooks.length === 0 ? (
            <Empty title="No webhook events" body="Book a job or escalate a call to generate a payload." />
          ) : (
            <div className="grid gap-3 lg:grid-cols-[280px_minmax(0,1fr)]">
              <ul className="overflow-hidden rounded-lg border border-border bg-card">
                {hooks.map((event) => {
                  const payload = event.payload as { event?: string; contact?: { name?: string; phone?: string }; delivery?: { status?: string } };
                  const mock = (payload.delivery?.status || event.status) === "mock";
                  return (
                    <li key={event.id} className="border-b border-border last:border-0">
                      <button
                        type="button"
                        onClick={() => setSelected(event.id || null)}
                        className={cn(
                          "w-full px-3 py-2 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
                          activeHook?.id === event.id && "bg-primary-soft shadow-[inset_2px_0_0_hsl(var(--primary))]",
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-medium">{payload.event}</span>
                          {mock && <Badge tone="mock">Mock</Badge>}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          <CallerName name={payload.contact?.name} phone={payload.contact?.phone} />
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
              {activeHook && (
                <div className="rounded-lg border border-border bg-card p-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h3 className="text-sm font-medium">Payload</h3>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        if (!activeHook.id) return;
                        api
                          .replay(activeHook.id)
                          .then((result) => setReplay(result.status))
                          .catch((reason: Error) => setReplay(reason.message));
                      }}
                    >
                      Replay delivery
                    </Button>
                  </div>
                  {replay && <p className="mb-2 text-xs text-muted-foreground">Last replay: {replay}</p>}
                  <pre className="overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs leading-5">{JSON.stringify(activeHook.payload, null, 2)}</pre>
                </div>
              )}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
