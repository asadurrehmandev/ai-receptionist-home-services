import { CalendarDays, LayoutDashboard, PhoneCall, Settings2, SquareUser, Waves } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { KeySettings } from "@/components/KeySettings";
import { ModeBadge } from "@/components/ModeBadge";
import { cn } from "@/lib/utils";

const LINKS = [
  { to: "/", label: "Board", icon: LayoutDashboard, end: true },
  { to: "/calls", label: "Calls", icon: PhoneCall, end: false },
  { to: "/calendar", label: "Calendar", icon: CalendarDays, end: false },
  { to: "/leads", label: "Leads", icon: SquareUser, end: false },
  { to: "/simulator", label: "Call simulator", icon: Waves, end: false },
  { to: "/setup", label: "Shop setup", icon: Settings2, end: false },
];

export function Shell() {
  return (
    <div className="min-h-screen md:grid md:grid-cols-[240px_1fr]">
      <aside className="flex flex-col bg-[#14241c] text-[#f4efe6] md:min-h-screen">
        <div className="flex items-center gap-3 px-5 py-5">
          <span className="grid h-9 w-9 place-items-center rounded-md bg-[#b8612f] text-[#1c1915]">
            <Waves className="h-4 w-4" />
          </span>
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-[#e7a27a]">Northline</div>
            <div className="text-sm text-[#d9d3c7]">AI Receptionist</div>
          </div>
        </div>
        <nav className="flex flex-wrap gap-1 px-3 pb-3 md:flex-col md:flex-nowrap">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                cn(
                  "flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm text-[#d9d3c7]",
                  isActive && "bg-[#1f3a2e] text-white",
                )
              }
            >
              <link.icon className="h-4 w-4" />
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto hidden px-5 py-5 text-xs leading-5 text-[#b7c0b8] md:block">
          On-call tonight
          <div className="mt-1 text-sm text-[#f4efe6]">Miguel Santos</div>
          <div>(512) 555-0199</div>
        </div>
      </aside>
      <main className="min-w-0 px-4 py-5 md:px-8 md:py-7">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <ModeBadge />
          <KeySettings />
        </div>
        <Outlet />
      </main>
    </div>
  );
}
