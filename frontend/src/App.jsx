import React from 'react';
import { Route, Routes } from 'react-router-dom';
import { ScrollText, SlidersHorizontal } from 'lucide-react';
import AppLayout from './components/layout/AppLayout.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Analysis from './pages/Analysis.jsx';
import Invoices from './pages/Invoices.jsx';
import Risk from './pages/Risk.jsx';
import Mail from './pages/Mail.jsx';
import ComingSoon from './pages/ComingSoon.jsx';
import { AppStateProvider } from './state/AppState.jsx';

export default function App() {
  return (
    <AppStateProvider>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="analysis" element={<Analysis />} />
          <Route path="invoices" element={<Invoices />} />
          <Route path="risk" element={<Risk />} />
          <Route path="mail" element={<Mail />} />
          <Route
            path="ledger"
            element={<ComingSoon icon={ScrollText} title="Ledger" text="Every decision and agent action with its rule, status (SIMULATED, PENDING, BLOCKED BY POLICY) and the full “why”. Not designed yet." />}
          />
          <Route
            path="rules"
            element={<ComingSoon icon={SlidersHorizontal} title="Rules" text="Hard rules the agent must follow and rules learned from your swipes. Not designed yet." />}
          />
          <Route path="*" element={<ComingSoon title="Page not found" text="This page does not exist." />} />
        </Route>
      </Routes>
    </AppStateProvider>
  );
}
