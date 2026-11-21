import React, { useMemo, useState } from 'react';
import {
  Area, CartesianGrid, ComposedChart, Line, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { company, forecastKeyPoints, forecastSummary } from '../../data/mockData.js';
import { buildForecastRows } from '../../utils/forecast.js';
import { cx, formatK, formatPLN } from '../../utils/format.js';
import { useAppState } from '../../state/AppState.jsx';
import { Segmented } from '../ui/primitives.jsx';

const C = { ink: '#23382B', green: '#2F8A57', fill: '#6F8F78', red: '#C8463C', muted: '#6B716C', line: '#E6E4DE' };

const TICKS = { 30: [0, 11, 19, 30], 60: [0, 11, 19, 30, 42, 60], 90: [0, 11, 19, 30, 42, 60, 72, 90] };

function Legend() {
  const item = (swatch, label) => (
    <span className="flex items-center gap-1.5 t-small text-text-muted">
      {swatch}
      {label}
    </span>
  );
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1">
      {item(<span className="h-[3px] w-4 rounded-full bg-green-900" />, 'Baseline · if you do nothing')}
      {item(<span className="h-0 w-4 border-t-[3px] border-dashed border-status-green" />, 'After approved actions')}
      {item(<span className="h-3 w-3 rounded-[3px] bg-status-red/35" />, 'Below buffer')}
      {item(<span className="h-0 w-4 border-t-2 border-dotted border-text-muted" />, `Safety buffer ${formatK(company.safetyBuffer)}`)}
    </div>
  );
}

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  const diff = row.balance - company.safetyBuffer;
  return (
    <div className="min-w-[200px] rounded-2xl bg-surface p-3 shadow-card ring-1 ring-line">
      <p className="t-overline text-text-muted">{row.label}</p>
      <p className="mt-1 t-title">{formatPLN(row.balance)}</p>
      <p className={cx('t-small', diff < 0 ? 'text-status-red' : 'text-text-muted')}>
        {diff < 0 ? `${formatPLN(-diff)} under the buffer` : `${formatPLN(diff)} above the buffer`}
      </p>
      {row.after != null && row.after !== row.balance && (
        <p className="mt-1.5 t-small text-status-green">With approved actions: {formatPLN(row.after)}</p>
      )}
    </div>
  );
}

/** Small HTML chip inside the SVG chart (used as a ReferenceDot label). */
function ChipLabel({ viewBox, text, tone, dx = 14, dy = -14, width = 260 }) {
  if (!viewBox) return null;
  const tones = { red: 'bg-status-red-soft text-status-red', green: 'bg-status-green-soft text-status-green' };
  const dot = { red: 'bg-status-red', green: 'bg-status-green' };
  return (
    <foreignObject x={viewBox.x + dx} y={viewBox.y + dy} width={width} height={30} style={{ overflow: 'visible' }}>
      <span className={cx('inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 t-small shadow-soft', tones[tone])}>
        <span className={cx('h-1.5 w-1.5 rounded-full', dot[tone])} />
        {text}
      </span>
    </foreignObject>
  );
}

function Kpi({ label, value, sub, tone }) {
  return (
    <div className="min-w-0 rounded-[18px] bg-subtle px-4 py-3">
      <p className="t-small text-text-muted">{label}</p>
      <p className={cx('t-title', tone)}>{value}</p>
      <p className="t-small text-text-muted">{sub}</p>
    </div>
  );
}

export default function ForecastCard() {
  const [horizon, setHorizon] = useState(60);
  // Phones: shorter chart labels so they stay inside the card.
  const narrow = typeof window !== 'undefined' && window.innerWidth < 640;
  const { cashProtected } = useAppState();
  const rows = useMemo(() => buildForecastRows(forecastKeyPoints, horizon, company.safetyBuffer), [horizon]);
  const low = rows.reduce((m, r) => (r.balance < m.balance ? r : m), rows[0]);
  const lowAfter = rows[low.day]?.after;
  const lastAfter = rows[rows.length - 1];

  return (
    <section className="card flex flex-col gap-4" aria-label="Cash forecast">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="t-display-l">Cash forecast</h2>
          <p className="t-small text-text-muted">Next {horizon} days · PLN · numbers from the engine, words from the AI</p>
        </div>
        <Segmented
          value={horizon}
          onChange={setHorizon}
          options={[{ value: 30, label: '30 d' }, { value: 60, label: '60 d' }, { value: 90, label: '90 d' }]}
        />
      </div>
      <Legend />

      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 16, right: 12, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="fcFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={C.fill} stopOpacity={0.28} />
                <stop offset="100%" stopColor={C.fill} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke={C.line} />
            <XAxis
              dataKey="day"
              type="number"
              domain={[0, horizon]}
              ticks={TICKS[horizon]}
              tickFormatter={(d) => rows[d]?.label}
              tickLine={false}
              axisLine={false}
              tick={{ fill: C.muted, fontSize: 13, fontFamily: 'Red Hat Text' }}
              dy={8}
            />
            <YAxis
              domain={[50000, 450000]}
              ticks={[100000, 200000, 300000, 400000]}
              tickFormatter={formatK}
              tickLine={false}
              axisLine={false}
              width={44}
              tick={{ fill: C.muted, fontSize: 13, fontFamily: 'Red Hat Text' }}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: C.ink, strokeOpacity: 0.25, strokeDasharray: '3 3' }} />
            <Area dataKey="balance" stroke="none" fill="url(#fcFill)" isAnimationActive={false} />
            <Area dataKey="gap" stroke="none" fill={C.red} fillOpacity={0.3} isAnimationActive={false} connectNulls={false} />
            <ReferenceLine y={company.safetyBuffer} stroke={C.muted} strokeWidth={1.5} strokeDasharray="2 4" />
            <ReferenceLine x={0} stroke={C.ink} strokeOpacity={0.35} strokeDasharray="3 3" />
            <Line dataKey="after" stroke={C.green} strokeWidth={2.5} strokeDasharray="6 5" dot={false} activeDot={{ r: 4 }} connectNulls={false} isAnimationActive={false} />
            <Line dataKey="balance" stroke={C.ink} strokeWidth={2.75} dot={false} activeDot={{ r: 5, fill: C.ink, stroke: '#fff', strokeWidth: 2 }} isAnimationActive={false} />
            {lowAfter && <ReferenceDot x={low.day} y={lowAfter} r={5} fill={C.green} stroke="#fff" strokeWidth={2.5} />}
            <ReferenceDot
              x={low.day}
              y={low.balance}
              r={6}
              fill={C.red}
              stroke="#fff"
              strokeWidth={3}
              label={<ChipLabel tone="red" text={narrow ? `−${formatK(company.safetyBuffer - low.balance)} under buffer` : `Below buffer · −${formatPLN(company.safetyBuffer - low.balance).replace(' PLN', '')} PLN on ${low.label}`} dx={narrow ? -60 : 14} dy={narrow ? 10 : -6} width={narrow ? 150 : 260} />}
            />
            <ReferenceDot
              x={lastAfter.day}
              y={lastAfter.after}
              r={0}
              label={<ChipLabel tone="green" text={narrow ? `With actions: low ${formatK(forecastSummary.lowestWithActions)}` : `With approved actions: lowest ${formatPLN(forecastSummary.lowestWithActions)}`} dx={narrow ? -170 : -300} dy={-44} width={narrow ? 170 : 300} />}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Kpi
          label="Lowest balance"
          value={formatPLN(forecastSummary.lowest.amount)}
          sub={`${forecastSummary.lowest.date} · ${formatPLN(forecastSummary.lowest.underBuffer).replace(' PLN', '')} under buffer`}
          tone="text-status-red"
        />
        <Kpi label="Runway" value={`${company.runwayMonths} months`} sub="at current costs" />
        <Kpi label="Cash protected" value={formatPLN(cashProtected, { sign: true })} sub="this month, from your swipes" tone="text-status-green" />
      </div>
    </section>
  );
}
