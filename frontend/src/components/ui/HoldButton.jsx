import React, { useEffect, useRef, useState } from 'react';
import { cx } from '../../utils/format.js';

/**
 * Button that confirms only after being held for `holdMs` (friction against accidental decisions).
 * Releasing early cancels. Works with mouse, touch and keyboard (hold Space or Enter).
 * `onProgress(p)` reports 0..1 while held, so the card can show the same progress.
 */
export default function HoldButton({ holdMs = 600, onConfirm, onProgress, onPressChange, children, className, fillClassName = 'bg-black/15', label, disabled }) {
  const [progress, setProgress] = useState(0);
  const raf = useRef(0);
  const start = useRef(0);
  const active = useRef(false);

  const report = (p) => {
    setProgress(p);
    onProgress?.(p);
  };

  // `release`: the finger or key went up (may confirm); otherwise the press was cancelled.
  const stop = (release = false) => {
    if (!active.current) return;
    active.current = false;
    cancelAnimationFrame(raf.current);
    report(0);
    onPressChange?.(false);
    if (release === true && performance.now() - start.current >= holdMs) onConfirm();
  };

  const tick = (now) => {
    if (!active.current) return;
    const p = Math.min(1, (now - start.current) / holdMs);
    report(p);
    if (p >= 1) {
      active.current = false;
      navigator.vibrate?.(15);
      onPressChange?.(false);
      onConfirm();
      requestAnimationFrame(() => report(0));
      return;
    }
    raf.current = requestAnimationFrame(tick);
  };

  const begin = () => {
    if (disabled || active.current) return;
    active.current = true;
    start.current = performance.now();
    onPressChange?.(true);
    raf.current = requestAnimationFrame(tick);
  };

  useEffect(() => () => cancelAnimationFrame(raf.current), []);

  return (
    <button
      type="button"
      disabled={disabled}
      aria-label={label}
      onPointerDown={(e) => {
        e.preventDefault();
        begin();
      }}
      onPointerUp={() => stop(true)}
      onPointerLeave={() => stop()}
      onPointerCancel={() => stop()}
      onContextMenu={(e) => e.preventDefault()}
      onKeyDown={(e) => {
        if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) {
          e.preventDefault();
          begin();
        }
      }}
      onKeyUp={(e) => (e.key === ' ' || e.key === 'Enter') && stop(true)}
      onBlur={() => stop()}
      className={cx('relative inline-flex touch-none select-none items-center justify-center overflow-hidden disabled:opacity-50', className)}
    >
      <span className={cx('pointer-events-none absolute inset-y-0 left-0', fillClassName)} style={{ width: `${progress * 100}%` }} aria-hidden />
      <span className="relative flex items-center gap-2">{children}</span>
    </button>
  );
}
