import React, { useMemo, useState } from 'react';
import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useAnalysis } from '../../state/analysisStore.js';
import { cx, formatK, formatPLN } from '../../utils/format.js';

const C = { in: '#2F8A57', out: '#C8463C', ink: '#23382B', muted: '#6B716C', line: '#E6E4DE', subtle: '#F5F4F0' };
const AXIS_TICK = { fill: C.muted, fontSize: 13, fontFamily: 'Red Hat Text' };
// Only the largest payments get a marker, so the chart stays readable.
const KEY_PAYMENTS = 5;

const dateFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });

let q4Start = null;

function dateLabel(day) {
  const d = new Date(q4Start);
  d.setDate(d.getDate() + day);
  return dateFmt.format(d);
}

/** The few payments that move the most money, in date order. */
function keyPayments(events) {
  return [...events]
    .sort((a, b) => b.amount - a.amount)
    .slice(0, KEY_PAYMENTS)
    .sort((a, b) => a.day - b.day);
}

function WeekTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const r = payload[0].payload;
  return (
    <div className="rounded-2xl bg-surface p-3 shadow-card ring-1 ring-line">
      <p className="t-overline text-text-muted">
        Week of {dateLabel(r.day)}
        {r.forecast ? ' · forecast' : ''}
      </p>
      <p className={cx('t-title', r.net < 0 ? 'text-status-red' : 'text-status-green')}>{formatPLN(r.net, { sign: true })}</p>
      <p className="t-small text-text-muted">
        in {formatPLN(r.revenue)} · out {formatPLN(r.expenses)}
      </p>
    </div>
  );
}

/** Small dot above a key payment's line. */
function PaymentMarker({ viewBox, payment, selected, onSelect }) {
  if (!viewBox) return null;
  const color = payment.kind === 'in' ? C.in : C.out;
  return (
    <g style={{ cursor: 'pointer' }} onMouseEnter={() => onSelect(payment)} onClick={() => onSelect(payment)}>
      <title>{`${dateLabel(payment.day)} · ${payment.label} · ${formatPLN(payment.kind === 'in' ? payment.amount : -payment.amount, { sign: true })}`}</title>
      <circle cx={viewBox.x} cy={viewBox.y - 10} r={14} fill="transparent" />
      <circle cx={viewBox.x} cy={viewBox.y - 10} r={selected ? 6 : 4.5} fill={color} stroke="#fff" strokeWidth={2} />
    </g>
  );
}

function PaymentList({ payments, selected, onSelect, today }) {
  return (
    <ul className="flex flex-col divide-y divide-line">
      {payments.map((p) => {
        const incoming = p.kind === 'in';
        return (
          <li key={`${p.day}-${p.label}`}>
            <button
              type="button"
              onClick={() => onSelect(p)}
              onMouseEnter={() => onSelect(p)}
              className={cx('flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left transition-colors', selected === p ? 'bg-subtle' : 'hover:bg-subtle')}
            >
              <span className={cx('h-2 w-2 shrink-0 rounded-full', incoming ? 'bg-status-green' : 'bg-status-red')} />
              <span className="w-14 shrink-0 t-small text-text-muted">{dateLabel(p.day)}</span>
              <span className="min-w-0 flex-1 truncate t-small">
                {p.label}
                {p.day > today && <span className="text-text-muted"> · planned</span>}
              </span>
              <span className={cx('shrink-0 t-body-m', incoming ? 'text-status-green' : 'text-status-red')}>
                {formatPLN(incoming ? p.amount : -p.amount, { sign: true })}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function Totals({ rows, today }) {
  const sum = (key, pred) => rows.filter(pred).reduce((s, r) => s + r[key], 0);
  const soFar = (r) => r.day < today;
  const all = () => true;
  const items = [
    { label: 'Money in · so far', value: sum('revenue', soFar), sub: `Q4 forecast ${formatK(sum('revenue', all))}` },
    { label: 'Money out · so far', value: sum('expenses', soFar), sub: `Q4 forecast ${formatK(sum('expenses', all))}` },
    { label: 'Net · Q4 forecast', value: sum('net', all), sub: 'Dec from the engine', net: true },
  ];
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {items.map((t) => (
        <div key={t.label} className="flex flex-col gap-0.5 rounded-[18px] bg-subtle px-4 py-3">
          <p className="t-small text-text-muted">{t.label}</p>
          <p className={cx('t-title', t.net && (t.value >= 0 ? 'text-status-green' : 'text-status-red'))}>{formatPLN(t.value, { sign: t.net })}</p>
          <p className="t-small text-text-muted">{t.sub}</p>
        </div>
      ))}
    </div>
  );
}

/** Q4 in one chart: what is left each week (money in − money out), with markers only for the largest payments. */
export default function CashFlowQ4() {
  const { q4 } = useAnalysis();
  q4Start = q4.start;
  const rows = useMemo(() => q4.weeks.map((w) => ({ ...w, net: w.revenue - w.expenses, forecast: w.day >= q4.today })), [q4]);
  const payments = useMemo(() => keyPayments(q4.events), [q4]);
  const [picked, setSelected] = useState(null);
  const selected = payments.includes(picked) ? picked : payments.find((p) => p.day >= q4.today) || payments[0];

  return (
    <section className="card flex min-w-0 flex-1 flex-col gap-4" aria-label="Money in and out in Q4">
      <div className="min-w-0">
        <h2 className="t-title">Money in vs out · Q4</h2>
        <p className="t-small text-text-muted">{q4.label} · what is left each week (in − out)</p>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="flex items-center gap-1.5 t-small text-text-muted"><span className="h-[3px] w-4 rounded-full bg-status-green" />Net cash flow</span>      </div>

      <div className="h-[240px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 24, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke={C.line} />
            <ReferenceArea x1={q4.today} x2={q4.days} fill={C.subtle} fillOpacity={0.9} ifOverflow="hidden" />
            <XAxis
              dataKey="day"
              type="number"
              domain={[-3, q4.days]}
              ticks={q4.months.map((m) => m.day)}
              tickFormatter={(d) => q4.months.find((m) => m.day === d)?.label}
              tickLine={false}
              axisLine={false}
              tick={AXIS_TICK}
              dy={6}
            />
            <YAxis tickFormatter={formatK} tickLine={false} axisLine={false} width={44} tick={AXIS_TICK} />
            <Tooltip content={<WeekTooltip />} cursor={{ stroke: C.ink, strokeOpacity: 0.25, strokeDasharray: '3 3' }} />
            <ReferenceLine y={0} stroke={C.ink} strokeOpacity={0.35} />
            <Line
              type="monotone"
              dataKey="net"
              stroke={C.in}
              strokeWidth={2.5}
              dot={{ r: 4, fill: C.in, stroke: '#fff', strokeWidth: 1.5 }}
              activeDot={{ r: 6, fill: C.in, stroke: '#fff', strokeWidth: 2 }}
              isAnimationActive={false}
            />
            <ReferenceLine x={q4.today} stroke={C.ink} strokeOpacity={0.5} strokeDasharray="3 3" label={{ value: 'Today', position: 'insideTopLeft', fill: C.muted, fontSize: 12 }} />
            {payments.map((p) => (
              <ReferenceLine
                key={`${p.day}-${p.label}`}
                x={p.day}
                stroke={p.kind === 'in' ? C.in : C.out}
                strokeOpacity={selected === p ? 0.9 : 0.3}
                strokeDasharray="2 4"
                label={<PaymentMarker payment={p} selected={selected === p} onSelect={setSelected} />}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div>
        <p className="mb-1 px-2 t-overline text-text-muted">Largest payments</p>
        <PaymentList payments={payments} selected={selected} onSelect={setSelected} today={q4.today} />
      </div>

      <Totals rows={rows} today={q4.today} />
    </section>
  );
}
