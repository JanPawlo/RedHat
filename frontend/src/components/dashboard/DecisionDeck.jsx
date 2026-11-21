import React, { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion, useMotionValue } from 'framer-motion';
import { ArrowLeft, ArrowRight, CheckCheck, Clock3, History, Mail, Sparkles, Undo2 } from 'lucide-react';
import DecisionCard from './DecisionCard.jsx';
import { Button, Chip } from '../ui/primitives.jsx';
import { useAppState } from '../../state/AppState.jsx';
import { useAgentProgress } from '../../state/agentStore.js';
import { cx, formatPLN } from '../../utils/format.js';

const exitVariants = {
  enter: { opacity: 0, scale: 0.96, y: 14 },
  center: { opacity: 1, scale: 1, y: 0, x: 0, rotate: 0 },
  exit: (dir) => ({
    x: (dir?.x || 0) * 700,
    y: (dir?.y || 0) * 420,
    rotate: (dir?.x || 0) * 18,
    opacity: 0,
    transition: { duration: 0.35, ease: [0.32, 0.72, 0, 1] },
  }),
};

function AllDone({ decisions, cashProtected, onUndo }) {
  const approved = decisions.filter((d) => d.choice === 'approve').length;
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      className="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-card bg-surface p-8 text-center shadow-card"
    >
      <span className="flex h-24 w-24 items-center justify-center rounded-full bg-green-700 ring-[6px] ring-green-200">
        <CheckCheck className="h-11 w-11 text-white" />
      </span>
      <h3 className="mt-2 t-display-l">All done for today</h3>
      <p className="t-body text-text-muted">
        {decisions.length} decisions · {approved} approved
      </p>
      <Chip tone="green">Cash protected {formatPLN(cashProtected, { sign: true })}</Chip>
      <div className="mt-2 flex flex-wrap justify-center gap-2">
        <Link to="/history">
          <Button kind="soft" icon={History}>See History</Button>
        </Link>
        <Link to="/mail">
          <Button kind="ghost" icon={Mail}>Mail</Button>
        </Link>
      </div>
      {decisions.length > 0 && (
        <button type="button" onClick={onUndo} className="t-small text-text-muted hover:text-text">Undo last decision</button>
      )}
    </motion.div>
  );
}

/** Animated hint under the card: a hand that slides left and right. */
function SwipeHint() {
  return (
    <div className="flex items-center gap-2.5 text-text-muted" aria-label="Drag the card left or right and hold to decide">
      <ArrowLeft className="h-4 w-4 text-status-red/70" strokeWidth={2.2} aria-hidden />
      <motion.svg
        viewBox="0 0 24 24"
        className="h-7 w-7 text-green-700"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.7}
        strokeLinecap="round"
        strokeLinejoin="round"
        animate={{ x: [-7, 7, -7], rotate: [-8, 8, -8] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
        aria-hidden
      >
        <path d="M9 11V5.5a1.5 1.5 0 0 1 3 0V11" />
        <path d="M12 10V9a1.5 1.5 0 0 1 3 0v2" />
        <path d="M15 10.5a1.5 1.5 0 0 1 3 0V15a6 6 0 0 1-6 6h-1.2a6 6 0 0 1-4.7-2.3L3.6 15.5a1.6 1.6 0 0 1 2.3-2.2L9 15.5" />
      </motion.svg>
      <ArrowRight className="h-4 w-4 text-status-green/80" strokeWidth={2.2} aria-hidden />
      <span className="t-small">Drag and hold to decide · tap to see why</span>
    </div>
  );
}

function AgentStatus({ cards }) {
  const { ready, failed, total } = useAgentProgress(cards);
  const analysing = total - ready - failed;
  if (analysing <= 0) return null;
  return (
    <span className="flex items-center gap-1.5 t-small text-text-muted">
      <Sparkles className="h-3.5 w-3.5 animate-pulse text-green-700" /> Agent analysing cards · {ready}/{total} ready
    </span>
  );
}

/** Main screen: one card in the middle. Tap to flip, drag and hold to decide (front or back). */
export default function DecisionDeck() {
  const { queue, decide, decisions, undoLast, cashProtected, holdMsFor } = useAppState();
  const [flipped, setFlipped] = useState(false);
  const [dir, setDir] = useState({ x: 1, y: 0 });
  const progress = useMotionValue(0);
  const current = queue[0];
  const total = queue.length + decisions.length;
  const position = decisions.length + 1;
  const holdMs = holdMsFor(current);

  const onDecide = useCallback(
    (choice, d) => {
      if (!current) return;
      setDir(d);
      setFlipped(false);
      progress.set(0);
      decide(current.id, choice);
    },
    [current, decide, progress],
  );

  return (
    <section className="flex min-h-0 flex-1 flex-col items-center gap-3 sm:gap-4" aria-label="Decision card">
      <div className="flex w-full max-w-[440px] items-center justify-between gap-3 px-1">
        <div className="flex items-center gap-1.5" aria-hidden>
          {Array.from({ length: total }).map((_, i) => (
            <span
              key={i}
              className={cx(
                'h-1.5 rounded-full',
                i === position - 1 && current ? 'w-7 bg-green-700' : i < decisions.length ? 'w-4 bg-green-500' : 'w-4 bg-green-200',
              )}
            />
          ))}
        </div>
        <span className="t-small text-text-muted">{current ? `Card ${position} of ${total}` : 'Nothing waiting'}</span>
      </div>

      <div className="flex min-h-0 w-full flex-1 items-center justify-center">
        {/* Portrait card (about 2:3); on narrow phones it takes the full width and stays taller than wide. */}
        <div className="relative aspect-[2/3] h-full max-h-[640px] min-h-[380px] max-w-full">
          {current ? (
            <AnimatePresence custom={dir} initial={false}>
              <motion.div key={current.id} custom={dir} variants={exitVariants} initial="enter" animate="center" exit="exit" className="absolute inset-0">
                <DecisionCard card={current} flipped={flipped} onFlip={() => setFlipped((f) => !f)} onDecide={onDecide} holdMs={holdMs} progress={progress} />
              </motion.div>
            </AnimatePresence>
          ) : (
            <AllDone decisions={decisions} cashProtected={cashProtected} onUndo={undoLast} />
          )}
        </div>
      </div>

      {current && (
        <div className="flex w-full max-w-[440px] flex-col items-center gap-2">
          <SwipeHint />
          <div className="flex flex-wrap items-center justify-center gap-2">
            <button
              type="button"
              onClick={() => onDecide('later', { x: 0, y: 1 })}
              className="flex items-center gap-2 rounded-full bg-surface px-5 py-2.5 t-small text-text shadow-soft hover:bg-subtle"
            >
              <Clock3 className="h-4 w-4" /> Skip for now
            </button>
            {decisions.length > 0 && (
              <button type="button" onClick={undoLast} className="flex items-center gap-1 rounded-full px-3 py-2.5 t-small text-text-muted hover:text-text">
                <Undo2 className="h-3.5 w-3.5" /> Undo last
              </button>
            )}
          </div>
        </div>
      )}
      <AgentStatus cards={queue} />
    </section>
  );
}
