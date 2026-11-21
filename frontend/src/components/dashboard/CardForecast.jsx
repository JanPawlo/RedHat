import React, { useMemo } from 'react';
import { Area, CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { TrendingUp } from 'lucide-react';
import { weekLabel } from '../../utils/forecast.js';
import { cx } from '../../utils/format.js';

const C = { green: '#2F8A57', fill: '#2F8A57', grey: '#6B716C', red: '#C8463C', redZone: '#C8463C', line: '#E6E4DE', ink: '#23382B' };
const AXIS_TICK = { fill: C.grey, fontSize: 12, fontFamily: 'Red Hat Text' };
// A week counts as "close to the buffer" when it is less than this far above it (same scale as the card's weeks).
const NEAR_BUFFER = 8;
const BUFFER_FACT = 'Safety buffer';

const SERIES = {
  left: { label: 'If you swipe left', color: C.grey },
  right: { label: 'If you swipe right', color: C.green },
};

function status(value, buffer) {
  if (value < buffer) return { text: 'Under the buffer', tone: 'text-status-red' };
  if (value < buffer + NEAR_BUFFER) return { text: 'Close to the buffer', tone: 'text-status-amber' };
  return { text: 'Above the buffer', tone: 'text-status-green' };
}

function lowestIndex(values) {
  return values.reduce((low, v, i) => (v < values[low] ? i : low), 0);
}

function WeekTooltip({ active, payload, buffer }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="min-w-[200px] rounded-2xl bg-surface p-3 shadow-card ring-1 ring-line">
      <p className="t-overline text-text-muted">{row.label}</p>
      {['left', 'right'].map((side) => {
        const s = status(row[side], buffer);
        return (
          <p key={side} className="mt-1 flex items-center justify-between gap-3 t-small">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ background: SERIES[side].color }} />
              {SERIES[side].label}
            </span>
            <span className={cx('font-semibold', s.tone)}>{s.text}</span>
          </p>
        );
      })}
    </div>
  );
}

/** Small chip next to a point of the chart (SVG foreignObject, like on the main forecast). */
function PointLabel({ viewBox, text, tone, above }) {
  if (!viewBox) return null;
  const tones = { red: 'bg-status-red-soft text-status-red', green: 'bg-status-green-soft text-status-green' };
  return (
    <foreignObject x={viewBox.x - 70} y={above ? viewBox.y - 36 : viewBox.y + 10} width={140} height={28} style={{ overflow: 'visible' }}>
      <span className="flex justify-center">
        <span className={cx('whitespace-nowrap rounded-full px-2.5 py-1 text-[12px] font-semibold shadow-soft', tones[tone])}>{text}</span>
      </span>
    </foreignObject>
  );
}

function Legend({ bufferText }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 t-small text-text-muted">
      <span className="flex items-center gap-1.5">
        <span className="h-[3px] w-5 rounded-full" style={{ background: C.green }} /> {SERIES.right.label}
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-0 w-5 border-t-[3px] border-dashed" style={{ borderColor: C.grey }} /> {SERIES.left.label}
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-3 w-3 rounded-[3px] bg-status-red/20" /> {bufferText}
      </span>
    </div>
  );
}

/**
 * Cash over the next 8 weeks for both decisions of a card, shown in the large card view.
 * The weeks come from the card's engine data (`back.weeks` / `weeksIfApproved`, relative to `bufferLevel`), so the
 * chart shows dates and where the cash is against the buffer, not amounts; the amounts are in the facts above.
 */
export default function CardForecast({ card, className }) {
  const { back } = card;
  const buffer = back.bufferLevel;
  const left = back.weeksIfDeclined || back.weeks;
  const right = back.weeksIfApproved;
  const bufferFact = back.facts?.find(([k]) => k === BUFFER_FACT)?.[1];
  const bufferText = bufferFact ? `Under the safety buffer (${bufferFact})` : 'Under the safety buffer';

  const rows = useMemo(() => left.map((v, i) => ({ week: i, label: weekLabel(i), left: v, right: right[i] })), [left, right]);
  const lowLeft = lowestIndex(left);
  const lowRight = lowestIndex(right);
  const min = Math.min(...left, ...right, buffer);
  const max = Math.max(...left, ...right, buffer);
  const pad = Math.max(6, (max - min) * 0.15);
  const domain = [min - pad, max + pad];
  const lowLeftStatus = status(left[lowLeft], buffer);
  const lowRightStatus = status(right[lowRight], buffer);

  return (
    <section className={cx('card flex flex-col gap-3', className)} aria-label="Cash in the next 8 weeks">
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-green-100 text-green-700">
          <TrendingUp className="h-5 w-5" strokeWidth={1.8} />
        </span>
        <div className="min-w-0">
          <h2 className="t-title">Cash in the next 8 weeks</h2>
          <p className="t-small text-text-muted">
            Lowest week if you swipe left: <b className={lowLeftStatus.tone}>{rows[lowLeft].label} · {lowLeftStatus.text.toLowerCase()}</b>.{' '}
            If you swipe right: <b className={lowRightStatus.tone}>{rows[lowRight].label} · {lowRightStatus.text.toLowerCase()}</b>.
          </p>
        </div>
      </div>
      <Legend bufferText={bufferText} />

      <div className="h-[220px] w-full sm:h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 40, right: 16, bottom: 4, left: 16 }}>
            <defs>
              <linearGradient id="cardFcRight" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={C.fill} stopOpacity={0.22} />
                <stop offset="100%" stopColor={C.fill} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke={C.line} />
            <ReferenceArea y1={domain[0]} y2={buffer} fill={C.redZone} fillOpacity={0.08} ifOverflow="hidden" />
            <XAxis dataKey="week" type="number" domain={[0, rows.length - 1]} ticks={rows.map((r) => r.week)} tickFormatter={(w) => rows[w]?.label} interval="preserveStartEnd" minTickGap={18} tickLine={false} axisLine={false} tick={AXIS_TICK} dy={6} />
            <YAxis hide domain={domain} />
            <Tooltip content={<WeekTooltip buffer={buffer} />} cursor={{ stroke: C.ink, strokeOpacity: 0.2, strokeDasharray: '3 3' }} />
            <ReferenceLine y={buffer} stroke={C.red} strokeOpacity={0.6} strokeDasharray="4 4" label={{ value: 'Safety buffer', position: 'insideBottomLeft', fill: C.red, fontSize: 12, dy: 14 }} />
            <Area dataKey="right" stroke="none" fill="url(#cardFcRight)" isAnimationActive={false} />
            <Line dataKey="left" stroke={C.grey} strokeWidth={2.5} strokeDasharray="6 5" dot={{ r: 3, fill: C.grey, strokeWidth: 0 }} isAnimationActive={false} />
            <Line dataKey="right" stroke={C.green} strokeWidth={3} dot={{ r: 3.5, fill: C.green, strokeWidth: 0 }} activeDot={{ r: 5 }} isAnimationActive={false} />
            <ReferenceDot x={lowLeft} y={left[lowLeft]} r={6} fill={left[lowLeft] < buffer ? C.red : C.grey} stroke="#fff" strokeWidth={2.5} label={<PointLabel text={`Lowest · ${rows[lowLeft].label}`} tone={left[lowLeft] < buffer ? 'red' : 'green'} above={false} />} />
            {lowRight !== lowLeft || right[lowRight] !== left[lowLeft] ? (
              <ReferenceDot x={lowRight} y={right[lowRight]} r={6} fill={C.green} stroke="#fff" strokeWidth={2.5} label={<PointLabel text={`Lowest · ${rows[lowRight].label}`} tone={right[lowRight] < buffer ? 'red' : 'green'} above />} />
            ) : null}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="t-small text-text-muted">Weeks start on Monday. The amounts are in the facts above; tap a week to compare both decisions.</p>
    </section>
  );
}
