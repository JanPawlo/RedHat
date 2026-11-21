import React from 'react';
import { cx } from '../../utils/format.js';
import Icon from './Icon.jsx';

// ---------- Chip (Figma: Chip · Tone) ----------
const CHIP_TONES = {
  green: 'bg-status-green-soft text-status-green',
  red: 'bg-status-red-soft text-status-red',
  amber: 'bg-status-amber-soft text-status-amber',
  blue: 'bg-status-blue-soft text-status-blue',
  neutral: 'bg-subtle text-text-muted',
  dark: 'bg-green-900 text-white',
};
const DOT_TONES = {
  green: 'bg-status-green', red: 'bg-status-red', amber: 'bg-status-amber', blue: 'bg-status-blue', neutral: 'bg-text-muted', dark: 'bg-white',
};

export function Chip({ tone = 'neutral', dot = true, children, className }) {
  return (
    <span className={cx('inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 t-small', CHIP_TONES[tone], className)}>
      {dot && <span className={cx('h-1.5 w-1.5 rounded-full', DOT_TONES[tone])} />}
      {children}
    </span>
  );
}

export const TONE_TEXT = {
  green: 'text-status-green', red: 'text-status-red', amber: 'text-status-amber', blue: 'text-status-blue', neutral: 'text-text-muted',
};
export const TONE_DOT = DOT_TONES;

// ---------- Button ----------
const BTN_KINDS = {
  primary: 'bg-green-700 text-white hover:bg-green-900',
  dark: 'bg-green-900 text-white hover:bg-ink',
  soft: 'bg-green-100 text-green-700 hover:bg-green-200',
  ghost: 'bg-surface text-text ring-1 ring-inset ring-line hover:bg-subtle',
  danger: 'bg-status-red-soft text-status-red hover:brightness-95',
};

export function Button({ kind = 'primary', icon: IconCmp, iconRight: IconRight, children, className, size = 'md', ...props }) {
  return (
    <button
      type="button"
      className={cx(
        'inline-flex select-none items-center justify-center gap-2 rounded-full t-small transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50',
        size === 'sm' ? 'px-3.5 py-2' : 'px-[18px] py-[11px]',
        BTN_KINDS[kind],
        className,
      )}
      {...props}
    >
      {IconCmp && <IconCmp className="h-4 w-4" strokeWidth={2} />}
      {children}
      {IconRight && <IconRight className="h-4 w-4" strokeWidth={2} />}
    </button>
  );
}

// ---------- Icon circle ----------
export function IconCircle({ name, icon: IconCmp, size = 44, tone = 'green', className }) {
  const tones = {
    green: 'bg-green-100 text-green-700',
    solid: 'bg-green-700 text-white',
    white: 'bg-surface text-text',
    red: 'bg-status-red-soft text-status-red',
    amber: 'bg-status-amber-soft text-status-amber',
    blue: 'bg-status-blue-soft text-status-blue',
  };
  const iconSize = Math.round(size * 0.45);
  return (
    <span className={cx('inline-flex shrink-0 items-center justify-center rounded-full', tones[tone], className)} style={{ width: size, height: size }}>
      {IconCmp ? <IconCmp style={{ width: iconSize, height: iconSize }} strokeWidth={1.8} /> : <Icon name={name} style={{ width: iconSize, height: iconSize }} />}
    </span>
  );
}

// ---------- Segmented control ----------
export function Segmented({ options, value, onChange, className, onSurface = false }) {
  return (
    <div className={cx('inline-flex gap-0.5 rounded-full p-1', onSurface ? 'bg-surface' : 'bg-subtle', className)} role="tablist">
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(opt.value)}
            className={cx('rounded-full px-3.5 py-1.5 t-small transition-colors', active ? 'bg-green-700 text-white' : 'text-text-muted hover:text-text')}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

// ---------- Filter pills ----------
export function Pill({ active, children, onClick, muted }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        'shrink-0 whitespace-nowrap rounded-full px-4 py-2 t-small transition-colors',
        active ? 'bg-green-900 text-white' : muted ? 'bg-subtle text-text hover:bg-line' : 'bg-surface text-text hover:bg-green-100',
      )}
    >
      {children}
    </button>
  );
}

// ---------- Progress bar ----------
export function Bar({ pct, color = 'bg-green-700', track = 'bg-subtle', height = 8 }) {
  return (
    <div className={cx('w-full overflow-hidden rounded-full', track)} style={{ height }}>
      <div className={cx('h-full rounded-full transition-[width] duration-500', color)} style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
    </div>
  );
}

// ---------- AI insight strip ----------
export function Insight({ children, tone = 'green', icon: IconCmp }) {
  const tones = { green: 'bg-green-100', amber: 'bg-status-amber-soft', blue: 'bg-status-blue-soft' };
  const iconTone = { green: 'text-green-700', amber: 'text-status-amber', blue: 'text-status-blue' };
  return (
    <div className={cx('flex items-center gap-2.5 rounded-2xl px-3.5 py-3', tones[tone])}>
      {IconCmp && <IconCmp className={cx('h-[18px] w-[18px] shrink-0', iconTone[tone])} strokeWidth={1.8} />}
      <p className="t-small text-text">{children}</p>
    </div>
  );
}

// ---------- Page header ----------
export function PageHeader({ title, subtitle, children }) {
  return (
    <header className="flex flex-wrap items-center gap-3">
      <div className="min-w-0 flex-1">
        <h1 className="t-display-l">{title}</h1>
        {subtitle && <p className="mt-0.5 t-small text-text-muted">{subtitle}</p>}
      </div>
      {children}
    </header>
  );
}
