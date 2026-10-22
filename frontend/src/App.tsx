import { Route, Routes } from "react-router-dom";

import { Shell } from "@/components/Shell";
import { Board } from "@/pages/Board";
import { CalendarPage } from "@/pages/CalendarPage";
import { CallDetail } from "@/pages/CallDetail";
import { Calls } from "@/pages/Calls";
import { Leads } from "@/pages/Leads";
import { Setup } from "@/pages/Setup";
import { Simulator } from "@/pages/Simulator";

export default function App() {
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
