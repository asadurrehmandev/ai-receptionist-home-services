/** A visitor key for this browser tab. It is not written to localStorage, sessionStorage, or a cookie. */

export type ProviderChoice = "auto" | "anthropic" | "openai";

export type SessionState = {
  key: string;
  provider: ProviderChoice;
  refused: boolean;
  note: string;
};

let state: SessionState = { key: "", provider: "auto", refused: false, note: "" };
const listeners = new Set<() => void>();

function emit() {
  for (const listener of listeners) listener();
}

export function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSession(): SessionState {
  return state;
}

export function setSessionKey(key: string, provider: ProviderChoice) {
  state = { key: key.trim(), provider, refused: false, note: "" };
  emit();
}

export function clearSessionKey() {
  state = { key: "", provider: "auto", refused: false, note: "" };
  emit();
}

export function noteRefusal(note: string) {
  state = { ...state, refused: true, note };
  emit();
}

export function resolvedProvider(session: SessionState = state): "anthropic" | "openai" | null {
  if (!session.key || session.refused) return null;
  if (session.provider === "anthropic" || session.key.startsWith("sk-ant-")) return "anthropic";
  if (session.provider === "openai" || session.key.startsWith("sk-")) return "openai";
  return "anthropic";
}

export function badgeLabel(envProvider?: string | null): string {
  const live = resolvedProvider();
  if (live === "openai") return "Live AI (OpenAI)";
  if (live === "anthropic") return "Live AI (Claude)";
  if (!state.key && envProvider === "openai") return "Live AI (OpenAI)";
  if (!state.key && envProvider === "anthropic") return "Live AI (Claude)";
  return "Demo mode: sample responses. Add your API key for live AI.";
}

export function isLive(envProvider?: string | null): boolean {
  return badgeLabel(envProvider).startsWith("Live AI");
}
