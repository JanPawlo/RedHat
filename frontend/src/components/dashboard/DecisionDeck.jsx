import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, CheckCheck, ChevronRight, Keyboard, Mail, Undo2, X } from 'lucide-react';
import DecisionCard, { CARD_H, CARD_W, HoldButton, LARGE_H, LARGE_W } from './DecisionCard.jsx';
import Icon from '../ui/Icon.jsx';
import { Button, Chip } from '../ui/primitives.jsx';
import { useAppState } from '../../state/AppState.jsx';
import { formatPLN } from '../../utils/format.js';

const exitVariants = {
  enter: { opacity: 0, scale: 0.96, y: 14 },
  center: { opacity: 1, scale: 1, y: 0, x: 0, rotate: 0 },
  exit: (dir) => ({
    x: (dir?.x || 0) * 640,
    y: (dir?.y || 0) * 420,
    rotate: (dir?.x || 0) * 18,
    opacity: 0,
    transition: { duration: 0.35, ease: [0.32, 0.72, 0, 1] },
  }),
};

function UpNextRow({ card }) {
  return (
    <div className="flex items-start gap-3 rounded-[20px] bg-surface p-3.5">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-green-100">
        <Icon name={card.icon} className="h-5 w-5 text-green-700" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="t-body-m">{card.title}</p>
        <p className="t-small text-text-muted">{card.next.sub}</p>
        <Chip tone={card.next.tone} dot={false} className="mt-1.5">{card.next.chip}</Chip>
      </div>
    </div>
  );
}

function AllDone({ decisions, cashProtected, onUndo }) {
  const approved = decisions.filter((d) => d.choice === 'approve').length;
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center gap-3 rounded-card bg-surface p-8 text-center shadow-card"
      style={{ width: CARD_W, height: CARD_H }}
    >
      <span className="flex h-24 w-24 items-center justify-center rounded-full bg-green-700 ring-[6px] ring-green-200">
        <CheckCheck className="h-11 w-11 text-white" />
      </span>
      <h3 className="mt-2 t-display-l">All done for today</h3>
      <p className="t-body text-text-muted">
        {decisions.length} decisions · {approved} approved
      </p>
      <Chip tone="green">Cash protected {formatPLN(cashProtected, { sign: true })}</Chip>
      <Link to="/mail" className="mt-2">
        <Button kind="soft" icon={Mail}>See emails in Mail</Button>
      </Link>
      <button type="button" onClick={onUndo} className="t-small text-text-muted hover:text-text">Undo last swipe</button>
    </motion.div>
  );
}

function useFitScale(height, reserved = 170) {
  const calc = () => (typeof window === 'undefined' ? 1 : Math.min(1, (window.innerHeight - reserved) / height));
  const [scale, setScale] = useState(calc);
  useEffect(() => {
    const onResize = () => setScale(calc());
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [height]);
  return scale;
}

/** Focus layer: the current card alone, bigger, in the middle of the screen. Click the card to flip it. */
function FocusLayer({ open, onClose, current, flipped, setFlipped, dir, swipe, holdHint, position, total }) {
  const scale = useFitScale(LARGE_H, 250);
  const gesture = (IconCmp, label, onClick, tone = 'ghost') => (
    <button
      type="button"
      onClick={onClick}
      className={
        tone === 'yes'
          ? 'flex items-center gap-2 rounded-full bg-green-700 px-5 py-3 t-small text-white hover:bg-green-900'
          : tone === 'no'
            ? 'flex items-center gap-2 rounded-full bg-status-red-soft px-5 py-3 t-small text-status-red hover:brightness-95'
            : 'flex items-center gap-2 rounded-full bg-surface px-5 py-3 t-small text-text hover:bg-subtle'
      }
    >
      <IconCmp className="h-4 w-4" strokeWidth={2} />
      {label}
    </button>
  );
  return (
    <AnimatePresence>
      {open && current && (
        <motion.div
          key="focus"
          role="dialog"
          aria-label="Decision card"
          data-deck-focus
          className="fixed inset-0 z-40 flex flex-col items-center justify-center gap-6 bg-ink/45 backdrop-blur-[3px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={(e) => e.target === e.currentTarget && onClose()}
        >
          <div className="pointer-events-none absolute inset-x-0 top-6 flex items-center justify-center">
            <Chip tone="dark" dot={false}>Card {position} of {total} · click the card to flip it</Chip>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="absolute right-6 top-6 flex h-11 w-11 items-center justify-center rounded-full bg-surface text-text shadow-soft hover:bg-subtle"
          >
            <X className="h-5 w-5" />
          </button>

          <div style={{ width: LARGE_W * scale, height: LARGE_H * scale }}>
            <div className="relative origin-top-left" style={{ width: LARGE_W, height: LARGE_H, transform: `scale(${scale})` }}>
              <AnimatePresence custom={dir} initial={false}>
                <motion.div
                  key={current.id}
                  custom={dir}
                  variants={exitVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  className="absolute left-0 top-0"
                  style={{ width: LARGE_W, height: LARGE_H }}
                >
                  <DecisionCard
                    large
                    card={current}
                    flipped={flipped}
                    onFlip={() => setFlipped((f) => !f)}
                    onTap={() => setFlipped((f) => !f)}
                    onSwipe={swipe}
                    onHoldHint={holdHint}
                  />
                </motion.div>
              </AnimatePresence>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-2.5">
            {gesture(ArrowLeft, current.left, () => swipe('decline', { x: -1, y: 0 }), 'no')}
            {gesture(ArrowUp, flipped ? 'Show the card' : 'Ask why', () => setFlipped((f) => !f))}
            {gesture(ArrowDown, 'Later', () => swipe('later', { x: 0, y: 1 }))}
            {current.holdToConfirm ? (
              <HoldButton className="!px-5 !py-3" onConfirm={() => swipe('approve', { x: 1, y: 0 })}>{current.right}</HoldButton>
            ) : (
              gesture(ArrowRight, current.right, () => swipe('approve', { x: 1, y: 0 }), 'yes')
            )}
          </div>
          <p className="t-small text-white/80">Esc to close · arrow keys work here too</p>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default function DecisionDeck() {
  const { queue, decide, decisions, undoLast, cashProtected, showToast, autopilot, company } = useAppState();
  const [flipped, setFlipped] = useState(false);
  const [dir, setDir] = useState({ x: 1, y: 0 });
  const [focus, setFocus] = useState(false);
  const current = queue[0];
  const total = queue.length + decisions.length;
  const position = decisions.length + 1;

  const holdHint = useCallback(() => {
    showToast({ tone: 'neutral', text: `Above ${company.autopilotLimit.toLocaleString('en-US')} PLN you press and hold the approve button.` });
  }, [showToast, company.autopilotLimit]);

  const swipe = useCallback(
    (choice, d) => {
      if (!current) return;
      setDir(d);
      setFlipped(false);
      if (queue.length <= 1 && choice !== 'later') setFocus(false);
      decide(current.id, choice);
    },
    [current, decide, queue.length],
  );

  useEffect(() => {
    const onKey = (e) => {
      if (!current || e.target.closest?.('input, textarea, [contenteditable]')) return;
      const dialog = document.querySelector('[role="dialog"]');
      if (dialog && !dialog.hasAttribute('data-deck-focus')) return;
      if (e.key === 'Escape' && dialog) {
        setFocus(false);
        return;
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        if (current.holdToConfirm) holdHint();
        else swipe('approve', { x: 1, y: 0 });
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        swipe('decline', { x: -1, y: 0 });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setFlipped((f) => !f);
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        swipe('later', { x: 0, y: 1 });
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [current, swipe, holdHint]);

  const minutes = Math.max(1, Math.round(queue.length * 0.5));

  return (
    <section id="deck" className="flex scroll-mt-6 flex-col gap-5 rounded-panel bg-green-100 p-6" aria-label="Decision deck">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="t-display-l">Decisions waiting</h2>
        <Chip tone="dark" dot={false}>
          {current ? `Card ${position} of ${total} · about ${minutes} min` : 'Nothing waiting'}
        </Chip>
        <div className="flex-1" />
        <Button kind="ghost" icon={Undo2} onClick={undoLast} disabled={!decisions.length}>Undo last swipe</Button>
        <Link to="/ledger">
          <Button kind="soft" iconRight={ChevronRight}>Ledger</Button>
        </Link>
      </div>

      <div className="flex flex-wrap gap-7">
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-1.5" aria-hidden>
            {Array.from({ length: total }).map((_, i) => (
              <span key={i} className={i === position - 1 && current ? 'h-1.5 w-7 rounded-full bg-green-700' : i < decisions.length ? 'h-1.5 w-4 rounded-full bg-green-500' : 'h-1.5 w-4 rounded-full bg-green-200'} />
            ))}
          </div>
          <div className="relative" style={{ width: CARD_W + 24, height: CARD_H + 20 }}>
            {current ? (
              <>
                {queue.length > 2 && <span className="absolute rounded-card border border-green-200 bg-surface/50" style={{ left: 22, top: 20, width: CARD_W, height: CARD_H, transform: 'rotate(-3deg)' }} />}
                {queue.length > 1 && <span className="absolute rounded-card border border-green-200 bg-surface/80" style={{ left: 12, top: 10, width: CARD_W, height: CARD_H, transform: 'rotate(-1.5deg)' }} />}
                <AnimatePresence custom={dir} initial={false}>
                  <motion.div
                    key={current.id}
                    custom={dir}
                    variants={exitVariants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                    className="absolute left-0 top-0"
                    style={{ width: CARD_W, height: CARD_H }}
                  >
                    <DecisionCard
                      card={current}
                      flipped={flipped && !focus}
                      onFlip={() => setFlipped((f) => !f)}
                      onSwipe={swipe}
                      onHoldHint={holdHint}
                      onTap={() => setFocus(true)}
                      onEnlarge={() => setFocus(true)}
                    />
                  </motion.div>
                </AnimatePresence>
              </>
            ) : (
              <AllDone decisions={decisions} cashProtected={cashProtected} onUndo={undoLast} />
            )}
          </div>
        </div>

        <div className="flex min-w-[280px] flex-1 flex-col gap-2.5">
          <p className="t-overline text-green-700">Up next</p>
          {queue.slice(1, 4).map((c) => (
            <UpNextRow key={c.id} card={c} />
          ))}
          {queue.length <= 1 && <p className="rounded-[20px] bg-surface/60 p-4 t-small text-text-muted">No more cards after this one.</p>}
          <div className="mt-1 flex flex-col gap-1.5 rounded-[20px] border border-dashed border-green-200 p-4">
            <p className="flex items-center gap-2 t-small text-green-700">
              <Keyboard className="h-4 w-4" /> Shortcuts
            </p>
            <p className="t-small text-text-muted">
              Click the card to open it bigger. ← decline · → approve · ↑ ask why · ↓ later. Above {company.autopilotLimit.toLocaleString('en-US')} PLN you hold the button to confirm.
              {autopilot ? '' : ' Autopilot is off, so every action waits for you.'}
            </p>
          </div>
        </div>
      </div>
      <FocusLayer
        open={focus}
        onClose={() => setFocus(false)}
        current={current}
        flipped={flipped}
        setFlipped={setFlipped}
        dir={dir}
        swipe={swipe}
        holdHint={holdHint}
        position={position}
        total={total}
      />
    </section>
  );
}
