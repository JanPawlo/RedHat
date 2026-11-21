import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Ban, Bell, CheckCheck, Info, SlidersHorizontal, TriangleAlert, X } from 'lucide-react';
import { useAppState } from '../../state/AppState.jsx';
import { cx } from '../../utils/format.js';

const TYPES = {
  warning: { bg: 'bg-status-amber-soft', fg: 'text-status-amber', icon: TriangleAlert },
  error: { bg: 'bg-status-red-soft', fg: 'text-status-red', icon: Ban },
  success: { bg: 'bg-status-green-soft', fg: 'text-status-green', icon: CheckCheck },
  info: { bg: 'bg-status-blue-soft', fg: 'text-status-blue', icon: Bell },
  neutral: { bg: 'bg-subtle', fg: 'text-text-muted', icon: Info },
};

/** One alert row (Figma: Alert toast · Type). */
export function AlertToast({ alert, onDismiss, onAction, compact = false, className }) {
  const t = TYPES[alert.type] || TYPES.neutral;
  const IconCmp = t.icon;
  return (
    // Phones: icon, text and close on one row, the action button under the text. From sm up: everything on one row.
    <div className={cx('flex flex-wrap items-start gap-x-3 gap-y-2 rounded-[22px] px-4 py-3.5 sm:flex-nowrap sm:items-center sm:gap-4', t.bg, className)}>
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[14px] bg-white/85">
        <IconCmp className={cx('h-[22px] w-[22px]', t.fg)} strokeWidth={1.8} />
      </span>
      {/* Phones: the text takes the row (minus icon, close and gaps), so the action wraps below it. */}
      <div className="min-w-0 flex-1 basis-[calc(100%-6rem)] sm:basis-auto">
        <p className={cx('t-title', compact && 'truncate')}>{alert.title}</p>
        {alert.message && <p className={cx('t-small text-text-muted', compact && 'truncate')}>{alert.message}</p>}
      </div>
      {alert.action && onAction && (
        <button type="button" onClick={() => onAction(alert)} className="order-last ml-14 shrink-0 rounded-full bg-surface px-3.5 py-2 t-small transition-colors hover:bg-subtle sm:order-none sm:ml-0">
          {alert.action}
        </button>
      )}
      {onDismiss && (
        <button type="button" onClick={() => onDismiss(alert.id)} aria-label="Dismiss alert" className="shrink-0 rounded-full p-1 text-text-muted transition-colors hover:bg-white/60 hover:text-text">
          <X className="h-[18px] w-[18px]" />
        </button>
      )}
    </div>
  );
}

function useAlertAction() {
  const navigate = useNavigate();
  return (alert) => {
    if (alert.to?.startsWith('/#')) {
      navigate('/');
      requestAnimationFrame(() => document.getElementById(alert.to.slice(2))?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    } else if (alert.to) navigate(alert.to);
  };
}

/** Notifications list, opened from the bell in the top right corner. */
export function AlertsPanel({ open, onClose }) {
  const { alerts, dismissAlert, markAllRead } = useAppState();
  const act = useAlertAction();
  const unread = alerts.filter((a) => a.unread).length;

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            key="dim"
            className="fixed inset-0 z-40 bg-ink/35"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.section
            key="panel"
            role="dialog"
            aria-label="Notifications"
            initial={{ opacity: 0, y: -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ type: 'spring', stiffness: 380, damping: 32 }}
            className="fixed inset-x-3 top-3 z-50 flex max-h-[calc(100dvh-24px)] flex-col gap-3 rounded-card bg-surface p-4 shadow-card sm:inset-x-auto sm:right-6 sm:top-24 sm:max-h-[calc(100dvh-120px)] sm:w-[640px] sm:max-w-[calc(100vw-48px)] sm:p-5"
          >
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-status-red font-display text-lg font-black text-white">!</span>
              <div className="min-w-0 flex-1">
                <p className="t-title">Notifications</p>
                <p className="t-small text-text-muted">{unread} new · {alerts.length} in total · newest first</p>
              </div>
              <button type="button" onClick={markAllRead} aria-label="Mark all read" title="Mark all read" className="flex items-center gap-2 rounded-full px-2.5 py-2 t-small ring-1 ring-inset ring-line hover:bg-subtle sm:px-3.5">
                <CheckCheck className="h-4 w-4" /> <span className="hidden sm:inline">Mark all read</span>
              </button>
              <button type="button" onClick={onClose} aria-label="Close notifications" className="rounded-full p-1.5 text-text-muted hover:bg-subtle hover:text-text">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="-mr-2 flex flex-col gap-3 overflow-y-auto pr-2 scrollbar-thin">
              {alerts.length === 0 && <p className="py-10 text-center t-body text-text-muted">No notifications. All quiet.</p>}
              {alerts.map((a) => (
                <div key={a.id} className="relative">
                  {a.unread && <span className="absolute -left-1 top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-status-red" aria-label="unread" />}
                  <AlertToast alert={a} onDismiss={dismissAlert} onAction={(x) => { onClose(); act(x); }} />
                </div>
              ))}
            </div>
            <button type="button" onClick={() => { onClose(); act({ to: '/rules' }); }} className="flex items-center gap-2 px-1 py-1 t-small text-text-muted hover:text-text">
              <SlidersHorizontal className="h-4 w-4" /> Alert settings · what should interrupt me
            </button>
          </motion.section>
        </>
      )}
    </AnimatePresence>
  );
}
