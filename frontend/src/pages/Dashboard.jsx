import React from 'react';
import { Bell, Search } from 'lucide-react';
import { AlertStack } from '../components/dashboard/Alerts.jsx';
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

export function TopBar() {
  const { company, alerts, setAlertsOpen } = useAppState();
  const unread = alerts.some((a) => a.unread);
  return (
    <header className="hidden flex-wrap items-center gap-3 lg:flex">
      <div className="min-w-0 flex-1">
        <h1 className="t-display-l">
          {greeting()}, {company.owner.firstName}
        </h1>
        <p className="mt-0.5 t-small text-text-muted">{dateLabel} · here is what needs you today</p>
      </div>
      <label className="flex w-[260px] items-center gap-2.5 rounded-full bg-surface py-1.5 pl-[18px] pr-1.5 xl:w-[300px]">
        <input placeholder="Search invoices, people, emails…" className="min-w-0 flex-1 bg-transparent t-small outline-none placeholder:text-text-muted" />
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-green-900 text-white">
          <Search className="h-[18px] w-[18px]" />
        </span>
      </label>
      <button type="button" onClick={() => setAlertsOpen(true)} aria-label="Alerts" className="relative flex h-12 w-12 items-center justify-center rounded-full bg-surface transition-colors hover:bg-subtle">
        <Bell className="h-5 w-5" strokeWidth={1.8} />
        {unread && <span className="absolute right-3 top-2.5 h-2.5 w-2.5 rounded-full bg-status-red" />}
      </button>
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-green-700 t-title text-white">{company.owner.initials}</span>
    </header>
  );
}

/** Main screen: greeting and alerts on top (desktop), then the decision card in the middle. Phone: the card fills the screen. */
export default function Dashboard() {
  const { setAlertsOpen } = useAppState();
  return (
    <div className="flex h-[calc(100dvh-88px)] min-h-[520px] flex-col gap-4 lg:h-[calc(100dvh-48px)] lg:min-h-[600px] lg:gap-5">
      <TopBar />
      <div className="hidden lg:block">
        <AlertStack onOpen={() => setAlertsOpen(true)} />
      </div>
      <DecisionDeck />
    </div>
  );
}
