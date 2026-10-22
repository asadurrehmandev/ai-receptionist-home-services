import { useEffect, useState, useSyncExternalStore } from "react";

import { api } from "@/lib/api";
import { badgeLabel, getSession, isLive, subscribe } from "@/lib/sessionKey";

export function ModeBadge({ compact = false }: { compact?: boolean }) {
  const session = useSyncExternalStore(subscribe, getSession, getSession);
  const [envProvider, setEnvProvider] = useState<string | null>(null);

  useEffect(() => {
    api
      .health()
      .then((health) => setEnvProvider(health.llm_provider ?? null))
      .catch(() => setEnvProvider(null));
  }, []);

  const label = badgeLabel(envProvider);
  const live = isLive(envProvider);
  return (
    <p
      role="status"
      className={
        compact
          ? `max-w-[14rem] text-left text-[10px] leading-4 ${live ? "text-[#1f6a45]" : "text-[#8a5a12]"}`
          : `rounded-full border px-3 py-1 text-xs leading-5 ${
              live ? "border-[#b7d7c4] bg-[#e5f2ea] text-[#1f6a45]" : "border-[#e6d3a4] bg-[#f8ecd9] text-[#6b4a10]"
            }`
      }
    >
      {label}
      {session.note ? <span className="sr-only">{session.note}</span> : null}
    </p>
  );
}
