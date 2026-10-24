import { Check, Mic, Send } from "lucide-react";
import { useEffect, useRef, useState, useSyncExternalStore, type FormEvent } from "react";

import { ErrorState } from "@/components/States";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, type DemoTurn } from "@/lib/api";
import { formatMs, formatPhone } from "@/lib/format";
import { SCRIPTS } from "@/lib/scripts";
import { getSession, isLive, subscribe } from "@/lib/sessionKey";
import { cn } from "@/lib/utils";

type Bubble = {
  role: "agent" | "caller";
  text: string;
  latency_ms?: number | null;
  thinking?: boolean;
  streaming?: boolean;
};

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

const DANGER = new Set(["gas", "burst"]);

function speak(text: string, muted: () => boolean, onStart: () => void, onEnd: () => void) {
  if (muted() || !window.speechSynthesis) {
    onEnd();
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.02;
  utterance.onstart = onStart;
  utterance.onend = onEnd;
  utterance.onerror = onEnd;
  window.speechSynthesis.speak(utterance);
}

export function Simulator() {
  const session = useSyncExternalStore(subscribe, getSession, getSession);
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
  const [ended, setEnded] = useState(false);
  const [muted, setMuted] = useState(false);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [showTimings, setShowTimings] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const [pinned, setPinned] = useState(true);
  const [shopName, setShopName] = useState("Porter Plumbing & HVAC");
  const scroller = useRef<HTMLDivElement>(null);
  const callIdRef = useRef<string | null>(null);
  const generation = useRef(0);
  const mutedRef = useRef(false);
  const prevFields = useRef<Record<string, string>>({});
  const script = SCRIPTS.find((item) => item.id === scriptId) || SCRIPTS[0];

  useEffect(() => {
    api.health().then((health) => setShopName(health.business)).catch(() => undefined);
  }, []);

  async function typeReply(text: string, latency?: number | null) {
    const token = ++generation.current;
    const thinking = isLive() ? "Asking the live model…" : "Checking the shop rules…";
    setBubbles((current) => [...current, { role: "agent", text: thinking, thinking: true, latency_ms: latency }]);
    await wait(900);
    if (generation.current !== token) return;
    const words = text.split(/(\s+)/);
    let shown = "";
    for (const word of words) {
      if (generation.current !== token) return;
      shown += word;
      const partial = shown;
      setBubbles((current) => {
        const next = current.slice();
        const last = next[next.length - 1];
        if (last?.role === "agent") {
          next[next.length - 1] = { role: "agent", text: partial, streaming: true, latency_ms: latency };
        }
        return next;
      });
      await wait(word.trim() ? 70 : 0);
    }
    if (generation.current !== token) return;
    setBubbles((current) => {
      const next = current.slice();
      const last = next[next.length - 1];
      if (last?.role === "agent") next[next.length - 1] = { role: "agent", text, streaming: false, latency_ms: latency };
      return next;
    });
    speak(text, () => mutedRef.current, () => setSpeaking(true), () => setSpeaking(false));
  }

  async function begin() {
    generation.current += 1;
    window.speechSynthesis?.cancel();
    const previous = callIdRef.current;
    if (previous) {
      callIdRef.current = null;
      await api.discardCall(previous).catch(() => undefined);
    }
    const started = await api.startCall();
    callIdRef.current = started.id;
    setCallId(started.id);
    setBubbles([]);
    setTurn(started);
    setEvents([]);
    setCursor(0);
    setError(null);
    setEnded(false);
    setStartedAt(Date.now());
    setElapsed(0);
    await typeReply(started.say, started.latency_ms);
    return started;
  }

  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel();
      const id = callIdRef.current;
      if (id) void api.discardCall(id).catch(() => undefined);
    };
  }, []);

  useEffect(() => {
    if (!startedAt || ended) return;
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [startedAt, ended]);

  useEffect(() => {
    const node = scroller.current;
    if (!node || !pinned) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    node.scrollTo({ top: node.scrollHeight, behavior: reduce ? "auto" : "smooth" });
  }, [bubbles, events, pinned]);

  useEffect(() => {
    const next = fieldMap(turn);
    const previous = prevFields.current;
    const changed = Object.keys(next).find((key) => next[key] && next[key] !== previous[key]);
    prevFields.current = next;
    if (!changed) return;
    setFlash(changed);
    const timer = window.setTimeout(() => setFlash(null), 400);
    return () => window.clearTimeout(timer);
  }, [turn]);

  function markEnded(result: DemoTurn | null) {
    if (result?.outcome) setEnded(true);
  }

  async function send(text: string, activeId = callId) {
    const trimmed = text.trim();
    let id = activeId;
    if (!id) {
      const started = await begin();
      id = started.id;
    }
    if (!id || !trimmed || ended) return null;
    setBubbles((current) => [...current, { role: "caller", text: trimmed }]);
    const result = await api.sendTurn(id, trimmed);
    setTurn(result);
    setEvents((current) => [...current, ...result.events]);
    markEnded(result);
    await typeReply(result.say, result.latency_ms);
    return result;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (busy || ended || turn?.outcome || !draft.trim()) return;
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
      markEnded(latest);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Playback failed.");
    } finally {
      setBusy(false);
    }
  }

  async function step() {
    if (busy || ended || cursor >= script.turns.length) return;
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
    setSpeechNote("Listening. Speak as the caller, then press send.");
  }

  function toggleMute() {
    mutedRef.current = !mutedRef.current;
    setMuted(mutedRef.current);
    if (mutedRef.current) {
      window.speechSynthesis?.cancel();
      setSpeaking(false);
    }
  }

  function endCall() {
    generation.current += 1;
    window.speechSynthesis?.cancel();
    setSpeaking(false);
    setBusy(false);
    setEnded(true);
    const id = callIdRef.current;
    if (id && !turn?.outcome) {
      callIdRef.current = null;
      void api.discardCall(id).catch(() => undefined);
      setCallId(null);
    }
  }

  async function startNewCall() {
    setBusy(true);
    setError(null);
    try {
      await begin();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not start a new call.");
    } finally {
      setBusy(false);
    }
  }

  async function chooseScenario(nextId: string) {
    const switching = nextId !== scriptId;
    setScriptId(nextId);
    setCursor(0);
    if (switching && (ended || turn?.outcome || callId)) {
      await startNewCall();
    }
  }

  if (error && bubbles.length === 0) return <ErrorState message={error} onRetry={() => begin()} />;

  const slots = turn?.slots;
  const fields = [
    { id: "intent", label: "Intent", value: turn?.intent?.replaceAll("_", " ") || "" },
    { id: "issue", label: "Issue", value: slots?.issue || "" },
    { id: "name", label: "Name", value: slots?.name || "" },
    { id: "phone", label: "Phone", value: slots?.phone ? formatPhone(slots.phone) : "", mono: true },
    { id: "address", label: "Address", value: slots?.address || "" },
  ];
  const captured = fields.filter((field) => field.value && field.value !== "–").length;
  const sms = [...events].reverse().find((event) => event.type === "sms");
  const smsPayload = sms?.payload as { body?: string; delivery?: string } | undefined;
  const smsSent = smsPayload?.delivery === "sent";
  const nextLine = cursor < script.turns.length ? script.turns[cursor] : "";

  return (
    <div className="grid items-start gap-4 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
      <aside aria-label="Scenarios" className="order-2 xl:order-none">
        <div className="space-y-1" role="radiogroup" aria-label="Caller scenarios">
          {SCRIPTS.map((item) => {
            const selected = item.id === scriptId;
            return (
              <button
                key={item.id}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => {
                  void chooseScenario(item.id);
                }}
                className={cn(
                  "block w-full rounded-md px-2 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  selected ? "bg-primary-soft shadow-[inset_2px_0_0_hsl(var(--primary))]" : "hover:bg-muted",
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{item.label}</span>
                  {DANGER.has(item.id) && <Badge tone="escalated">Emergency</Badge>}
                </div>
                <div className="text-xs text-muted-foreground">{item.detail}</div>
              </button>
            );
          })}
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          Next line: {nextLine || "Scenario finished."}
        </p>
      </aside>

      <section aria-label="Live call" className="order-1 flex h-[min(640px,calc(100dvh-7rem))] min-h-[420px] flex-col rounded-lg border border-border bg-card xl:order-none xl:h-auto xl:min-h-[560px]">
        <div className="flex flex-col gap-2 border-b border-border px-3 py-2 sm:flex-row sm:flex-wrap sm:items-center">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            {ended ? (
              <span className="text-sm text-muted-foreground">Ended</span>
            ) : callId ? (
              <span className="text-xs font-medium text-muted-foreground">In call</span>
            ) : (
              <span className="text-xs font-medium text-muted-foreground">Ready</span>
            )}
            <span className="font-mono text-xs tabular-nums text-subtle">{formatElapsed(elapsed)}</span>
            <span className="truncate text-sm font-medium">{shopName}</span>
            <span className="text-xs text-subtle">{PHASE_LABEL[turn?.phase || "discover"] || turn?.phase}</span>
            {speaking && <span className="text-xs text-muted-foreground">Speaking</span>}
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
            <Button type="button" size="sm" variant="outline" aria-pressed={muted} onClick={toggleMute}>
              {muted ? "Unmute" : "Mute"}
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={endCall} disabled={ended}>
              End
            </Button>
            {(ended || turn?.outcome) && (
              <Button type="button" size="sm" onClick={() => void startNewCall()} disabled={busy}>
                Start new call
              </Button>
            )}
            <Button type="button" size="sm" variant="outline" onClick={step} disabled={busy || ended || cursor >= script.turns.length}>
              Step
            </Button>
            <Button type="button" size="sm" onClick={playThrough} disabled={busy}>
              Play through
            </Button>
          </div>
        </div>
        <div
          ref={scroller}
          className="relative flex-1 space-y-3 overflow-y-auto px-4 py-4"
          aria-live="polite"
          onScroll={() => {
            const node = scroller.current;
            if (!node) return;
            setPinned(node.scrollHeight - node.scrollTop - node.clientHeight < 48);
          }}
        >
          {bubbles.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Step through a scenario, or type what the caller would say. Nothing is logged until the call starts.
            </p>
          )}
          {bubbles.map((bubble, index) => (
            <div key={`${bubble.role}-${index}`} className={bubble.role === "caller" ? "ml-12" : "mr-12"}>
              <div className="mb-1 flex items-baseline justify-between text-xs text-subtle">
                <span>{bubble.role === "caller" ? "Caller" : "Riley"}</span>
                {showTimings && !bubble.thinking && bubble.latency_ms != null && (
                  <span className="font-mono tabular-nums" title="Rule engine response time (demo)">
                    {formatMs(bubble.latency_ms)}
                  </span>
                )}
              </div>
              <p
                className={cn(
                  "rounded-lg px-3 py-2 text-base",
                  bubble.role === "caller" ? "bg-muted" : "border border-border bg-background",
                  bubble.thinking && "text-muted-foreground",
                )}
              >
                {bubble.text}
                {bubble.streaming && <span className="caret" aria-hidden />}
              </p>
            </div>
          ))}
          {events.map((event, index) => (
            <details key={`${event.type}-${index}`} className="rounded-md border border-border px-3 py-2">
              <summary className="cursor-pointer text-sm font-medium">
                <span className="inline-flex items-center gap-1">
                  Tool call: {event.type.replaceAll("_", " ")}
                  <Check className="h-3.5 w-3.5 text-success" aria-hidden />
                </span>
              </summary>
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-5 text-muted-foreground">
                {JSON.stringify(event.payload, null, 2)}
              </pre>
            </details>
          ))}
          {!pinned && (
            <button
              type="button"
              className="sticky bottom-2 left-1/2 -translate-x-1/2 rounded-md border border-border bg-card px-2 py-1 text-xs shadow-composer dark:shadow-none"
              onClick={() => {
                setPinned(true);
                scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
              }}
            >
              Jump to latest
            </button>
          )}
        </div>
        <form onSubmit={onSubmit} className="border-t border-border p-3">
          {(ended || turn?.outcome) && (
            <p className="mb-2 text-sm text-muted-foreground">
              This call is finished. Start a new call to try another scenario or line.
            </p>
          )}
          <div className="flex items-center gap-2 rounded-lg border border-border bg-background p-2 shadow-composer dark:shadow-none">
            <Input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder={ended || turn?.outcome ? "Start a new call to continue" : "What the caller says"}
              aria-label="Caller line"
              disabled={busy || ended || Boolean(turn?.outcome)}
              className="border-0 bg-transparent shadow-none focus-visible:ring-offset-0"
            />
            <Button
              type="button"
              size="icon"
              variant="ghost"
              onClick={listen}
              aria-label="Speak as the caller"
              disabled={ended || Boolean(turn?.outcome)}
            >
              <Mic className="h-4 w-4" />
            </Button>
            <Button
              type="submit"
              size="icon"
              variant="outline"
              disabled={busy || ended || Boolean(turn?.outcome) || !draft.trim()}
              aria-label="Send caller line"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <p className="mt-1 text-xs text-subtle">Enter to send</p>
          {speechNote && <p className="mt-1 text-xs text-muted-foreground">{speechNote}</p>}
          {showTimings && <p className="mt-1 text-xs text-subtle">Rule engine response time (demo). This is not voice latency.</p>}
        </form>
        {error && bubbles.length > 0 && (
          <div className="mx-3 mb-3 flex items-center justify-between gap-2 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger" role="alert">
            <p>{error}</p>
            <Button type="button" size="sm" variant="outline" onClick={() => begin()}>
              Retry
            </Button>
          </div>
        )}
      </section>

      <aside aria-label="Call ticket" className="order-3 space-y-3 xl:order-none">
        {session.note && <p className="rounded-md bg-warning-soft px-3 py-2 text-sm text-warning">{session.note}</p>}
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-md font-semibold">Ticket</h2>
            {turn?.outcome && <Badge tone={turn.outcome}>{turn.outcome}</Badge>}
          </div>
          <p className="mt-1 text-xs text-subtle">{captured} of 5 details captured</p>
          <dl className="mt-2">
            {fields.map((field) => {
              const done = Boolean(field.value && field.value !== "–");
              return (
                <div
                  key={field.id}
                  className={cn(
                    "flex items-start justify-between gap-3 rounded-sm px-1 py-1.5 transition-colors duration-150",
                    flash === field.id && "bg-primary-soft",
                  )}
                >
                  <dt className="text-sm text-muted-foreground">{field.label}</dt>
                  <dd className={cn("flex items-center gap-1 text-right text-sm", field.mono && "font-mono tabular-nums")}>
                    {done ? <Check className="h-3.5 w-3.5 text-success" aria-hidden /> : null}
                    <span className={done ? "" : "text-subtle"}>{done ? field.value : "–"}</span>
                  </dd>
                </div>
              );
            })}
          </dl>
          {turn && turn.offered.length > 0 && (
            <div className="mt-3 border-t border-border pt-3">
              <div className="text-xs font-medium text-muted-foreground">Offered</div>
              <ul className="mt-1 space-y-1 text-sm">
                {turn.offered.map((slot) => (
                  <li key={slot}>{slot}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="mt-3 border-t border-border pt-3">
            <div className="mb-1 flex items-center justify-between">
              <h3 className="text-xs font-medium text-muted-foreground">Events</h3>
              <Button type="button" size="sm" variant="ghost" aria-pressed={showTimings} onClick={() => setShowTimings((value) => !value)}>
                {showTimings ? "Hide timings" : "Show timings"}
              </Button>
            </div>
            {events.length === 0 && <p className="text-sm text-subtle">–</p>}
            <ul className="space-y-1">
              {events.map((event, index) => (
                <li key={`${event.type}-${index}`} className="flex items-center gap-1 text-sm">
                  <Check className="h-3.5 w-3.5 text-success" aria-hidden />
                  <span className="capitalize">{event.type.replaceAll("_", " ")}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        {smsPayload?.body && (
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-medium">Confirmation text</h3>
              <Badge tone={smsSent ? "booked" : "mock"}>{smsSent ? "Sent" : "Mock"}</Badge>
            </div>
            <p className="mt-2 text-sm">{smsPayload.body}</p>
          </div>
        )}
      </aside>
    </div>
  );
}

function fieldMap(turn: DemoTurn | null): Record<string, string> {
  return {
    intent: turn?.intent || "",
    issue: turn?.slots.issue || "",
    name: turn?.slots.name || "",
    phone: turn?.slots.phone || "",
    address: turn?.slots.address || "",
  };
}

function formatElapsed(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
