import React, { useMemo } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { CHART_COLORS, CHART_HEIGHT, FORECAST_HORIZONS, SCENARIO, TOOLTIP_DRIVERS_LIMIT } from '../../const/forecast.js';
import { formatCompactMoney, formatMoney, formatShortDate, formatSignedMoney } from '../../utils/format.js';

function balanceAt(days, index) {
  return days ? Number(days[index].balance) : null;
}

function buildRows(forecast, preview) {
  const base = forecast.scenarios[SCENARIO.base].days;
  const low = forecast.scenarios[SCENARIO.pessimistic].days;
  const high = forecast.scenarios[SCENARIO.optimistic].days;
  const after = forecast.after_decisions?.days;
  const previewDays = preview?.simulated.scenarios[SCENARIO.base].days;
  const opening = Number(forecast.opening_balance);

  const start = {
    day: forecast.as_of,
    baseline: opening,
    band: [opening, opening],
    after: after ? opening : null,
    preview: previewDays ? opening : null,
    drivers: [],
  };

  return [
    start,
    ...base.map((day, index) => ({
      day: day.day,
      baseline: Number(day.balance),
      band: [balanceAt(low, index), balanceAt(high, index)],
      after: balanceAt(after, index),
      preview: balanceAt(previewDays, index),
      drivers: (after ? after[index] : day).drivers,
    })),
  ];
}

function ChartTooltip({ active, payload, currency }) {
  if (!active || !payload?.length) return null;

  const row = payload[0].payload;
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-xs max-w-xs">
      <p className="font-semibold text-slate-800 mb-1">{formatShortDate(row.day)}</p>
      <p className="text-slate-500">Do nothing: {formatMoney(row.baseline, currency)}</p>
      {row.after !== null && <p className="text-indigo-700">After decisions: {formatMoney(row.after, currency)}</p>}
      {row.preview !== null && <p className="text-emerald-700">If you approve: {formatMoney(row.preview, currency)}</p>}
      {row.drivers.length > 0 && (
        <ul className="mt-2 space-y-0.5 border-t border-slate-100 pt-2">
          {row.drivers.slice(0, TOOLTIP_DRIVERS_LIMIT).map((driver) => (
            <li key={driver.label} className="flex justify-between gap-3">
              <span className="text-slate-600 truncate">{driver.label}</span>
              <span className={Number(driver.amount) < 0 ? 'text-red-600' : 'text-emerald-600'}>
                {formatSignedMoney(driver.amount, currency)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function ForecastChart({ forecast, preview, previewRisky, horizon, onHorizonChange }) {
  const rows = useMemo(() => buildRows(forecast, preview), [forecast, preview]);
  const buffer = Number(forecast.safety_buffer);
  const previewColor = previewRisky ? CHART_COLORS.previewRisk : CHART_COLORS.previewSafe;

  return (
    <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-slate-800">Cash forecast</h2>
          <p className="text-xs text-slate-500">
            From {formatShortDate(forecast.as_of)} (last booked transaction). Band = pessimistic to optimistic revenue.
          </p>
        </div>
        <div className="flex rounded-lg border border-slate-200 overflow-hidden text-xs">
          {FORECAST_HORIZONS.map((days) => (
            <button
              key={days}
              type="button"
              onClick={() => onHorizonChange(days)}
              className={`px-3 py-1.5 ${days === horizon ? 'bg-indigo-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
            >
              {days} days
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <ComposedChart data={rows} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="day" tickFormatter={formatShortDate} tick={{ fontSize: 11 }} minTickGap={24} />
          <YAxis tickFormatter={formatCompactMoney} tick={{ fontSize: 11 }} width={48} />
          <Tooltip content={<ChartTooltip currency={forecast.currency} />} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Area dataKey="band" name="Scenario range" stroke="none" fill={CHART_COLORS.band} isAnimationActive={false} />
          <ReferenceLine y={buffer} stroke={CHART_COLORS.buffer} strokeDasharray="6 4" label={{ value: 'Safety buffer', fontSize: 11, fill: CHART_COLORS.buffer, position: 'insideTopRight' }} />
          <ReferenceLine y={0} stroke={CHART_COLORS.zero} />
          <Line dataKey="baseline" name="Do nothing" stroke={CHART_COLORS.baseline} strokeWidth={2} dot={false} isAnimationActive={false} />
          {forecast.after_decisions && (
            <Line dataKey="after" name="After your decisions" stroke={CHART_COLORS.afterDecisions} strokeWidth={2.5} strokeDasharray="8 4" dot={false} isAnimationActive={false} />
          )}
          {preview && (
            <Line dataKey="preview" name="If you approve this card" stroke={previewColor} strokeWidth={2} strokeDasharray="2 3" dot={false} isAnimationActive={false} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
