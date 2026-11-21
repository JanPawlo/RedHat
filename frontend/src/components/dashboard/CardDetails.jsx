import React, { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowLeft, ArrowRight, X } from 'lucide-react';
import { Back, CardFace } from './DecisionCard.jsx';
import { cx } from '../../utils/format.js';

function OutcomeBox({ side, card }) {
  const yes = side === 'yes';
  const IconCmp = yes ? ArrowRight : ArrowLeft;
  const outcomes = card.outcomes?.[yes ? 'right' : 'left'] || [];
  return (
    <div className={cx('flex min-w-0 flex-col gap-2 rounded-[22px] p-4', yes ? 'bg-status-green-soft' : 'bg-status-red-soft')}>
      <div className="flex items-center gap-2">
        <span className={cx('font-display text-[22px] font-black leading-none', yes ? 'text-status-green' : 'text-status-red')}>{yes ? 'YES' : 'NO'}</span>
        <IconCmp className={cx('h-4 w-4 shrink-0', yes ? 'text-status-green' : 'text-status-red')} strokeWidth={2.4} />
        <span className="min-w-0 t-body-m">{card[yes ? 'right' : 'left']}</span>
      </div>
      {outcomes.length > 0 && (
        <ul className="flex flex-col gap-1">
          {outcomes.map((o) => (
            <li key={o} className="flex items-start gap-2 t-small">
              <span className={cx('mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full', yes ? 'bg-status-green' : 'bg-status-red')} aria-hidden />
              {o}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * The card opened large (swipe up or the expand button): the card, what each decision leads to,
 * and the "why" side with the AI answer, facts, forecast and chat. Decisions are made back on the deck.
 */
export default function CardDetails({ card, onClose }) {
  useEffect(() => {
    if (!card) return undefined;
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [card, onClose]);

  return (
    <AnimatePresence>
      {card && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6" role="dialog" aria-modal="true" aria-label={card.title}>
          <motion.div className="absolute inset-0 bg-ink/45 backdrop-blur-[2px]" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.div
            className="relative flex max-h-full w-full max-w-[1080px] flex-col overflow-y-auto rounded-panel bg-canvas p-3 shadow-card scrollbar-thin sm:p-5"
            initial={{ opacity: 0, y: 40, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30, scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 320, damping: 30 }}
          >
            <div className="mb-3 flex items-center gap-3 px-1">
              <p className="min-w-0 flex-1 t-small text-text-muted">All details · close and drag the card to decide</p>
              <button type="button" onClick={onClose} aria-label="Close" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-surface hover:bg-subtle">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="flex min-w-0 flex-col gap-4">
                <div className="h-[440px] sm:h-[480px]">
                  <CardFace card={card} />
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <OutcomeBox side="no" card={card} />
                  <OutcomeBox side="yes" card={card} />
                </div>
              </div>
              <div className="h-[620px] min-w-0 lg:h-auto lg:min-h-[620px]">
                <Back card={card} standalone />
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
