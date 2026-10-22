export type OutcomeCounts = Record<string, number>;

export type CallSummary = {
  id: string;
  channel: string;
  started_at: string;
  ended_at: string | null;
  caller_name: string | null;
  caller_phone: string | null;
  caller_address: string | null;
  issue: string | null;
  intent: string | null;
  outcome: string | null;
  phase: string | null;
  summary: string | null;
  avg_latency_ms: number | null;
  max_latency_ms: number | null;
  timed_turns: number;
};

export type Turn = {
  role: string;
  text: string;
  latency_ms: number | null;
  created_at: string;
};

export type DeskEvent = {
  id?: number;
  call_id?: string | null;
  type: string;
  status?: string | null;
  created_at?: string;
  payload: Record<string, unknown>;
};

export type CallDetail = CallSummary & {
  turns: Turn[];
  events: DeskEvent[];
};

export type Booking = {
  id: string;
  call_id: string | null;
  name: string | null;
  phone: string | null;
  address: string | null;
  issue: string | null;
  start: string;
  end: string;
  status: string;
};

export type Lead = {
  id: string;
  call_id: string | null;
  name: string | null;
  phone: string | null;
  address: string | null;
  issue: string | null;
  intent: string | null;
  status: string | null;
  created_at: string;
  payload: Record<string, unknown>;
};

export type Metrics = {
  count: number;
  avg_ms: number | null;
  p50_ms: number | null;
  p95_ms: number | null;
  max_ms: number | null;
  outcomes: OutcomeCounts;
};

export type Overview = {
  business: { name: string; agent_name: string; trade: string; city: string; phone_display: string; timezone: string };
  on_call: { name: string; phone: string };
  counts: OutcomeCounts;
  total_calls: number;
  metrics: Metrics;
  recent_calls: CallSummary[];
  upcoming: Booking[];
  leads: Lead[];
  webhooks: DeskEvent[];
};

export type Health = {
  ok: boolean;
  business: string;
  llm: boolean;
  stt: boolean;
  tts: boolean;
  twilio_signature: boolean;
  media_stream_ready: boolean;
  brain: string;
  demo_mode?: boolean;
};

export type PublicConfig = {
  business: Overview["business"];
  service_area: { cities: string[]; zips: string[] };
  hours: Record<string, { open: string; close: string } | null>;
  services: string[];
  pricing: {
    diagnostic_fee_usd: number;
    after_hours_fee_usd: number;
    emergency_dispatch_usd: number;
    rules: { id: string; label: string; low_usd: number; high_usd: number }[];
  };
  escalation: { on_call_name: string; on_call_phone: string };
  crm: { webhook_url: string; provider_label: string };
  voice: { mode: string; gather_voice: string };
  runtime: Health;
};

export type DemoTurn = {
  id: string;
  say: string;
  outcome: string | null;
  intent: string | null;
  phase: string;
  latency_ms: number;
  slots: {
    name: string | null;
    phone: string | null;
    address: string | null;
    issue: string | null;
    zip: string | null;
    city: string | null;
  };
  offered: string[];
  events: { type: string; payload: Record<string, unknown> }[];
};

export function adminToken(): string {
  return sessionStorage.getItem("adminToken") || "";
}

export function setAdminToken(token: string) {
  if (token) sessionStorage.setItem("adminToken", token);
  else sessionStorage.removeItem("adminToken");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = adminToken();
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (response.status === 401) {
    setAdminToken("");
    throw new Error("unauthorized");
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  overview: () => request<Overview>("/api/overview"),
  calls: () => request<{ calls: CallSummary[] }>("/api/calls"),
  call: (id: string) => request<CallDetail>(`/api/calls/${id}`),
  bookings: () => request<{ bookings: Booking[] }>("/api/bookings"),
  leads: () => request<{ leads: Lead[] }>("/api/leads"),
  events: (type?: string) => request<{ events: DeskEvent[] }>(type ? `/api/events?type=${type}` : "/api/events"),
  config: () => request<PublicConfig>("/api/config"),
  health: () => request<Health>("/api/health"),
  startCall: () => request<DemoTurn>("/api/demo/calls", { method: "POST" }),
  sendTurn: (id: string, text: string) =>
    request<DemoTurn>(`/api/demo/calls/${id}/turns`, { method: "POST", body: JSON.stringify({ text }) }),
  reset: () => request<{ ok: boolean; calls: number }>("/api/admin/reset", { method: "POST" }),
  replay: (id: number) => request<{ status: string; detail?: string }>(`/api/events/${id}/replay`, { method: "POST" }),
};
