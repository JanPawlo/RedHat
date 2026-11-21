import React, { useState } from 'react';
import { Bell, Search } from 'lucide-react';
import { AlertStack, AlertsPanel } from '../components/dashboard/Alerts.jsx';
import ForecastCard from '../components/dashboard/ForecastCard.jsx';
import DecisionDeck from '../components/dashboard/DecisionDeck.jsx';
import { useAppState } from '../state/AppState.jsx';
import { TODAY } from '../data/mockData.js';

const dateLabel = new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(TODAY);

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

export function TopBar({ onBell }) {
  const { company, alerts } = useAppState();
  const unread = alerts.some((a) => a.unread);
  return (
    <header className="flex flex-wrap items-center gap-3">
      <div className="min-w-0 flex-1">
        <h1 className="t-display-l">{greeting()}, {company.owner.firstName}</h1>
        <p className="mt-0.5 t-small text-text-muted">{dateLabel} · here is what needs you today</p>
      </div>
      <label className="flex w-[300px] items-center gap-2.5 rounded-full bg-surface py-1.5 pl-[18px] pr-1.5">
        <input placeholder="Search invoices, people, emails…" className="min-w-0 flex-1 bg-transparent t-small outline-none placeholder:text-text-muted" />
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-green-900 text-white">
          <Search className="h-[18px] w-[18px]" />
        </span>
      </label>
      <button type="button" onClick={onBell} aria-label="Alerts" className="relative flex h-12 w-12 items-center justify-center rounded-full bg-surface transition-colors hover:bg-subtle">
        <Bell className="h-5 w-5" strokeWidth={1.8} />
        {unread && <span className="absolute right-3 top-2.5 h-2.5 w-2.5 rounded-full bg-status-red" />}
      </button>
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-green-700 t-title text-white">{company.owner.initials}</span>
    </header>
  );
}

export default function Dashboard() {
  const [alertsOpen, setAlertsOpen] = useState(false);
  return (
    <div className="flex flex-col gap-6">
      <TopBar onBell={() => setAlertsOpen(true)} />
      <AlertStack onOpen={() => setAlertsOpen(true)} />
      <ForecastCard />
      <DecisionDeck />
      <AlertsPanel open={alertsOpen} onClose={() => setAlertsOpen(false)} />
    </div>
  );
}
