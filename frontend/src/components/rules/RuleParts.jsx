import React from 'react';
import { Minus, Plus } from 'lucide-react';
import { cx, formatPLN } from '../../utils/format.js';

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

/** Amount in PLN with a slider. */
export function Amount({ value, onChange, min, max, step, label, hint, disabled }) {
  return (
    <div className={cx('flex flex-col gap-1.5', disabled && 'opacity-50')}>
      <div className="flex items-center justify-between gap-3">
        <span className="t-small text-text-muted">{label}</span>
        <span className="t-mono">{formatPLN(value)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label={label}
        className="h-8 w-full cursor-pointer accent-green-700"
      />
      {hint && <p className="t-small text-text-muted">{hint}</p>}
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
