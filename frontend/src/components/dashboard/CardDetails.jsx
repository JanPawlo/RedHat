import React, { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { Back, CardChat, CardFace } from './DecisionCard.jsx';
import CardForecast from './CardForecast.jsx';
/**
 * The card opened large (swipe up or the expand button): the card, what each decision leads to,
 * the "why" side with the AI answer, facts and forecast, and the chat at the bottom. Decisions are made back on the deck.
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
                  <CardFace card={card} footer={<span />} />
                </div>

              </div>
              <div className="min-w-0">
                <Back card={card} standalone chat={false} />
              </div>
            </div>
            {/* The 8-week cash chart for both decisions (only here; the card back links to it). */}
            <CardForecast card={card} className="mt-4" />
            {/* The chat is only here, at the very bottom (the card on a phone has none). */}
            <CardChat card={card} className="mt-4" />
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
