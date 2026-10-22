import { useEffect, useState } from "react";

import { ErrorState, Loading } from "@/components/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { api, type PublicConfig } from "@/lib/api";

export function Setup() {
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resetNote, setResetNote] = useState<string | null>(null);

  function load() {
    api
      .config()
      .then((payload) => {
        setConfig(payload);
        setError(null);
      })
      .catch((reason: Error) => setError(reason.message));
  }

  useEffect(() => {
    load();
  }, []);

  if (error && !config) return <ErrorState message={error} onRetry={load} />;
  if (!config) return <Loading label="Loading shop setup…" />;

  const checks = [
    ["Environment model key", config.runtime.llm],
    ["Deepgram speech-to-text", config.runtime.stt],
    ["ElevenLabs voice", config.runtime.tts],
    ["Twilio signature check", config.runtime.twilio_signature],
    ["Media stream ready", config.runtime.media_stream_ready],
  ] as const;

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-start justify-between gap-3">
        <p className="max-w-2xl text-sm text-muted-foreground">
          {config.business.agent_name} covers {config.business.trade.toLowerCase()} in {config.business.city}.{" "}
          {config.runtime.reply_mode === "live"
            ? `Live model from the environment (${config.runtime.llm_provider}).`
            : "Demo mode: replies come from the shop rules, not from Claude or GPT."}{" "}
          Calls and leads are kept 30 days, then purged.
        </p>
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline">Reset demo data</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Reset the sample desk?</DialogTitle>
              <DialogDescription>
                This clears calls, bookings, leads, and texts, then replays the sample scenarios. Dana Cho’s visit is
                planted again so the reschedule demo has someone to move.
              </DialogDescription>
            </DialogHeader>
            <Button
              className="mt-4"
              onClick={() => {
                api
                  .reset()
                  .then((result) => setResetNote(`Restored ${result.calls} sample calls.`))
                  .catch((reason: Error) => setResetNote(reason.message));
              }}
            >
              Reset and reseed
            </Button>
            {resetNote && <p className="mt-3 text-sm text-muted-foreground">{resetNote}</p>}
          </DialogContent>
        </Dialog>
      </div>

      <section className="grid gap-3 border-t border-border py-5 lg:grid-cols-[180px_minmax(0,1fr)]">
        <h2 className="text-sm font-semibold">Business hours</h2>
        <ul className="text-sm">
          {Object.entries(config.hours).map(([day, hours]) => (
            <li key={day} className="flex justify-between border-b border-border py-1.5 capitalize last:border-0">
              <span>{day}</span>
              <span className="tabular-nums text-muted-foreground">{hours ? `${hours.open}–${hours.close}` : "Closed"}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-3 border-t border-border py-5 lg:grid-cols-[180px_minmax(0,1fr)]">
        <h2 className="text-sm font-semibold">Service area</h2>
        <div>
          <p className="text-sm">{config.service_area.cities.join(", ")}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {config.service_area.zips.map((zip) => (
              <span key={zip} className="rounded-sm bg-muted px-1.5 py-0.5 font-mono text-xs tabular-nums">
                {zip}
              </span>
            ))}
          </div>
          <h3 className="mt-4 text-sm font-semibold">Escalation</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {config.escalation.on_call_name}
            <span className="ml-2 font-mono tabular-nums">{config.escalation.on_call_phone}</span>
          </p>
          <h3 className="mt-4 text-sm font-semibold">Services</h3>
          <ul className="mt-1 text-sm text-muted-foreground">
            {config.services.map((service) => (
              <li key={service}>{service}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="grid gap-3 border-t border-border py-5 lg:grid-cols-[180px_minmax(0,1fr)]">
        <h2 className="text-sm font-semibold">Pricing Riley can say</h2>
        <div>
          <p className="text-sm text-muted-foreground">
            Diagnostic visit ${config.pricing.diagnostic_fee_usd}, waived when the repair is approved. After-hours fee $
            {config.pricing.after_hours_fee_usd}. Emergency dispatch ${config.pricing.emergency_dispatch_usd}.
          </p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs font-medium text-muted-foreground">
                <tr className="h-9 border-b border-border">
                  <th className="font-medium">Work</th>
                  <th className="text-right font-medium">Typical range</th>
                </tr>
              </thead>
              <tbody>
                {config.pricing.rules.map((rule) => (
                  <tr key={rule.id} className="border-b border-border last:border-0">
                    <td className="py-2">{rule.label}</td>
                    <td className="py-2 text-right tabular-nums text-muted-foreground">
                      ${rule.low_usd.toLocaleString()}–${rule.high_usd.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="grid gap-3 border-t border-border py-5 lg:grid-cols-[180px_minmax(0,1fr)]">
        <h2 className="text-sm font-semibold">Keys</h2>
        <div>
          <p className="text-sm text-muted-foreground">
            The demo runs with none of these set. CRM target: {config.crm.provider_label}
            {config.crm.webhook_url ? `. ${config.crm.webhook_url}` : ". Webhook URL empty, so payloads stay in the log."}
          </p>
          <ul className="mt-3 divide-y divide-border rounded-lg border border-border">
            {checks.map(([label, on]) => (
              <li key={label} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                <span>{label}</span>
                <Badge tone={on ? "booked" : "open"}>{on ? "Connected" : "Not set"}</Badge>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
