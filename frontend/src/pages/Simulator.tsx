import { Mic, Send } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { ErrorState } from "@/components/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api, type DemoTurn } from "@/lib/api";
import { formatMs, formatPhone } from "@/lib/format";
import { SCRIPTS } from "@/lib/scripts";

type Bubble = { role: "agent" | "caller"; text: string; latency_ms?: number | null };

const PHASE_LABEL: Record<string, string> = {
  discover: "Listening",
  collect_issue: "Getting the problem",
  collect_name: "Asking for a name",
  collect_phone: "Asking for a number",
  collect_address: "Asking for the address",
  collect_zip: "Checking the service area",
  quote_decision: "Giving a price",
  offer: "Offering times",
  confirm: "Confirming the visit",
  existing_lookup: "Looking up the visit",
  existing_action: "Existing appointment",
  closed: "Call ended",
};

function speak(text: string, onStart: () => void, onEnd: () => void) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.02;
  utterance.onstart = onStart;
  utterance.onend = onEnd;
  utterance.onerror = onEnd;
  window.speechSynthesis.speak(utterance);
}

export function Simulator() {
  const [callId, setCallId] = useState<string | null>(null);
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [draft, setDraft] = useState("");
  const [turn, setTurn] = useState<DemoTurn | null>(null);
  const [events, setEvents] = useState<DemoTurn["events"]>([]);
  const [scriptId, setScriptId] = useState(SCRIPTS[0].id);
  const [cursor, setCursor] = useState(0);
  const [busy, setBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [speechNote, setSpeechNote] = useState<string | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const script = SCRIPTS.find((item) => item.id === scriptId) || SCRIPTS[0];

  async function begin() {
    const started = await api.startCall();
    setCallId(started.id);
    setBubbles([{ role: "agent", text: started.say, latency_ms: started.latency_ms }]);
    setTurn(started);
    setEvents([]);
    setCursor(0);
    setError(null);
    speak(started.say, () => setSpeaking(true), () => setSpeaking(false));
    return started;
  }

  useEffect(() => {
    begin().catch((reason: Error) => setError(reason.message));
    return () => window.speechSynthesis?.cancel();
  }, []);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [bubbles, speaking]);

  async function send(text: string, activeId = callId) {
    const trimmed = text.trim();
    if (!activeId || !trimmed) return null;
    setBubbles((current) => [...current, { role: "caller", text: trimmed }]);
    const result = await api.sendTurn(activeId, trimmed);
    setBubbles((current) => [...current, { role: "agent", text: result.say, latency_ms: result.latency_ms }]);
    setTurn(result);
    setEvents((current) => [...current, ...result.events]);
    speak(result.say, () => setSpeaking(true), () => setSpeaking(false));
    return result;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (busy || !draft.trim()) return;
    setBusy(true);
    try {
      await send(draft);
      setDraft("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The turn failed.");
    } finally {
      setBusy(false);
    }
  }

  async function playThrough() {
    setBusy(true);
    setSpeechNote(null);
    try {
      const started = await begin();
      let latest = started;
      for (const line of script.turns) {
        await wait(650);
        const result = await send(line, started.id);
        if (result) latest = result;
        if (result?.outcome) break;
        await wait(450);
      }
      setCursor(script.turns.length);
      setTurn(latest);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Playback failed.");
    } finally {
      setBusy(false);
    }
  }

  async function step() {
    if (busy || cursor >= script.turns.length) return;
    setBusy(true);
    try {
      await send(script.turns[cursor]);
      setCursor((value) => value + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The turn failed.");
    } finally {
      setBusy(false);
    }
  }

  function listen() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setSpeechNote("This browser has no speech recognition. Type what the caller would say.");
      return;
    }
    const recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.onresult = (speechEvent) => {
      setDraft(speechEvent.results[0][0].transcript);
      setSpeechNote(null);
    };
    recognition.onerror = () => setSpeechNote("The microphone didn't start. Type the caller's line instead.");
    recognition.start();
    setSpeechNote("Listening… speak as the caller, then press send.");
  }

  if (error && bubbles.length === 0) return <ErrorState message={error} onRetry={() => begin()} />;

  const slots = turn?.slots;
  const sms = [...events].reverse().find((event) => event.type === "sms");
  const transfer = [...events].reverse().find((event) => event.type === "transfer");
  const smsBody = (sms?.payload as { body?: string } | undefined)?.body;
  const transferTo = transfer?.payload as { to_name?: string; to_phone?: string; reason?: string } | undefined;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-copper">No Twilio account required</p>
          <h1 className="mt-1 font-display text-4xl">Call simulator</h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            Talk with the browser’s microphone or type as the homeowner. Riley answers with the same brain the Twilio
            webhook uses. Without an Anthropic key, that brain is the rule receptionist. With a key, Claude calls the
            calendar tools and cannot invent a time or a price.
          </p>
        </div>
      </header>

      <div className="grid items-start gap-4 xl:grid-cols-[240px_minmax(320px,420px)_minmax(260px,1fr)]">
        <aside className="space-y-2">
          <h2 className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Scenarios</h2>
          {SCRIPTS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                setScriptId(item.id);
                setCursor(0);
              }}
              className={`block w-full rounded-md border px-3 py-2 text-left ${
                item.id === scriptId ? "border-copper bg-[#f8f1ea]" : "border-border bg-card"
              }`}
            >
              <div className="text-sm font-medium">{item.label}</div>
              <div className="text-xs text-muted-foreground">{item.detail}</div>
            </button>
          ))}
          <div className="flex gap-2 pt-2">
            <Button type="button" size="sm" variant="outline" onClick={step} disabled={busy || !callId || cursor >= script.turns.length}>
              Step
            </Button>
            <Button type="button" size="sm" onClick={playThrough} disabled={busy}>
              Play through
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Next line: {cursor < script.turns.length ? script.turns[cursor] : "Scenario finished."}
          </p>
        </aside>

        <div className="phone-bezel">
          <div className="phone-screen">
            <div className="flex items-center justify-between border-b border-[#e6dfd4] px-4 py-3">
              <div>
                <div className="text-[11px] uppercase tracking-[0.16em] text-copper">Live call</div>
                <div className="text-sm font-medium">Northline Plumbing</div>
              </div>
              <div className="text-right">
                <div className="text-xs text-muted-foreground">{PHASE_LABEL[turn?.phase || "discover"] || turn?.phase}</div>
                {speaking ? (
                  <div className="wave ml-auto mt-1" aria-hidden>
                    <span /><span /><span /><span />
                  </div>
                ) : (
                  <div className="text-[11px] text-muted-foreground">{speaking ? "" : "Speaker idle"}</div>
                )}
              </div>
            </div>
            {turn?.outcome === "booked" && (
              <div className="bg-[#e5f2ea] px-4 py-2 text-sm text-[#1f6a45]">Booked. Confirmation text is in the log.</div>
            )}
            {turn?.outcome === "escalated" && (
              <div className="bg-[#f8e4e1] px-4 py-2 text-sm text-[#9d2c2c]">
                Transferred to {transferTo?.to_name || "on-call"}.
              </div>
            )}
            {turn?.outcome === "spam" && (
              <div className="bg-[#f8ecd9] px-4 py-2 text-sm text-[#8a5a12]">Closed as a sales call.</div>
            )}
            <div ref={scroller} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
              {bubbles.map((bubble, index) => (
                <div key={`${bubble.role}-${index}`} className={bubble.role === "caller" ? "ml-8" : "mr-8"}>
                  <div className="text-[10px] uppercase tracking-wide text-[#8a8175]">
                    {bubble.role === "caller" ? "Caller" : "Riley"}
                    {bubble.latency_ms != null ? ` · ${formatMs(bubble.latency_ms)}` : ""}
                  </div>
                  <p
                    className={`mt-1 rounded-2xl px-3 py-2 text-sm leading-6 ${
                      bubble.role === "caller" ? "bg-[#1c1915] text-[#f4efe6]" : "bg-white"
                    }`}
                  >
                    {bubble.text}
                  </p>
                </div>
              ))}
            </div>
            <form onSubmit={onSubmit} className="flex gap-2 border-t border-[#e6dfd4] p-3">
              <Input
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="What the caller says"
                aria-label="Caller line"
                disabled={busy}
              />
              <Button type="button" size="icon" variant="outline" onClick={listen} aria-label="Speak as the caller">
                <Mic className="h-4 w-4" />
              </Button>
              <Button type="submit" size="icon" disabled={busy || !draft.trim()} aria-label="Send caller line">
                <Send className="h-4 w-4" />
              </Button>
            </form>
            {speechNote && <p className="px-3 pb-3 text-xs text-muted-foreground">{speechNote}</p>}
          </div>
        </div>

        <aside className="space-y-3">
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-2xl">Ticket</h2>
              {turn?.outcome && <Badge tone={turn.outcome}>{turn.outcome}</Badge>}
            </div>
            <dl className="mt-3 space-y-2 text-sm">
              <Row label="Intent" value={turn?.intent?.replaceAll("_", " ") || "—"} />
              <Row label="Issue" value={slots?.issue || "—"} />
              <Row label="Name" value={slots?.name || "—"} />
              <Row label="Phone" value={formatPhone(slots?.phone)} />
              <Row label="Address" value={slots?.address || "—"} />
            </dl>
            {turn && turn.offered.length > 0 && (
              <div className="mt-3 border-t border-border pt-3">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">Offered</div>
                <ul className="mt-1 space-y-1 text-sm">
                  {turn.offered.map((slot) => (
                    <li key={slot}>{slot}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          {turn?.outcome === "booked" && smsBody && (
            <div className="rounded-lg border border-[#cfe3d6] bg-[#f3faf5] p-4">
              <div className="text-xs uppercase tracking-[0.14em] text-[#1f6a45]">Confirmation text</div>
              <p className="mt-2 text-sm leading-6">{smsBody}</p>
            </div>
          )}
          {turn?.outcome === "escalated" && (
            <div className="rounded-lg border border-[#efc8c4] bg-[#fdf6f5] p-4">
              <div className="text-xs uppercase tracking-[0.14em] text-[#9d2c2c]">Transfer event</div>
              <p className="mt-2 font-display text-2xl">{transferTo?.to_name}</p>
              <p className="text-sm">{formatPhone(transferTo?.to_phone)}</p>
              <p className="mt-1 text-sm text-muted-foreground">{transferTo?.reason}</p>
            </div>
          )}
          <ScrollArea className="h-48 rounded-lg border border-border bg-card p-3">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">Events this call</div>
            {events.length === 0 && <p className="mt-2 text-sm text-muted-foreground">Nothing filed yet.</p>}
            <ul className="mt-2 space-y-2">
              {events.map((event, index) => (
                <li key={`${event.type}-${index}`} className="text-sm">
                  <span className="font-medium capitalize">{event.type}</span>
                </li>
              ))}
            </ul>
          </ScrollArea>
          {error && <p className="text-sm text-clay">{error}</p>}
        </aside>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right">{value}</dd>
    </div>
  );
}

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
