import * as Tooltip from "@radix-ui/react-tooltip";
import { FlaskConical } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";

import { api } from "@/lib/api";
import { badgeLabel, getSession, isLive, subscribe } from "@/lib/sessionKey";

const TIP =
  "No API key: replies come from rules and recorded samples. CRM sync is mocked. Add your API key for live AI.";

export function ModeBadge() {
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
  const short = live ? label : "Demo mode: sample responses";

  return (
    <Tooltip.Provider delayDuration={200}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <p
            role="status"
            className={
              live
                ? "inline-flex h-5 max-w-full items-center gap-1 rounded-sm bg-info-soft px-1.5 text-xs font-medium text-info"
                : "inline-flex h-5 max-w-full items-center gap-1 rounded-sm bg-warning-soft px-1.5 text-xs font-medium text-warning"
            }
          >
            <FlaskConical className="h-3.5 w-3.5 shrink-0" aria-hidden />
            <span className="truncate sm:hidden">{live ? "Live" : "Demo mode"}</span>
            <span className="hidden truncate sm:inline">{short}</span>
            <span className="sr-only">{label}</span>
            {session.note ? <span className="sr-only">{session.note}</span> : null}
          </p>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            className="z-50 max-w-xs rounded-lg border border-border-strong bg-popover px-3 py-2 text-xs text-popover-foreground shadow-pop dark:shadow-none"
            sideOffset={6}
          >
            {live ? label : TIP}
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
