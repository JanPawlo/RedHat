import React, { useMemo, useState } from 'react';
import {
  Area, CartesianGrid, ComposedChart, Line, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { forecastKeyPoints, forecastSummary } from '../../data/mockData.js';
import { buildForecastRows, buildLiveRows, liveDomain, liveTicks } from '../../utils/forecast.js';
import { cx, formatK, formatPLN } from '../../utils/format.js';
import { useAppState } from '../../state/AppState.jsx';
import { Segmented } from '../ui/primitives.jsx';

const C = { ink: '#23382B', green: '#2F8A57', fill: '#6F8F78', red: '#C8463C', muted: '#6B716C', line: '#E6E4DE', past: '#9AA39C' };

const TICKS = { 30: [0, 11, 19, 30], 60: [0, 11, 19, 30, 42, 60], 90: [0, 11, 19, 30, 42, 60, 72, 90] };
const PAST_DAYS = 30;
const TOOLTIP_DRIVERS = 3;

function Legend({ buffer, live }) {
  const item = (swatch, label) => (
    <span className="flex items-center gap-1.5 t-small text-text-muted">
      {swatch}
      {label}
    </span>
  );
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1">
      {live && item(<span className="h-[3px] w-4 rounded-full" style={{ background: C.past }} />, 'Past · bank statement')}
      {item(<span className="h-[3px] w-4 rounded-full bg-green-900" />, 'Baseline · if you do nothing')}
      {item(<span className="h-0 w-4 border-t-[3px] border-dashed border-status-green" />, 'After approved actions')}
      {item(<span className="h-3 w-3 rounded-[3px] bg-status-red/35" />, 'Below buffer')}
      {item(<span className="h-0 w-4 border-t-2 border-dotted border-text-muted" />, `Safety buffer ${formatK(buffer)}`)}
    </div>
  );
}

function ChartTooltip({ active, payload, buffer }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  const value = row.balance ?? row.past;
  const diff = value - buffer;
  return (
    <div className="min-w-[220px] max-w-[300px] rounded-2xl bg-surface p-3 shadow-card ring-1 ring-line">
      <p className="t-overline text-text-muted">{row.label}{row.balance == null ? ' · actual' : ''}</p>
      <p className="mt-1 t-title">{formatPLN(value)}</p>
      <p className={cx('t-small', diff < 0 ? 'text-status-red' : 'text-text-muted')}>
        {diff < 0 ? `${formatPLN(-diff)} under the buffer` : `${formatPLN(diff)} above the buffer`}
      </p>
      {row.after != null && row.after !== row.balance && (
        <p className="mt-1.5 t-small text-status-green">With approved actions: {formatPLN(row.after)}</p>
      )}
      {row.drivers?.length > 0 && (
        <ul className="mt-2 space-y-0.5 border-t border-line pt-2">
          {row.drivers.slice(0, TOOLTIP_DRIVERS).map((driver) => (
            <li key={driver.label} className="flex justify-between gap-3 t-small">
              <span className="truncate text-text-muted">{driver.label}</span>
              <span className={Number(driver.amount) < 0 ? 'text-status-red' : 'text-status-green'}>{formatPLN(Number(driver.amount), { sign: true })}</span>
            </li>
          ))}
        </ul>
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

function useChartData(forecast, company, horizon) {
  return useMemo(() => {
    if (!forecast) {
      const rows = buildForecastRows(forecastKeyPoints, horizon, company.safetyBuffer);
      return { rows, ticks: TICKS[horizon], domain: [50000, 450000], yTicks: [100000, 200000, 300000, 400000], minX: 0 };
    }

    const rows = buildLiveRows(forecast, horizon, PAST_DAYS);
    return { rows, ticks: liveTicks(PAST_DAYS, horizon), domain: liveDomain(rows, company.safetyBuffer), yTicks: undefined, minX: -PAST_DAYS };
  }, [forecast, company.safetyBuffer, horizon]);
}

export default function ForecastCard() {
  const [horizon, setHorizon] = useState(60);
  // Phones: shorter chart labels so they stay inside the card.
  const narrow = typeof window !== 'undefined' && window.innerWidth < 640;
  const { cashProtected, forecast, company } = useAppState();
  const buffer = company.safetyBuffer;
  const { rows, ticks, domain, yTicks, minX } = useChartData(forecast, company, horizon);

  const future = rows.filter((r) => r.day >= 0 && r.balance != null);
  const labelByDay = useMemo(() => Object.fromEntries(rows.map((r) => [r.day, r.label])), [rows]);
  const low = future.reduce((m, r) => (r.balance < m.balance ? r : m), future[0]);
  const lowAfter = rows.find((r) => r.day === low.day)?.after;
  const afterValues = future.map((r) => r.after).filter((v) => v != null);
  const lowestWithActions = forecast ? (afterValues.length ? Math.min(...afterValues) : null) : forecastSummary.lowestWithActions;
  const lastRow = future[future.length - 1];
  const underBuffer = buffer - low.balance;

  return (
    <section className="card flex flex-col gap-4" aria-label="Cash forecast">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="t-display-l">Cash forecast</h2>
          <p className="t-small text-text-muted">
            {forecast ? `Last ${PAST_DAYS} days from the bank statement · next ${horizon} days from the engine` : `Next ${horizon} days`} · {company.currency}
          </p>
        </div>
        <Segmented
          value={horizon}
          onChange={setHorizon}
          options={[{ value: 30, label: '30 d' }, { value: 60, label: '60 d' }, { value: 90, label: '90 d' }]}
        />
      </div>
      <Legend buffer={buffer} live={Boolean(forecast)} />

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
              domain={[minX, horizon]}
              ticks={ticks}
              tickFormatter={(d) => labelByDay[d]}
              tickLine={false}
              axisLine={false}
              tick={{ fill: C.muted, fontSize: 13, fontFamily: 'Red Hat Text' }}
              dy={8}
            />
            <YAxis
              domain={domain}
              ticks={yTicks}
              tickFormatter={formatK}
              tickLine={false}
              axisLine={false}
              width={44}
              tick={{ fill: C.muted, fontSize: 13, fontFamily: 'Red Hat Text' }}
            />
            <Tooltip content={<ChartTooltip buffer={buffer} />} cursor={{ stroke: C.ink, strokeOpacity: 0.25, strokeDasharray: '3 3' }} />
            <Area dataKey="balance" stroke="none" fill="url(#fcFill)" isAnimationActive={false} />
            <Area dataKey="gap" stroke="none" fill={C.red} fillOpacity={0.3} isAnimationActive={false} connectNulls={false} />
            <ReferenceLine y={buffer} stroke={C.muted} strokeWidth={1.5} strokeDasharray="2 4" />
            <ReferenceLine x={0} stroke={C.ink} strokeOpacity={0.35} strokeDasharray="3 3" />
            {forecast && <Line dataKey="past" stroke={C.past} strokeWidth={2.25} dot={false} connectNulls={false} isAnimationActive={false} />}
            <Line dataKey="after" stroke={C.green} strokeWidth={2.5} strokeDasharray="6 5" dot={false} activeDot={{ r: 4 }} connectNulls={false} isAnimationActive={false} />
            <Line dataKey="balance" stroke={C.ink} strokeWidth={2.75} dot={false} activeDot={{ r: 5, fill: C.ink, stroke: '#fff', strokeWidth: 2 }} connectNulls={false} isAnimationActive={false} />
            {lowAfter != null && <ReferenceDot x={low.day} y={lowAfter} r={5} fill={C.green} stroke="#fff" strokeWidth={2.5} />}
            <ReferenceDot
              x={low.day}
              y={low.balance}
              r={6}
              fill={underBuffer > 0 ? C.red : C.ink}
              stroke="#fff"
              strokeWidth={3}
              label={
                underBuffer > 0 ? (
                  <ChipLabel tone="red" text={narrow ? `−${formatK(underBuffer)} under buffer` : `Below buffer · −${formatPLN(underBuffer)} on ${low.label}`} dx={narrow ? -60 : 14} dy={narrow ? 10 : -6} width={narrow ? 150 : 260} />
                ) : undefined
              }
            />
            {lowestWithActions != null && lastRow?.after != null && (
              <ReferenceDot
                x={lastRow.day}
                y={lastRow.after}
                r={0}
                label={<ChipLabel tone="green" text={narrow ? `With actions: low ${formatK(lowestWithActions)}` : `With approved actions: lowest ${formatPLN(lowestWithActions)}`} dx={narrow ? -170 : -300} dy={-44} width={narrow ? 170 : 300} />}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Kpi
          label="Lowest balance"
          value={formatPLN(low.balance)}
          sub={underBuffer > 0 ? `${low.label} · ${formatPLN(underBuffer)} under buffer` : `${low.label} · above the buffer`}
          tone={underBuffer > 0 ? 'text-status-red' : undefined}
        />
        <Kpi label="Runway" value={typeof company.runwayMonths === 'number' ? `${company.runwayMonths} months` : 'Not falling'} sub="at current costs" />
        <Kpi label="Cash protected" value={formatPLN(cashProtected, { sign: true })} sub="lowest balance gained from your swipes" tone="text-status-green" />
      </div>
    </section>
  );
}
