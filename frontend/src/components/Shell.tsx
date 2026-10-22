import { CalendarDays, LayoutDashboard, Menu, Monitor, Moon, Phone, PhoneCall, Settings2, SquareUser, Sun, Waves, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import * as Tooltip from "@radix-ui/react-tooltip";

import { KeySettings } from "@/components/KeySettings";
import { ModeBadge } from "@/components/ModeBadge";
import { Button } from "@/components/ui/button";
import { readTheme, storeTheme, type ThemeChoice } from "@/lib/theme";
import { cn } from "@/lib/utils";

const LINKS = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/calls", label: "Calls", icon: PhoneCall, end: false },
  { to: "/calendar", label: "Calendar", icon: CalendarDays, end: false },
  { to: "/leads", label: "Leads", icon: SquareUser, end: false },
  { to: "/simulator", label: "Simulator", icon: Waves, end: false },
  { to: "/setup", label: "Shop setup", icon: Settings2, end: false },
];

const TITLES: Record<string, string> = {
  "/": "Overview",
  "/calls": "Calls",
  "/calendar": "Calendar",
  "/leads": "Leads",
  "/simulator": "Simulator",
  "/setup": "Shop setup",
};

function titleFor(pathname: string) {
  if (pathname.startsWith("/calls/")) return "Call";
  return TITLES[pathname] || "Northline";
}

export function Shell() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState<ThemeChoice>(() => readTheme());
  const wide = useWide();

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  function choose(next: ThemeChoice) {
    setTheme(next);
    storeTheme(next);
  }

  return (
    <Tooltip.Provider delayDuration={300}>
      <div className="min-h-screen bg-background md:grid md:grid-cols-[56px_1fr] lg:grid-cols-[232px_1fr]">
        <aside className="hidden min-h-screen flex-col border-r border-border bg-surface md:flex">
          <Brand />
          <Nav compact={!wide} />
          <p className="mt-auto hidden px-4 py-4 text-xs text-subtle lg:block">Sample data</p>
        </aside>
        {open && (
          <div className="fixed inset-0 z-40 md:hidden">
            <button className="absolute inset-0 bg-foreground/40" aria-label="Close menu" onClick={() => setOpen(false)} />
            <aside className="relative flex h-full w-[232px] flex-col border-r border-border bg-surface">
              <div className="flex items-center justify-between pr-2">
                <Brand />
                <Button variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Close menu">
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <Nav compact={false} />
              <p className="mt-auto px-4 py-4 text-xs text-subtle">Sample data</p>
            </aside>
          </div>
        )}
        <div className="min-w-0">
          <header className="flex min-h-[52px] flex-wrap items-center gap-x-2 gap-y-1 border-b border-border px-3 py-1.5 md:px-4">
            <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
              <Menu className="h-4 w-4" />
            </Button>
            <h1 className="min-w-0 truncate text-md font-semibold tracking-tight">{titleFor(pathname)}</h1>
            <div className="flex w-full min-w-0 flex-wrap items-center justify-end gap-1.5 sm:ml-auto sm:w-auto">
              <ModeBadge />
              <div className="flex rounded-md border border-border" role="group" aria-label="Color theme">
                <ThemeButton current={theme} value="light" label="Light theme" onClick={choose}>
                  <Sun className="h-3.5 w-3.5" />
                </ThemeButton>
                <ThemeButton current={theme} value="dark" label="Dark theme" onClick={choose}>
                  <Moon className="h-3.5 w-3.5" />
                </ThemeButton>
                <ThemeButton current={theme} value="system" label="System theme" onClick={choose}>
                  <Monitor className="h-3.5 w-3.5" />
                </ThemeButton>
              </div>
              <KeySettings />
            </div>
          </header>
          <main className="min-w-0 overflow-x-hidden px-3 py-4 md:px-6 md:py-5">
            <Outlet />
          </main>
        </div>
      </div>
    </Tooltip.Provider>
  );
}

function useWide() {
  const [wide, setWide] = useState(true);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const apply = () => setWide(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);
  return wide;
}

function Brand() {
  return (
    <div className="flex h-[52px] items-center gap-2 px-3 lg:px-3">
      <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-primary text-primary-foreground">
        <Phone className="h-4 w-4" />
      </span>
      <span className="hidden text-sm font-semibold lg:inline">Northline</span>
    </div>
  );
}

function Nav({ compact }: { compact: boolean }) {
  return (
    <nav className="flex flex-col gap-0.5 px-2" aria-label="Desk">
      {LINKS.map((link) => {
        const item = (
          <NavLink
            to={link.to}
            end={link.end}
            aria-label={link.label}
            className={({ isActive }) =>
              cn(
                "flex h-8 items-center gap-2 rounded-md px-2 text-sm font-medium text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
                isActive && "bg-muted text-foreground",
              )
            }
          >
            <link.icon className="h-4 w-4 shrink-0" />
            <span className="hidden lg:inline">{link.label}</span>
          </NavLink>
        );
        if (!compact) return <div key={link.to}>{item}</div>;
        return (
          <Tooltip.Root key={link.to}>
            <Tooltip.Trigger asChild>{item}</Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                side="right"
                sideOffset={8}
                className="z-50 rounded-md border border-border-strong bg-popover px-2 py-1 text-xs text-popover-foreground shadow-pop dark:shadow-none"
              >
                {link.label}
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        );
      })}
    </nav>
  );
}

function ThemeButton({
  current,
  value,
  label,
  onClick,
  children,
}: {
  current: ThemeChoice;
  value: ThemeChoice;
  label: string;
  onClick: (value: ThemeChoice) => void;
  children: ReactNode;
}) {
  const active = current === value;
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={active}
      onClick={() => onClick(value)}
      className={cn(
        "grid h-8 w-8 place-items-center text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        active && "bg-muted text-foreground",
      )}
    >
      {children}
    </button>
  );
}
