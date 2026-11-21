import React, { useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Ban, CalendarDays, Check, CheckCheck, ChevronDown, Clock, FileText, Filter, Sparkles } from 'lucide-react';
import { invoiceGroups, paidThisMonth } from '../data/mockData.js';
import { useAppState } from '../state/AppState.jsx';
import { Bar, Button, Chip, IconCircle, PageHeader, Pill, TONE_DOT } from '../components/ui/primitives.jsx';
import Icon from '../components/ui/Icon.jsx';
import { cx, formatPLN } from '../utils/format.js';

const GROUP_TONE = { overdue: 'red', today: 'blue', week: 'amber', later: 'green' };
const BAR_COLOR = { red: 'bg-status-red', blue: 'bg-status-blue', amber: 'bg-status-amber', green: 'bg-status-green' };

function InvoiceTile({ inv, onPay, onSchedule, onToggle }) {
  const tone = GROUP_TONE[inv.group];
  const scheduled = inv.status === 'scheduled';
  return (
    <motion.article
      layout
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96, transition: { duration: 0.2 } }}
      className={cx('flex flex-col gap-3.5 rounded-tile bg-surface p-5 transition-shadow', inv.selected ? 'ring-2 ring-green-700' : 'hover:shadow-soft')}
    >
      <div className="flex items-start gap-3">
        <button
          type="button"
          onClick={onToggle}
          aria-pressed={!!inv.selected}
          aria-label={inv.selected ? 'Unselect invoice' : 'Select invoice'}
          className={cx('relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full transition-colors', inv.selected ? 'bg-green-700 text-white' : 'bg-green-100 text-green-700 hover:bg-green-200')}
        >
          {inv.selected ? <Check className="h-5 w-5" strokeWidth={2.4} /> : <Icon name={inv.icon} className="h-[22px] w-[22px]" />}
        </button>
        <div className="min-w-0 flex-1">
          <p className="t-title">{inv.supplier}</p>
          <p className="t-small text-text-muted">{inv.category}</p>
        </div>
        <Chip tone={scheduled ? 'neutral' : tone}>{scheduled ? 'Scheduled' : inv.urgency}</Chip>
      </div>
      <p className="t-display-l">{formatPLN(inv.amount)}</p>
      <div className="flex items-center justify-between gap-2">
        <span className="t-mono text-text-muted">{inv.number}</span>
        <span className="text-right t-small">{inv.due}</span>
      </div>
      <Bar pct={inv.progress * 100} color={BAR_COLOR[tone]} height={6} />
      <div className="flex items-center gap-2">
        <Chip dot>KSeF verified</Chip>
        <div className="flex-1" />
        <Button kind="ghost" size="sm" onClick={onSchedule}>{scheduled ? 'Unschedule' : 'Schedule'}</Button>
        <Button size="sm" onClick={onPay}>Pay now</Button>
      </div>
    </motion.article>
  );
}

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'overdue', label: 'Overdue' },
  { id: 'week', label: 'This week' },
  { id: 'discount', label: 'Discount' },
  { id: 'later', label: 'Later' },
];

export default function Invoices() {
  const { invoices, payInvoice, scheduleInvoice, toggleInvoice, paySelected, showToast } = useAppState();
  const [filter, setFilter] = useState('all');
  const [showPaid, setShowPaid] = useState(false);
  const open = invoices.filter((i) => i.status !== 'paid');
  const paidNow = invoices.filter((i) => i.status === 'paid');
  const selected = open.filter((i) => i.selected);

  const sum = (list) => list.reduce((s, i) => s + i.amount, 0);
  const byGroup = (g) => open.filter((i) => i.group === g);
  const counts = {
    all: open.length,
    overdue: byGroup('overdue').length,
    week: byGroup('week').length,
    discount: open.filter((i) => i.discount).length,
    later: byGroup('later').length,
  };

  const visible = useMemo(() => {
    if (filter === 'all') return open;
    if (filter === 'discount') return open.filter((i) => i.discount);
    return open.filter((i) => i.group === filter);
  }, [open, filter]);

  const summary = [
    { icon: Ban, tone: 'red', label: 'Overdue', value: formatPLN(sum(byGroup('overdue'))), sub: `${counts.overdue} invoices · pay today` },
    { icon: Clock, tone: 'amber', label: 'Due in 7 days', value: formatPLN(sum(byGroup('week'))), sub: `${counts.week} invoices` },
    { icon: Sparkles, tone: 'blue', label: 'Discount available', value: counts.discount ? '−592 PLN' : '—', sub: counts.discount ? '1 invoice · ends today' : 'none open' },
    { icon: CalendarDays, tone: 'green', label: 'Later', value: formatPLN(sum(byGroup('later'))), sub: `${counts.later} invoices · after 1 Dec` },
  ];

  const pay = (inv) => {
    payInvoice(inv.id);
    showToast({ tone: 'green', text: `${formatPLN(inv.amount)} to ${inv.supplier} · SIMULATED payment` });
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Pending invoices" subtitle={`${open.length} to pay · ${formatPLN(sum(open))} · most urgent first`}>
        <Button kind="ghost" icon={FileText}>Import from KSeF</Button>
        <Button
          icon={Check}
          disabled={!selected.length}
          onClick={() => {
            paySelected();
            showToast({ tone: 'green', text: `${selected.length} invoices paid · ${formatPLN(sum(selected))} · SIMULATED` });
          }}
        >
          Pay selected ({selected.length})
        </Button>
      </PageHeader>

      <div className="grid grid-cols-4 gap-4">
        {summary.map((s) => (
          <div key={s.label} className="flex items-center gap-3.5 rounded-tile bg-surface p-[18px]">
            <IconCircle icon={s.icon} tone={s.tone} />
            <div>
              <p className="t-small text-text-muted">{s.label}</p>
              <p className="t-title">{s.value}</p>
              <p className="t-small text-text-muted">{s.sub}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {FILTERS.map((f) => (
          <Pill key={f.id} active={filter === f.id} onClick={() => setFilter(f.id)}>
            {f.label} · {counts[f.id]}
          </Pill>
        ))}
        <div className="flex-1" />
        <span className="flex items-center gap-1.5 rounded-full bg-surface px-3.5 py-2 t-small">
          <Filter className="h-4 w-4 text-text-muted" /> Sort: most urgent
        </span>
      </div>

      {invoiceGroups.map((g) => {
        const list = visible.filter((i) => i.group === g.id);
        if (!list.length) return null;
        return (
          <section key={g.id} className="flex flex-col gap-3">
            <h2 className="flex items-center gap-2.5">
              <span className={cx('h-2.5 w-2.5 rounded-full', TONE_DOT[g.tone])} />
              <span className="t-overline">{g.label}</span>
              <span className="t-small text-text-muted">
                {list.length} · {g.id === 'today' ? g.note : formatPLN(sum(list))}
              </span>
            </h2>
            <motion.div layout className="grid grid-cols-3 gap-4">
              <AnimatePresence initial={false}>
                {list.map((inv) => (
                  <InvoiceTile key={inv.id} inv={inv} onPay={() => pay(inv)} onSchedule={() => scheduleInvoice(inv.id)} onToggle={() => toggleInvoice(inv.id)} />
                ))}
              </AnimatePresence>
            </motion.div>
          </section>
        );
      })}
      {!visible.length && <p className="card text-center t-body text-text-muted">Nothing here. Every invoice in this filter is paid.</p>}

      <section className="flex flex-col gap-3 rounded-tile bg-green-100 px-5 py-4">
        <div className="flex items-center gap-3">
          <CheckCheck className="h-5 w-5 text-status-green" />
          <p className="flex-1 t-body-m">
            Paid this month: {paidThisMonth.count + paidNow.length} invoices · {paidThisMonth.note}
          </p>
          <Button kind="ghost" iconRight={ChevronDown} onClick={() => setShowPaid((v) => !v)}>{showPaid ? 'Hide paid' : 'Show paid'}</Button>
        </div>
        {showPaid && (
          <ul className="flex flex-col divide-y divide-green-200">
            {paidNow.map((i) => (
              <li key={i.id} className="flex justify-between py-2 t-small">
                <span>{i.supplier} · {i.number}</span>
                <span className="t-mono">{formatPLN(i.amount)} · just now</span>
              </li>
            ))}
            <li className="py-2 t-small text-text-muted">+ {paidThisMonth.count} earlier this month · {paidThisMonth.amount}</li>
          </ul>
        )}
      </section>
    </div>
  );
}
