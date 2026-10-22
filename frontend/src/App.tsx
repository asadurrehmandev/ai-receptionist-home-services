import { useEffect, useState, type FormEvent } from "react";
import { Route, Routes } from "react-router-dom";

import { Shell } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, setAdminToken } from "@/lib/api";
import { Board } from "@/pages/Board";
import { CalendarPage } from "@/pages/CalendarPage";
import { CallDetail } from "@/pages/CallDetail";
import { Calls } from "@/pages/Calls";
import { Leads } from "@/pages/Leads";
import { Setup } from "@/pages/Setup";
import { Simulator } from "@/pages/Simulator";

function DeskLogin({ onReady }: { onReady: () => void }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setAdminToken(token.trim());
    try {
      await api.overview();
      onReady();
    } catch {
      setAdminToken("");
      setError("That token was refused. The board stays closed.");
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 className="text-lg font-semibold">Sign in</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        This board is locked. Paste the admin token to load calls and leads. The call simulator is available when demo mode is on.
      </p>
      <form className="mt-6 space-y-3" onSubmit={submit}>
        <Input
          type="password"
          autoComplete="current-password"
          value={token}
          onChange={(event) => setToken(event.target.value)}
          placeholder="Admin token"
          aria-label="Admin token"
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full">
          Open the desk
        </Button>
      </form>
    </main>
  );
}

export default function App() {
  const [gate, setGate] = useState<"loading" | "open" | "login">("loading");

  useEffect(() => {
    api
      .health()
      .then((health) => {
        if (health.demo_mode) setGate("open");
        else setGate("login");
      })
      .catch(() => setGate("login"));
  }, []);

  if (gate === "loading") {
    return <main className="p-8 text-sm text-muted-foreground">Opening the desk…</main>;
  }
  if (gate === "login") return <DeskLogin onReady={() => setGate("open")} />;

  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Board />} />
        <Route path="calls" element={<Calls />} />
        <Route path="calls/:id" element={<CallDetail />} />
        <Route path="calendar" element={<CalendarPage />} />
        <Route path="leads" element={<Leads />} />
        <Route path="simulator" element={<Simulator />} />
        <Route path="setup" element={<Setup />} />
      </Route>
    </Routes>
  );
}
