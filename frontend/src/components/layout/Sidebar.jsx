import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { BarChart3, ChevronDown, Database, FileText, LayoutGrid, LogOut, Mail, ScrollText, ShieldAlert, SlidersHorizontal } from 'lucide-react';
import { apiFetch } from '../../api/client.js';
import { useAppState } from '../../state/AppState.jsx';
import { cx } from '../../utils/format.js';

export function Logo({ size = 34 }) {
  return (
    <span className="relative inline-flex shrink-0 items-center justify-center rounded-xl bg-green-900" style={{ width: size, height: size }} aria-hidden>
      <svg viewBox="0 0 34 34" width={size} height={size}>
        <path d="M8 19a9 9 0 0 1 18 0z" fill="#D7262E" />
        <rect x="6" y="19" width="22" height="3" rx="1.5" fill="#D7262E" />
      </svg>
    </span>
  );
}

function NavItem({ to, icon: IconCmp, label, badge, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cx('group flex items-center gap-3 rounded-full px-4 py-3 t-body-m transition-colors', isActive ? 'bg-green-700 text-white' : 'text-text-muted hover:bg-subtle hover:text-text')
      }
    >
      {({ isActive }) => (
        <>
          <IconCmp className="h-5 w-5 shrink-0" strokeWidth={1.8} />
          <span className="flex-1">{label}</span>
          {badge ? (
            <span className={cx('min-w-[22px] rounded-full px-2 py-0.5 text-center t-small', isActive ? 'bg-surface text-green-700' : 'bg-status-red text-white')}>{badge}</span>
          ) : null}
        </>
      )}
    </NavLink>
  );
}

/** Shows whether the RHOAI model answers (hard requirement badge). Falls back to "demo data" offline. */
function ModelStatus() {
  const [state, setState] = useState({ status: 'checking' });
  useEffect(() => {
    let alive = true;
    const json = (r) => (r.ok ? r.json() : Promise.reject(r.status));
    // 1) direct vLLM connection (Vite /vllm proxy to the OpenShift AI port-forward), 2) backend health check
    fetch('/vllm/v1/models')
      .then(json)
      .then((d) => alive && setState({ status: 'online', model: d.data?.[0]?.id }))
      .catch(() =>
        apiFetch('/ai/health')
          .then((d) => alive && setState({ status: 'online', model: d.configured_model }))
          .catch(() => alive && setState({ status: 'offline' })),
      );
    return () => {
      alive = false;
    };
  }, []);
  const dot = { online: 'bg-status-green', offline: 'bg-status-amber', checking: 'bg-text-muted animate-pulse' }[state.status];
  const line1 = state.status === 'online' ? `${state.model || 'Model'} · vLLM` : 'Qwen3-8B · vLLM';
  const line2 = { online: 'OpenShift AI · active', offline: 'Model offline · demo data', checking: 'Checking model…' }[state.status];
  return (
    <div className="flex items-center gap-2.5 rounded-2xl px-3 py-2.5 ring-1 ring-inset ring-line" title="Open-weights model served on Red Hat OpenShift AI">
      <span className={cx('h-2 w-2 shrink-0 rounded-full', dot)} />
      <div className="min-w-0">
        <p className="truncate t-small text-text">{line1}</p>
        <p className="truncate t-small text-text-muted">{line2}</p>
      </div>
    </div>
  );
}

export default function Sidebar({ onLogout }) {
  const { company, invoices, mails, autopilot, setAutopilot } = useAppState();
  const unpaid = invoices.filter((i) => i.status !== 'paid').length;
  const needsOk = mails.filter((m) => m.status === 'Needs OK').length;

  return (
    <aside className="sticky top-6 flex h-[calc(100vh-48px)] w-[232px] shrink-0 flex-col gap-1.5 overflow-y-auto rounded-card bg-surface px-4 py-5 scrollbar-thin">
      <div className="flex items-center gap-2.5 px-2 py-1">
        <Logo />
        <span className="t-title">RedCaps CFO</span>
      </div>

      <button type="button" className="mt-1 flex items-center gap-2 rounded-2xl bg-subtle px-3 py-2.5 text-left transition-colors hover:bg-line">
        <span className="min-w-0 flex-1">
          <span className="block t-overline text-text-muted">Company</span>
          <span className="block truncate t-body-m">{company.name}</span>
        </span>
        <ChevronDown className="h-4 w-4 text-text-muted" />
      </button>

      <p className="mt-4 px-4 py-1.5 t-overline text-text-muted">Menu</p>
      <nav className="flex flex-col gap-1.5">
        <NavItem to="/" end icon={LayoutGrid} label="Dashboard" />
        <NavItem to="/analysis" icon={BarChart3} label="Analysis" />
        <NavItem to="/invoices" icon={FileText} label="Invoices" badge={unpaid || null} />
        <NavItem to="/risk" icon={ShieldAlert} label="Risk" />
        <NavItem to="/mail" icon={Mail} label="Mail" badge={needsOk || null} />
      </nav>

      <p className="mt-3 px-4 py-1.5 t-overline text-text-muted">Control</p>
      <nav className="flex flex-col gap-1.5">
        <NavItem to="/ledger" icon={ScrollText} label="Ledger" />
        <NavItem to="/rules" icon={SlidersHorizontal} label="Rules" />
        <NavItem to="/live" icon={Database} label="Live data" />
      </nav>

      <div className="flex-1" />

      <div className="flex flex-col gap-2.5 rounded-[22px] bg-green-900 p-4">
        <div className="flex items-center justify-between">
          <span className="t-title text-white">Autopilot</span>
          <button
            type="button"
            role="switch"
            aria-checked={autopilot}
            aria-label="Autopilot"
            onClick={() => setAutopilot(!autopilot)}
            className={cx('relative h-6 w-10 rounded-full transition-colors', autopilot ? 'bg-green-500' : 'bg-white/20')}
          >
            <span className={cx('absolute left-0 top-[3px] h-[18px] w-[18px] rounded-full bg-surface shadow transition-transform', autopilot ? 'translate-x-[19px]' : 'translate-x-[3px]')} />
          </button>
        </div>
        <p className="t-small text-green-200">
          {autopilot
            ? `Acts alone under ${company.autopilotLimit.toLocaleString('en-US')} PLN. Bigger moves wait for your swipe.`
            : 'Off. Every action waits for your swipe.'}
        </p>
      </div>

      <ModelStatus />

      <button type="button" onClick={onLogout} className="flex items-center gap-3 rounded-full px-4 py-2.5 t-body-m text-text-muted transition-colors hover:bg-subtle hover:text-text">
        <LogOut className="h-5 w-5" strokeWidth={1.8} />
        Log out
      </button>
    </aside>
  );
}
