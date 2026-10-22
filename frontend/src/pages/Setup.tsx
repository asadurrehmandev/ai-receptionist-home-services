import { useEffect, useState } from "react";

import { ErrorState, Loading } from "@/components/States";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
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
  if (!config) return <Loading label="Reading the shop profile…" />;

  const checks = [
    ["OpenAI phrasing", config.runtime.llm],
    ["Deepgram speech-to-text", config.runtime.stt],
    ["ElevenLabs voice", config.runtime.tts],
    ["Twilio signature check", config.runtime.twilio_signature],
    ["Media stream ready", config.runtime.media_stream_ready],
  ] as const;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-copper">config/business.yaml</p>
          <h1 className="mt-1 font-display text-4xl">{config.business.name}</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            {config.business.agent_name} covers {config.business.trade.toLowerCase()} in {config.business.city}. Swap the
            YAML to retarget the same desk at another plumber, HVAC shop, or tow company. Brain right now:{" "}
            {config.runtime.brain}.
          </p>
        </div>
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
      </header>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-lg border border-border bg-card p-5">
          <h2 className="font-display text-2xl">Hours</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {Object.entries(config.hours).map(([day, hours]) => (
              <li key={day} className="flex justify-between border-b border-border py-1 capitalize last:border-0">
                <span>{day}</span>
                <span className="text-muted-foreground">{hours ? `${hours.open}–${hours.close}` : "Closed"}</span>
              </li>
            ))}
          </ul>
        </article>
        <article className="rounded-lg border border-border bg-card p-5">
          <h2 className="font-display text-2xl">Service area</h2>
          <p className="mt-2 text-sm text-muted-foreground">{config.service_area.cities.join(", ")}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {config.service_area.zips.map((zip) => (
              <span key={zip} className="rounded-full bg-muted px-2 py-0.5 text-xs">
                {zip}
              </span>
            ))}
          </div>
          <Separator className="my-4" />
          <h3 className="text-sm font-medium">Escalation</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {config.escalation.on_call_name} · {config.escalation.on_call_phone}
          </p>
          <p className="mt-3 text-sm font-medium">Services</p>
          <p className="mt-1 text-sm text-muted-foreground">{config.services.join(" · ")}</p>
        </article>
      </section>

      <section className="rounded-lg border border-border bg-card p-5">
        <h2 className="font-display text-2xl">Pricing Riley is allowed to say</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Diagnostic visit ${config.pricing.diagnostic_fee_usd}, waived when the repair is approved. After-hours fee $
          {config.pricing.after_hours_fee_usd}. Emergency dispatch ${config.pricing.emergency_dispatch_usd}.
        </p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2 font-medium">Work</th>
                <th className="py-2 font-medium">Typical range</th>
              </tr>
            </thead>
            <tbody>
              {config.pricing.rules.map((rule) => (
                <tr key={rule.id} className="border-t border-border">
                  <td className="py-2">{rule.label}</td>
                  <td className="py-2 text-muted-foreground">
                    ${rule.low_usd.toLocaleString()}–${rule.high_usd.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card p-5">
        <h2 className="font-display text-2xl">Keys</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          The demo runs with none of these. Add them in the environment when the same webhook should answer a real
          number. CRM target: {config.crm.provider_label}
          {config.crm.webhook_url ? ` · ${config.crm.webhook_url}` : " · webhook URL empty, payloads stay in the log"}.
        </p>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {checks.map(([label, on]) => (
            <li key={label} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm">
              <span>{label}</span>
              <span className={on ? "text-pine" : "text-muted-foreground"}>{on ? "Connected" : "Not set"}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
