import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, Check, CheckCheck, Undo2, X } from 'lucide-react';
import { useAppState } from '../../state/AppState.jsx';
import { Chip } from '../ui/primitives.jsx';
import { cx, formatPLN } from '../../utils/format.js';
import { followUpsFor } from './followUps.js';
import { keepOnMainThread } from '../../utils/motion.js';
import { BANK_ORDER_LABEL } from '../../const/mockup.js';

const COPY = {
  approve: {
    tone: 'green',
    title: 'Approved',
    icon: CheckCheck,
    circle: 'bg-green-700 text-white ring-green-200',
  },
  decline: {
    tone: 'neutral',
    title: 'Declined',
    icon: X,
    circle: 'bg-status-red-soft text-status-red ring-status-red-soft/60',
  },
};

/**
 * Shown after every decision: what just happened, whether it was simulated, and optional follow-ups
 * (see followUps.js). Rendered as a centered dialog on desktop and a full-height sheet on phones.
 */
export default function Confirmation() {
  const app = useAppState();
  const { confirmation: entry, closeConfirmation, undoLast, addEntryAction, cards, queue } = app;
  const [done, setDone] = useState([]);

  useEffect(() => setDone([]), [entry?.id]);

  useEffect(() => {
    if (!entry) return undefined;
    const onKey = (e) => e.key === 'Escape' && closeConfirmation();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [entry, closeConfirmation]);

  // The card as it was when the decision was made. After the decision the backend refresh drops it from
  // `cards`, and looking it up again fell back to the short snapshot: the follow-ups vanished a moment later.
  const decided = useRef({ entryId: null, card: null });
  if (entry && decided.current.entryId !== entry.id) {
    decided.current = { entryId: entry.id, card: cards.find((c) => c.id === entry.cardId) || entry.card };
  }
  const card = entry ? decided.current.card : null;
  const look = entry ? COPY[entry.choice] : null;
  const approved = entry?.choice === 'approve';
  const simulated = approved && /SIMULATED/.test(entry.card.resultLabel || '');
  const followUps = approved ? followUpsFor(card) : [];

  const what = !entry
    ? ''
    : approved
      ? entry.card.resultLabel.replace(' · SIMULATED', '')
      : 'Nothing was sent or paid. I will not suggest this again this week.';

  const runFollowUp = (f) => {
    f.run({ card, entry, app });
    addEntryAction(entry.id, f.doneLabel);
    setDone((d) => [...d, f.key]);
  };

  return (
    <AnimatePresence>
      {entry && (
        <motion.div
          key={entry.id}
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirmation-title"
          className="fixed inset-0 z-50 flex items-end justify-center bg-ink/40 backdrop-blur-[2px] sm:items-center sm:p-6"
          onUpdate={keepOnMainThread}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={(e) => e.target === e.currentTarget && closeConfirmation()}
        >
          <motion.div
            onUpdate={keepOnMainThread}
            initial={{ y: 40, scale: 0.98 }}
            animate={{ y: 0, scale: 1 }}
            exit={{ y: 30, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 380, damping: 32 }}
            className="flex max-h-[100dvh] w-full flex-col gap-5 overflow-y-auto rounded-t-[28px] bg-surface p-6 pb-[max(24px,env(safe-area-inset-bottom))] shadow-card sm:max-w-[480px] sm:rounded-card sm:p-8"
          >
            <div className="flex flex-col items-center gap-3 text-center">
              <span className={cx('flex h-20 w-20 items-center justify-center rounded-full ring-[6px]', look.circle)}>
                <look.icon className="h-9 w-9" />
              </span>
              <p className="t-overline text-text-muted">Confirmation</p>
              <h2 id="confirmation-title" className="t-display-l">
                {look.title}: {approved ? entry.card.right : entry.card.left}
              </h2>
              <p className="t-body text-text-muted">{entry.card.title}</p>
            </div>

            <div className="flex flex-col gap-2">
              <p className="t-overline text-text-muted">What happened</p>
              <div className="rounded-[20px] bg-subtle p-4">
                <p className="t-body-m">{what}</p>
                {(simulated || (approved && entry.card.amount)) && (
                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                    {simulated && <Chip tone="blue">{BANK_ORDER_LABEL}</Chip>}
                    {approved && entry.card.amount ? <Chip tone="neutral" dot={false}>{formatPLN(entry.card.amount)}</Chip> : null}
                  </div>
                )}
              </div>
            </div>

            {followUps.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="t-overline text-text-muted">Optional steps</p>
                {followUps.map((f) => {
                  const isDone = done.includes(f.key);
                  return (
                    <button
                      key={f.key}
                      type="button"
                      disabled={isDone}
                      onClick={() => runFollowUp(f)}
                      className={cx(
                        'flex items-center gap-3 rounded-[18px] p-3.5 text-left transition-colors',
                        isDone ? 'bg-status-green-soft' : 'bg-green-100 hover:bg-green-200',
                      )}
                    >
                      <span className={cx('flex h-10 w-10 shrink-0 items-center justify-center rounded-full', isDone ? 'bg-status-green text-white' : 'bg-surface text-green-700')}>
                        {isDone ? <Check className="h-5 w-5" /> : <f.icon className="h-5 w-5" />}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block t-body-m">{isDone ? f.doneLabel : f.label}</span>
                        {!isDone && <span className="block t-small text-text-muted">{f.hint}</span>}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}

            <div className="flex flex-col-reverse gap-2.5 sm:flex-row">
              <button type="button" onClick={undoLast} className="flex flex-1 items-center justify-center gap-2 rounded-full bg-surface px-5 py-3.5 t-small ring-1 ring-inset ring-line hover:bg-subtle">
                <Undo2 className="h-4 w-4" /> Undo
              </button>
              <button type="button" onClick={closeConfirmation} className="flex flex-1 items-center justify-center gap-2 rounded-full bg-green-700 px-5 py-3.5 t-small text-white hover:bg-green-900">
                {queue.length ? 'Next card' : 'Done'} <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
