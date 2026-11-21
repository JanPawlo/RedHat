import React, { useEffect } from 'react';
import { Bot, Check, RotateCcw, ThumbsDown, ThumbsUp, X } from 'lucide-react';
import { ACTION_STATUS } from '../../const/api.js';
import { CARD_KEYS, PERCENT, SCENARIO } from '../../const/forecast.js';
import { formatMoney, formatShortDate, formatSignedMoney } from '../../utils/format.js';

const KEY_APPROVE = 'ArrowRight';
const KEY_REJECT = 'ArrowLeft';

export function previewEffect(preview) {
  if (!preview) return null;

  const before = preview.baseline;
  const after = preview.simulated;
  const afterIndicators = after.scenarios[SCENARIO.base].indicators;

  const change = Number(preview.lowest_balance_change);
  const confidenceBefore = Number(before.confidence);
  const confidenceAfter = Number(after.confidence);

  return {
    change,
    confidenceBefore,
    confidenceAfter,
    breachDate: afterIndicators.first_below_buffer_date,
    lowestAfter: afterIndicators.lowest_balance,
    engineSaysYes: change >= 0 && confidenceAfter >= confidenceBefore && !afterIndicators.first_below_buffer_date,
  };
}

function percent(value) {
  return `${Math.round(value * PERCENT)}%`;
}

function hasCashChanges(card) {
  const changes = card.impact_simulation?.[CARD_KEYS.cashChanges];
  return Array.isArray(changes) && changes.length > 0;
}

function EffectBox({ effect, hasCash, currency }) {
  if (!hasCash) return <p className="text-xs text-slate-500">This card does not change cash in the forecast.</p>;
  if (!effect) return <p className="text-xs text-slate-400">Calculating the effect…</p>;

  return (
    <div className="grid grid-cols-3 gap-3 text-xs">
      <div className="p-3 rounded-lg bg-slate-50">
        <p className="text-slate-500">Lowest balance</p>
        <p className={`text-sm font-semibold ${effect.change < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
          {formatSignedMoney(effect.change, currency)}
        </p>
        <p className="text-slate-400">→ {formatMoney(effect.lowestAfter, currency)}</p>
      </div>
      <div className="p-3 rounded-lg bg-slate-50">
        <p className="text-slate-500">Confidence</p>
        <p className="text-sm font-semibold text-slate-800">
          {percent(effect.confidenceBefore)} → {percent(effect.confidenceAfter)}
        </p>
      </div>
      <div className={`p-3 rounded-lg ${effect.breachDate ? 'bg-red-50' : 'bg-emerald-50'}`}>
        <p className="text-slate-500">Safety buffer</p>
        <p className={`text-sm font-semibold ${effect.breachDate ? 'text-red-600' : 'text-emerald-700'}`}>
          {effect.breachDate ? `Broken ${formatShortDate(effect.breachDate)}` : 'Holds'}
        </p>
      </div>
    </div>
  );
}

function CurrentCard({ card, effect, busy, position, total, onApprove, onReject }) {
  const labels = card.impact_simulation || {};
  const hasCash = hasCashChanges(card);

  return (
    <div className="bg-gradient-to-br from-indigo-50 to-white p-6 rounded-xl border border-indigo-100 shadow-sm space-y-4">
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span className="uppercase tracking-wide">{card.agent_type.replaceAll('_', ' ')}</span>
        <span>
          Card {position} of {total}
        </span>
      </div>

      <div className="flex items-start space-x-3">
        <div className="p-2.5 bg-indigo-600 text-white rounded-xl">
          <Bot className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <h3 className="text-base font-semibold text-slate-900">{card.title}</h3>
          <p className="mt-1 text-sm text-slate-600">{card.trigger_reason}</p>
          <p className="mt-2 text-sm text-slate-500">{card.explanation}</p>
        </div>
      </div>

      <EffectBox effect={effect} hasCash={hasCash} currency={card.currency} />

      {hasCash && effect && (
        <p className="text-xs font-medium text-slate-600">
          Engine: I'd swipe {effect.engineSaysYes ? 'right' : 'left'} · {percent(effect.confidenceAfter)} of scenarios stay above the buffer
        </p>
      )}

      <div className="flex items-center gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={onReject}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-white hover:bg-slate-50 disabled:opacity-60 text-slate-700 border border-slate-300 text-sm font-semibold rounded-lg"
        >
          <ThumbsDown className="w-4 h-4" /> {labels[CARD_KEYS.swipeLeft] || 'Reject'}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onApprove}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-semibold rounded-lg shadow-sm"
        >
          <ThumbsUp className="w-4 h-4" /> {labels[CARD_KEYS.swipeRight] || 'Approve'}
        </button>
      </div>
      <p className="text-center text-[11px] text-slate-400">Keyboard: ← reject · → approve</p>
    </div>
  );
}

function DecidedList({ cards, busyCardId, onUndo }) {
  if (cards.length === 0) return null;

  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-800 mb-3">Your decisions</h3>
      <ul className="space-y-2">
        {cards.map((card) => {
          const approved = card.status === ACTION_STATUS.approved;
          return (
            <li key={card.id} className="flex items-center justify-between gap-3 text-sm">
              <span className="flex items-center gap-2 min-w-0">
                {approved ? (
                  <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                ) : (
                  <X className="w-4 h-4 text-slate-400 shrink-0" />
                )}
                <span className={`truncate ${approved ? 'text-slate-800' : 'text-slate-400 line-through'}`}>{card.title}</span>
              </span>
              <button
                type="button"
                disabled={busyCardId === card.id}
                onClick={() => onUndo(card.id)}
                className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 disabled:opacity-60 shrink-0"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Undo
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function DecisionDeck({ current, pending, decided, effect, busyCardId, onApprove, onReject, onUndo }) {
  const busy = Boolean(current && busyCardId === current.id);

  useEffect(() => {
    if (!current) return undefined;

    const handleKey = (event) => {
      if (busy || event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
      if (event.key === KEY_APPROVE) onApprove(current.id);
      if (event.key === KEY_REJECT) onReject(current.id);
    };

    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [current, busy, onApprove, onReject]);

  return (
    <div className="space-y-4">
      {current ? (
        <CurrentCard
          card={current}
          effect={effect}
          busy={busy}
          position={decided.length + 1}
          total={decided.length + pending.length}
          onApprove={() => onApprove(current.id)}
          onReject={() => onReject(current.id)}
        />
      ) : (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm text-sm text-slate-500">
          No cards waiting. Undo a decision below to see its effect again.
        </div>
      )}
      <DecidedList cards={decided} busyCardId={busyCardId} onUndo={onUndo} />
    </div>
  );
}
