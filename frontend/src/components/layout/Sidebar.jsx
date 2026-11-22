import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { BarChart3, Check, ChevronDown, Plus, FileText, LayoutGrid, History, Landmark, LogOut, Mail, MessageSquareText, SlidersHorizontal } from 'lucide-react';
import { apiFetch } from '../../api/client.js';
import { useAppState } from '../../state/AppState.jsx';
import { cx } from '../../utils/format.js';
import { COMPANY_SWITCHER_ADD, COMPANY_SWITCHER_LABEL } from '../../const/company.js';
import { AI_HEALTH_ENDPOINT, MODEL_BADGE_STATUS, MODEL_BADGE_TEXT, NEMO_STATUS_CONNECTED } from '../../const/layout.js';

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
        cx('group flex items-center gap-3 rounded-full px-4 py-2.5 t-body-m transition-colors', isActive ? 'bg-green-700 text-white' : 'text-text-muted hover:bg-subtle hover:text-text')
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

/**
 * Shows whether the RHOAI model answers (hard requirement badge), through the backend only: there is no direct
 * route from the browser to the model, so every question passes the guardrails. With NeMo Guardrails switched on
 * the badge shows its state too; NeMo down means every chat fails, so it is shown as a warning.
 */
function ModelStatus() {
  const [state, setState] = useState({ status: MODEL_BADGE_STATUS.checking });
  useEffect(() => {
    let alive = true;
    apiFetch(AI_HEALTH_ENDPOINT)
      .then((d) => {
        if (!alive) return;
        const nemo = d.guardrails || {};
        const nemoDown = nemo.enabled && nemo.status !== NEMO_STATUS_CONNECTED;
        setState({ status: nemoDown ? MODEL_BADGE_STATUS.warning : MODEL_BADGE_STATUS.online, model: d.configured_model, nemo });
      })
      .catch(() => alive && setState({ status: MODEL_BADGE_STATUS.offline }));
    return () => {
      alive = false;
    };
  }, []);
  const dot = {
    online: 'bg-status-green',
    warning: 'bg-status-amber',
    offline: 'bg-status-amber',
    checking: 'bg-text-muted animate-pulse',
  }[state.status];
  const line1 = state.model ? `${state.model} · vLLM` : MODEL_BADGE_TEXT.defaultModel;
  const line2 =
    state.status === MODEL_BADGE_STATUS.online && state.nemo?.enabled
      ? MODEL_BADGE_TEXT.onlineGuarded
      : MODEL_BADGE_TEXT[state.status];
  return (
    <div className="flex items-center gap-2.5 rounded-2xl px-3 py-2.5 ring-1 ring-inset ring-line" title={MODEL_BADGE_TEXT.tooltip}>
      <span className={cx('h-2 w-2 shrink-0 rounded-full', dot)} />
      <div className="min-w-0">
        <p className="truncate t-small text-text">{line1}</p>
        <p className="truncate t-small text-text-muted">{line2}</p>
      </div>
    </div>
  );
}

/** Company switcher: the current company and (later) other ones. One company per deployment for now. */
function CompanySwitcher() {
  const { company } = useAppState();
  const [open, setOpen] = useState(false);
  return (
    <div className="relative mt-1">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
        className="flex w-full items-center gap-2 rounded-2xl bg-subtle px-3 py-2 text-left transition-colors hover:bg-line"
      >
        <span className="min-w-0 flex-1">
          <span className="block t-overline text-text-muted">{COMPANY_SWITCHER_LABEL}</span>
          <span className="block truncate t-body-m">{company.name}</span>
        </span>
        <ChevronDown className={cx('h-4 w-4 shrink-0 text-text-muted transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <ul role="listbox" aria-label={COMPANY_SWITCHER_LABEL} className="absolute inset-x-0 top-full z-20 mt-1 flex flex-col gap-0.5 rounded-2xl bg-surface p-1.5 shadow-card ring-1 ring-line">
          <li role="option" aria-selected="true">
            <button type="button" onClick={() => setOpen(false)} className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left t-small hover:bg-subtle">
              <span className="min-w-0 flex-1 truncate">{company.legalName || company.name}</span>
              <Check className="h-4 w-4 shrink-0 text-green-700" />
            </button>
          </li>
          <li>
            <span className="flex items-center gap-2 rounded-xl px-2.5 py-2 t-small text-text-muted">
              <Plus className="h-4 w-4 shrink-0" /> {COMPANY_SWITCHER_ADD}
            </span>
          </li>
        </ul>
      )}
    </div>
  );
}

/** Menu items, shared by the desktop sidebar and the phone drawer. */
export function SidebarContent({ onLogout, onNavigate }) {
  const { invoices, mails } = useAppState();
  const unpaid = invoices.filter((i) => i.status !== 'paid').length;
  const needsOk = mails.filter((m) => m.status === 'Needs OK').length;

  return (
    <div className="flex min-h-full flex-1 flex-col gap-1" onClick={(e) => onNavigate && e.target.closest('a') && onNavigate()}>
      <div className="flex items-center gap-2.5 px-2 py-1">
        <Logo />
        <span className="t-title">RedCaps CFO</span>
      </div>

      <CompanySwitcher />

      <p className="mt-2 px-4 py-1 t-overline text-text-muted">Menu</p>
      <nav className="flex flex-col gap-0.5">
        <NavItem to="/" end icon={LayoutGrid} label="Dashboard" />
        <NavItem to="/analysis" icon={BarChart3} label="Analysis" />
        <NavItem to="/invoices" icon={FileText} label="Invoices" badge={unpaid || null} />
        <NavItem to="/mail" icon={Mail} label="Mail" badge={needsOk || null} />
        <NavItem to="/advisor" icon={MessageSquareText} label="Advisor" />
        <NavItem to="/banks" icon={Landmark} label="Banks" />
      </nav>

      <p className="mt-2 px-4 py-1 t-overline text-text-muted">Control</p>
      <nav className="flex flex-col gap-0.5">
        <NavItem to="/history" icon={History} label="History" />
        <NavItem to="/rules" icon={SlidersHorizontal} label="Rules" />
      </nav>

      <div className="min-h-3 flex-1" />

      <ModelStatus />

      <button type="button" onClick={onLogout} className="flex items-center gap-3 rounded-full px-4 py-2.5 t-body-m text-text-muted transition-colors hover:bg-subtle hover:text-text">
        <LogOut className="h-5 w-5" strokeWidth={1.8} />
        Log out
      </button>
    </div>
  );
}

/** Desktop and laptop sidebar; on smaller screens the same items live in the hamburger drawer. */
export default function Sidebar({ onLogout }) {
  return (
    <aside className="sticky top-6 hidden h-[calc(100dvh-48px)] w-[224px] shrink-0 flex-col overflow-y-auto rounded-card bg-surface px-3.5 py-4 scrollbar-thin lg:flex">
      <SidebarContent onLogout={onLogout} />
    </aside>
  );
}
