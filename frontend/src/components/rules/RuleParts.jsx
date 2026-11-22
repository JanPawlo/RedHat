import React, { useEffect, useState } from 'react';
import { Minus, Plus } from 'lucide-react';
import { cx, formatPLN, getDisplayCurrency } from '../../utils/format.js';

export function Switch({ checked, onChange, label, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cx('relative h-7 w-12 shrink-0 rounded-full transition-colors disabled:opacity-60', checked ? 'bg-green-700' : 'bg-line')}
    >
      <span className={cx('absolute left-0 top-1 h-5 w-5 rounded-full bg-surface shadow transition-transform', checked ? 'translate-x-6' : 'translate-x-1')} />
    </button>
  );
}

/** Keeps a typed amount inside the allowed range; an empty or invalid entry keeps the previous value. */
function clampAmount(text, previous, min, max) {
  const number = Number(String(text).replace(/[\s,]/g, ''));
  if (!text || !Number.isFinite(number)) return previous;
  return Math.min(max, Math.max(min, Math.round(number)));
}

/** Amount (in the data's currency) typed into a box. The value is saved on Enter or when the box loses focus, kept between min and max. */
export function Amount({ value, onChange, min, max, step, label, hint, disabled }) {
  const [draft, setDraft] = useState(String(value));

  useEffect(() => setDraft(String(value)), [value]);

  const commit = () => {
    const next = clampAmount(draft, value, min, max);
    setDraft(String(next));
    if (next !== value) onChange(next);
  };

  return (
    <div className={cx('flex flex-col gap-1.5', disabled && 'opacity-50')}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="t-small text-text-muted">{label}</span>
        <label className="flex items-center gap-2 rounded-full bg-subtle py-1.5 pl-4 pr-3 focus-within:ring-2 focus-within:ring-green-500">
          <input
            type="number"
            inputMode="numeric"
            min={min}
            max={max}
            step={step}
            value={draft}
            disabled={disabled}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
            aria-label={label}
            className="w-28 bg-transparent text-right t-mono outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          />
          <span className="t-small text-text-muted">{getDisplayCurrency()}</span>
        </label>
      </div>
      <p className="t-small text-text-muted">
        {formatPLN(min)} – {formatPLN(max)}
        {hint && ` · ${hint}`}
      </p>
    </div>
  );
}

/** Small number with − / + buttons (days, percent). */
export function Stepper({ value, onChange, min, max, step = 1, unit, label }) {
  const set = (v) => onChange(Math.min(max, Math.max(min, v)));
  const btn = 'flex h-8 w-8 items-center justify-center rounded-full bg-subtle text-text-muted hover:bg-line hover:text-text disabled:opacity-40';
  return (
    <div className="flex shrink-0 items-center gap-2" role="group" aria-label={label}>
      <button type="button" className={btn} onClick={() => set(value - step)} disabled={value <= min} aria-label={`Less: ${label}`}>
        <Minus className="h-4 w-4" />
      </button>
      <span className="min-w-[72px] text-center t-body-m">
        {value} {unit}
      </span>
      <button type="button" className={btn} onClick={() => set(value + step)} disabled={value >= max} aria-label={`More: ${label}`}>
        <Plus className="h-4 w-4" />
      </button>
    </div>
  );
}

/** A group of rules with a short heading. */
export function Section({ title, text, right, children }) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3 px-1">
        <div className="min-w-0">
          <h2 className="t-title">{title}</h2>
          {text && <p className="t-small text-text-muted">{text}</p>}
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

/** One row inside a card: title, rule ID, short text and a control on the right (below on phones). */
export function RuleRow({ ruleId, title, text, control, muted }) {
  return (
    <div className={cx('flex flex-col gap-3 py-3.5 sm:flex-row sm:items-center sm:justify-between', muted && 'opacity-60')}>
      <div className="min-w-0">
        <p className="t-body-m">
          {title} <span className="ml-1 t-mono text-[11px] text-text-muted">{ruleId}</span>
        </p>
        {text && <p className="t-small text-text-muted">{text}</p>}
      </div>
      {control}
    </div>
  );
}
