import React, { useMemo, useState } from 'react';
import { Area, CartesianGrid, ComposedChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ArrowDownLeft, ArrowUpRight } from 'lucide-react';
import { analysis } from '../../data/mockData.js';
import { Chip, Segmented } from '../ui/primitives.jsx';
import { cx, formatK, formatPLN } from '../../utils/format.js';

const C = { revenue: '#3F5E4A', expenses: '#E2B45C', in: '#2F8A57', out: '#C8463C', ink: '#23382B', muted: '#6B716C', line: '#E6E4DE', subtle: '#F5F4F0' };
const AXIS_TICK = { fill: C.muted, fontSize: 13, fontFamily: 'Red Hat Text' };
const FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'in', label: 'Money in' },
  { value: 'out', label: 'Money out' },
];

const dateFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });

function dateLabel(day) {
  const d = new Date(analysis.q4.start);
  d.setDate(d.getDate() + day);
  return dateFmt.format(d);
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
      <p className="t-small">Money in <b>{formatPLN(r.revenue)}</b></p>
      <p className="t-small">Money out <b>{formatPLN(r.expenses)}</b></p>
      <p className={cx('t-small', r.revenue - r.expenses < 0 ? 'text-status-red' : 'text-status-green')}>Net {formatPLN(r.revenue - r.expenses, { sign: true })}</p>
    </div>
  );
}

/** Round marker on top of an event line; hover or tap selects the event. */
function EventMarker({ viewBox, event, selected, onSelect }) {
  if (!viewBox) return null;
  const color = event.kind === 'in' ? C.in : C.out;
  const cx0 = viewBox.x;
  const cy0 = viewBox.y - 12;
  return (
    <g style={{ cursor: 'pointer' }} onMouseEnter={() => onSelect(event)} onClick={() => onSelect(event)}>
      <title>{`${dateLabel(event.day)} · ${event.label} · ${event.kind === 'in' ? '+' : '−'}${formatPLN(event.amount)}`}</title>
      {/* Larger invisible hit area for fingers. */}
      <circle cx={cx0} cy={cy0} r={14} fill="transparent" />
      <circle cx={cx0} cy={cy0} r={selected ? 9 : 7} fill={color} stroke="#fff" strokeWidth={2} />
      <text x={cx0} y={cy0 + 3.5} textAnchor="middle" fontSize={10} fontWeight={700} fill="#fff">
        {event.kind === 'in' ? '+' : '−'}
      </text>
    </g>
  );
}

function EventDetail({ event, today }) {
  const incoming = event.kind === 'in';
  const planned = event.day > today;
  const IconCmp = incoming ? ArrowDownLeft : ArrowUpRight;
  return (
    <div className={cx('flex flex-wrap items-center gap-3 rounded-[18px] px-4 py-3', incoming ? 'bg-status-green-soft' : 'bg-status-red-soft')}>
      <span className={cx('flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/85', incoming ? 'text-status-green' : 'text-status-red')}>
        <IconCmp className="h-5 w-5" strokeWidth={2} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="t-body-m">
          {event.label} · {event.who}
        </p>
        <p className="t-small text-text-muted">{dateLabel(event.day)} 2026</p>
      </div>
      <div className="flex flex-col items-end gap-1">
        <span className={cx('t-title', incoming ? 'text-status-green' : 'text-status-red')}>{formatPLN(incoming ? event.amount : -event.amount, { sign: true })}</span>
        <Chip tone={planned ? 'blue' : 'neutral'}>{planned ? 'Planned' : 'Done'}</Chip>
      </div>
    </div>
  );
}

function Totals({ rows, today }) {
  const sum = (key, pred) => rows.filter(pred).reduce((s, r) => s + r[key], 0);
  const soFar = (r) => r.day < today;
  const all = () => true;
  const items = [
    { label: 'Money in · so far', value: sum('revenue', soFar), sub: `Q4 forecast ${formatK(sum('revenue', all))}` },
    { label: 'Money out · so far', value: sum('expenses', soFar), sub: `Q4 forecast ${formatK(sum('expenses', all))}` },
    { label: 'Net · Q4 forecast', value: sum('revenue', all) - sum('expenses', all), sub: 'Dec from the engine', net: true },
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

/** Q4 money in vs out by week, with vertical markers on the days larger payments come in or go out. */
export default function CashFlowQ4() {
  const { q4 } = analysis;
  const [filter, setFilter] = useState('all');
  const rows = useMemo(() => q4.weeks.map((w) => ({ ...w, forecast: w.day >= q4.today })), [q4]);
  const events = q4.events.filter((e) => filter === 'all' || e.kind === filter);
  const nextEvent = q4.events.find((e) => e.day >= q4.today) || q4.events[0];
  const [selected, setSelected] = useState(nextEvent);
  const shown = events.includes(selected) ? selected : events[0];

  return (
    <section className="card flex min-w-0 flex-1 flex-col gap-4" aria-label="Money in and out in Q4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="t-title">Money in vs out · Q4</h2>
          <p className="t-small text-text-muted">{q4.label} · PLN per week · markers show when larger amounts move</p>
        </div>
        <Segmented value={filter} onChange={setFilter} options={FILTERS} />
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="flex items-center gap-1.5 t-small text-text-muted"><span className="h-3 w-3 rounded bg-green-700" />Money in</span>
        <span className="flex items-center gap-1.5 t-small text-text-muted"><span className="h-3 w-3 rounded bg-status-amber" />Money out</span>
        <span className="flex items-center gap-1.5 t-small text-text-muted"><span className="h-3 w-0.5 bg-status-green" />Payment in</span>
        <span className="flex items-center gap-1.5 t-small text-text-muted"><span className="h-3 w-0.5 bg-status-red" />Payment out</span>
        <span className="flex items-center gap-1.5 t-small text-text-muted"><span className="h-3 w-3 rounded bg-subtle ring-1 ring-line" />Forecast</span>
      </div>

      <div className="h-[260px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 28, right: 12, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="q4In" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={C.revenue} stopOpacity={0.35} />
                <stop offset="100%" stopColor={C.revenue} stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="q4Out" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={C.expenses} stopOpacity={0.4} />
                <stop offset="100%" stopColor={C.expenses} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke={C.line} />
            <ReferenceArea x1={q4.today} x2={q4.days} fill={C.subtle} fillOpacity={0.9} ifOverflow="hidden" />
            <XAxis
              dataKey="day"
              type="number"
              domain={[0, q4.days]}
              ticks={q4.months.map((m) => m.day)}
              tickFormatter={(d) => q4.months.find((m) => m.day === d)?.label}
              tickLine={false}
              axisLine={false}
              tick={AXIS_TICK}
              dy={6}
            />
            <YAxis tickFormatter={formatK} tickLine={false} axisLine={false} width={40} tick={AXIS_TICK} />
            <Tooltip content={<WeekTooltip />} cursor={{ stroke: C.ink, strokeOpacity: 0.25, strokeDasharray: '3 3' }} />
            <Area type="monotone" dataKey="revenue" stroke={C.revenue} strokeWidth={2.5} fill="url(#q4In)" isAnimationActive={false} />
            <Area type="monotone" dataKey="expenses" stroke={C.expenses} strokeWidth={2.5} fill="url(#q4Out)" isAnimationActive={false} />
            <ReferenceLine x={q4.today} stroke={C.ink} strokeOpacity={0.5} strokeDasharray="3 3" label={{ value: 'Today', position: 'insideBottomRight', fill: C.muted, fontSize: 12 }} />
            {events.map((e) => (
              <ReferenceLine
                key={`${e.day}-${e.label}`}
                x={e.day}
                stroke={e.kind === 'in' ? C.in : C.out}
                strokeWidth={shown === e ? 2.5 : 1.5}
                strokeOpacity={shown === e ? 1 : 0.55}
                strokeDasharray={e.day > q4.today ? '4 4' : undefined}
                label={<EventMarker event={e} selected={shown === e} onSelect={setSelected} />}
              />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {shown && <EventDetail event={shown} today={q4.today} />}

      <div className="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1 scrollbar-thin" aria-label="Payments in Q4">
        {events.map((e) => (
          <button
            key={`${e.day}-${e.label}`}
            type="button"
            onClick={() => setSelected(e)}
            className={cx(
              'flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 t-small transition-colors',
              shown === e ? 'bg-green-900 text-white' : 'bg-subtle text-text hover:bg-line',
            )}
          >
            <span className={cx('h-2 w-2 rounded-full', e.kind === 'in' ? 'bg-status-green' : 'bg-status-red')} />
            {dateLabel(e.day)} · {e.label}
          </button>
        ))}
      </div>

      <Totals rows={rows} today={q4.today} />
    </section>
  );
}
