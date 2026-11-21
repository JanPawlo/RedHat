import React from 'react';
import { CalendarClock, Gauge, ShieldCheck, Wallet } from 'lucide-react';
import { PERCENT, SCENARIO } from '../../const/forecast.js';
import { formatMoney, formatShortDate, formatSignedMoney } from '../../utils/format.js';

function currentPlan(forecast) {
  return {
    scenario: forecast.after_decisions || forecast.scenarios[SCENARIO.base],
    confidence: forecast.after_decisions_confidence ?? forecast.confidence,
  };
}

function Tile({ icon: Icon, label, value, hint, tone = 'text-slate-900' }) {
  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-500">{label}</span>
        <Icon className="w-4 h-4 text-slate-400" />
      </div>
      <p className={`mt-3 text-2xl font-bold ${tone}`}>{value}</p>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </div>
  );
}

export default function IndicatorTiles({ forecast }) {
  const { scenario, confidence } = currentPlan(forecast);
  const indicators = scenario.indicators;
  const baseLowest = Number(forecast.scenarios[SCENARIO.base].indicators.lowest_balance);
  const lowest = Number(indicators.lowest_balance);
  const buffer = Number(forecast.safety_buffer);
  const breach = indicators.first_below_buffer_date;
  const decisionsEffect = lowest - baseLowest;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <Tile
        icon={Wallet}
        label="Balance today"
        value={formatMoney(forecast.opening_balance, forecast.currency)}
        hint={`Safety buffer ${formatMoney(buffer, forecast.currency)}`}
      />
      <Tile
        icon={ShieldCheck}
        label="Lowest balance"
        value={formatMoney(lowest, forecast.currency)}
        tone={lowest < buffer ? 'text-red-600' : 'text-indigo-600'}
        hint={`On ${formatShortDate(indicators.lowest_balance_date)}${
          forecast.after_decisions ? ` · decisions ${formatSignedMoney(decisionsEffect, forecast.currency)}` : ''
        }`}
      />
      <Tile
        icon={CalendarClock}
        label="Liquidity gap"
        value={breach ? `in ${indicators.days_to_buffer_breach} days` : 'None'}
        tone={breach ? 'text-red-600' : 'text-emerald-600'}
        hint={breach ? `Below buffer on ${formatShortDate(breach)}` : `Above buffer for ${forecast.horizon_days} days`}
      />
      <Tile
        icon={Gauge}
        label="Confidence"
        value={`${Math.round(Number(confidence) * PERCENT)}%`}
        tone={Number(confidence) < 0.5 ? 'text-amber-600' : 'text-emerald-600'}
        hint="Revenue scenarios that stay above the buffer"
      />
    </div>
  );
}
