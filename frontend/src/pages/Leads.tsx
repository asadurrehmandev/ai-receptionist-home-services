import { useEffect, useState } from "react";

import { Empty, ErrorState, Loading } from "@/components/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, type DeskEvent, type Lead } from "@/lib/api";
import { formatPhone, formatWhen } from "@/lib/format";

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
  if (!leads || !events) return <Loading label="Loading the CRM tray…" />;

  const texts = events.filter((event) => event.type === "sms");
  const hooks = events.filter((event) => event.type === "webhook");
  const activeHook = hooks.find((event) => event.id === selected) || hooks[0];

  return (
    <div className="space-y-5">
      <header>
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-copper">GoHighLevel · HubSpot · Zapier</p>
        <h1 className="mt-1 font-display text-4xl">Leads and handoff</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Qualified callers become leads. Bookings, cancellations, and emergency transfers each emit a generic CRM
          webhook (GoHighLevel, HubSpot, or Zapier-compatible). Texts are logged, not sent, until a messaging provider
          is attached.
        </p>
      </header>
      <Tabs defaultValue="leads">
        <TabsList>
          <TabsTrigger value="leads">Leads</TabsTrigger>
          <TabsTrigger value="texts">Confirmation texts</TabsTrigger>
          <TabsTrigger value="hooks">Webhooks</TabsTrigger>
        </TabsList>
        <TabsContent value="leads">
          {leads.some((lead) => lead.status === "missed_transfer") && (
            <div className="border-b border-[#e7c7c2] bg-[#f8e4e1] px-4 py-3 text-sm text-[#9d2c2c]">
              A transfer was missed. These callers are waiting on a callback from the office.
            </div>
          )}
          {leads.length === 0 ? (
            <Empty title="No leads yet" body="A booked job or an escalation creates one." />
          ) : (
            <div className="overflow-hidden rounded-lg border border-border bg-card">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                  <tr className="border-b border-border">
                    <th className="px-4 py-3 font-medium">Contact</th>
                    <th className="px-4 py-3 font-medium">Issue</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">When</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.map((lead) => (
                    <tr key={lead.id} className="border-b border-border last:border-0">
                      <td className="px-4 py-3">
                        <div className="font-medium">{lead.name || "Unnamed"}</div>
                        <div className="text-xs text-muted-foreground">{formatPhone(lead.phone)}</div>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{lead.issue || "—"}</td>
                      <td className="px-4 py-3">
                        <Badge tone={lead.status || "open"}>{lead.status || "open"}</Badge>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{formatWhen(lead.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>
        <TabsContent value="texts">
          {texts.length === 0 ? (
            <Empty title="No texts logged" body="A booking keeps the message we would send. Twilio has to accept it before anyone is texted." />
          ) : (
            <ul className="space-y-2">
              {texts.map((event) => {
                const payload = event.payload as { to?: string; body?: string; delivery?: string };
                const note = payload.delivery === "sent" ? "sent by Twilio" : "logged, not sent";
                return (
                  <li key={event.id} className="rounded-lg border border-border bg-card p-3">
                    <div className="text-xs text-muted-foreground">To {formatPhone(payload.to)} · {note}</div>
                    <p className="mt-1 text-sm leading-6">{payload.body}</p>
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
              <ul className="space-y-2">
                {hooks.map((event) => {
                  const payload = event.payload as { event?: string; contact?: { name?: string }; delivery?: { status?: string } };
                  return (
                    <li key={event.id}>
                      <button
                        type="button"
                        onClick={() => setSelected(event.id || null)}
                        className={`w-full rounded-md border px-3 py-2 text-left text-sm ${
                          activeHook?.id === event.id ? "border-copper bg-[#f8f1ea]" : "border-border bg-card"
                        }`}
                      >
                        <div className="font-medium">{payload.event}</div>
                        <div className="text-xs text-muted-foreground">
                          {payload.contact?.name || "No name"} · {payload.delivery?.status || event.status}
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
              {activeHook && (
                <div className="rounded-lg border border-border bg-[#1c1915] p-4 text-[#f4efe6]">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <span className="text-xs uppercase tracking-[0.14em] text-[#e7a27a]">Payload</span>
                    <Button
                      size="sm"
                      variant="secondary"
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
                  {replay && <p className="mb-2 text-xs text-[#e7a27a]">Last replay: {replay}</p>}
                  <pre className="overflow-x-auto text-xs leading-5">{JSON.stringify(activeHook.payload, null, 2)}</pre>
                </div>
              )}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
