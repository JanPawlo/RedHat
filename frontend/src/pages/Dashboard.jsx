import React from 'react';
import { Bell } from 'lucide-react';
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
  const unread = alerts.filter((a) => a.unread).length;
  return (
    <header className="hidden flex-wrap items-center gap-3 lg:flex">
      <div className="min-w-0 flex-1">
        <h1 className="t-display-l">
          {greeting()}, {company.owner.firstName}
        </h1>
        <p className="mt-0.5 t-small text-text-muted">{dateLabel} · here is what needs you today</p>
      </div>
      <button
        type="button"
        onClick={() => setAlertsOpen(true)}
        aria-label={unread ? `Notifications · ${unread} new` : 'Notifications'}
        title="Notifications"
        className="relative flex h-12 w-12 items-center justify-center rounded-full bg-surface transition-colors hover:bg-subtle"
      >
        <Bell className="h-5 w-5" strokeWidth={1.8} />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-status-red px-1 text-[11px] font-semibold text-white ring-2 ring-canvas">
            {unread}
          </span>
        )}
      </button>
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-green-700 t-title text-white">{company.owner.initials}</span>
    </header>
  );
}

/** Main screen: greeting on top (desktop), then the decision card in the middle. Phone: the card fills the screen. */
export default function Dashboard() {
  return (
    <div className="flex h-[calc(100dvh-88px)] min-h-[520px] flex-col gap-4 lg:h-[calc(100dvh-48px)] lg:min-h-[600px] lg:gap-5">
      <TopBar />
      <DecisionDeck />
    </div>
  );
}
