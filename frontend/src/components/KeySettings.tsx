import { useState, useSyncExternalStore, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  clearSessionKey,
  getSession,
  setSessionKey,
  subscribe,
  type ProviderChoice,
} from "@/lib/sessionKey";

const NOTE =
  "Your key is used only for this session and is never stored or logged. We recommend rotating or revoking the key after testing.";

export function KeySettings({ label = "API key" }: { label?: string }) {
  const session = useSyncExternalStore(subscribe, getSession, getSession);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [provider, setProvider] = useState<ProviderChoice>("auto");

  function submit(event: FormEvent) {
    event.preventDefault();
    setSessionKey(draft, provider);
    setDraft("");
    setOpen(false);
  }

  const holding = session.key ? (session.refused ? "Key refused. Demo replies are on." : "Key held in memory for this tab") : "No key this session";

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button type="button" size="sm" variant="outline">
          <span className="sm:hidden">Key</span>
          <span className="hidden sm:inline">{label}</span>
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Use your own model key</DialogTitle>
          <DialogDescription>{NOTE}</DialogDescription>
        </DialogHeader>
        <form className="mt-4 space-y-3" onSubmit={submit}>
          <label className="block text-sm">
            <span className="text-muted-foreground">Provider</span>
            <select
              className="mt-1 w-full rounded-md border border-input bg-card px-3 py-2 text-sm"
              value={provider}
              onChange={(event) => setProvider(event.target.value as ProviderChoice)}
              aria-label="Model provider"
            >
              <option value="auto">Auto-detect from the key</option>
              <option value="anthropic">Anthropic</option>
              <option value="openai">OpenAI</option>
            </select>
          </label>
          <Input
            type="password"
            autoComplete="off"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Paste an Anthropic or OpenAI key"
            aria-label="API key"
          />
          <p className="text-xs text-muted-foreground">{holding}</p>
          <div className="flex gap-2">
            <Button type="submit" disabled={!draft.trim()}>
              Use for this session
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                clearSessionKey();
                setDraft("");
                setOpen(false);
              }}
            >
              Clear
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
