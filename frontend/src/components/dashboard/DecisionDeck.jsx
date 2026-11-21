import React, { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion, useMotionValue } from 'framer-motion';
import { ArrowLeft, ArrowRight, CheckCheck, Clock3, History, Mail, Sparkles, Undo2 } from 'lucide-react';
import DecisionCard from './DecisionCard.jsx';
import HoldButton from '../ui/HoldButton.jsx';
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

/** Side decision button (desktop: left/right of the card; phone: round buttons under it). Hold to confirm. */
function SideButton({ side, card, holdMs, onConfirm, onPress, progress, round = false }) {
  const yes = side === 'yes';
  const IconCmp = yes ? ArrowRight : ArrowLeft;
  return (
    <HoldButton
      holdMs={holdMs}
      label={`${yes ? 'Swipe right' : 'Swipe left'}: ${yes ? card.right : card.left}. Press and hold.`}
      onConfirm={onConfirm}
      onPressChange={(down) => onPress(down ? (yes ? 1 : -1) : 0)}
      onProgress={(p) => progress.set(p)}
      fillClassName={yes ? 'bg-green-900' : 'bg-status-red/20'}
      className={cx(
        'shrink-0 shadow-soft transition-transform active:scale-[0.97]',
        yes ? 'bg-green-700 text-white' : 'bg-surface text-status-red ring-1 ring-inset ring-status-red-soft',
        round ? 'h-16 w-16 rounded-full' : 'w-[148px] flex-col rounded-[28px] px-4 py-6 xl:w-[168px]',
      )}
    >
      {round ? (
        <IconCmp className="h-7 w-7" strokeWidth={2.2} />
      ) : (
        <span className="flex flex-col items-center gap-3 text-center">
          <span className={cx('flex h-14 w-14 items-center justify-center rounded-full', yes ? 'bg-white/15' : 'bg-status-red-soft')}>
            <IconCmp className="h-6 w-6" strokeWidth={2.2} />
          </span>
          <span className="t-overline opacity-80">{yes ? 'Swipe right' : 'Swipe left'}</span>
          <span className="t-body-m leading-snug">{yes ? card.right : card.left}</span>
          <span className="t-small opacity-70">Hold to confirm</span>
        </span>
      )}
    </HoldButton>
  );
}

function AgentStatus({ cards }) {
  const { ready, failed, total } = useAgentProgress(cards);
  if (!total) return null;
  const text = failed ? `Agent offline for ${failed} card${failed > 1 ? 's' : ''} · engine notes shown` : ready < total ? `Agent analysing cards · ${ready}/${total} ready` : 'Agent ready for every card';
  return (
    <span className="flex items-center gap-1.5 t-small text-text-muted">
      <Sparkles className={cx('h-3.5 w-3.5', ready < total && !failed ? 'animate-pulse text-green-700' : 'text-green-700')} /> {text}
    </span>
  );
}

/** Main screen: one card in the middle. Tap to flip, drag and hold to decide, or hold a side button. */
export default function DecisionDeck() {
  const { queue, decide, decisions, undoLast, cashProtected, holdMsFor } = useAppState();
  const [flipped, setFlipped] = useState(false);
  const [dir, setDir] = useState({ x: 1, y: 0 });
  const [pressDir, setPressDir] = useState(0);
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
      setPressDir(0);
      progress.set(0);
      decide(current.id, choice);
    },
    [current, decide, progress],
  );

  const sideProps = current && {
    card: current,
    holdMs,
    progress,
    onPress: setPressDir,
  };

  return (
    <section className="flex min-h-0 flex-1 flex-col items-center gap-3 sm:gap-4" aria-label="Decision card">
      <div className="flex w-full max-w-[520px] items-center justify-between gap-3 px-1">
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

      <div className="flex min-h-0 w-full flex-1 items-center justify-center gap-6 xl:gap-10">
        {current && (
          <div className="hidden lg:block">
            <SideButton side="no" {...sideProps} onConfirm={() => onDecide('decline', { x: -1, y: 0 })} />
          </div>
        )}

        <div className="relative h-full max-h-[700px] min-h-[320px] w-full max-w-[520px]">
          {current ? (
            <AnimatePresence custom={dir} initial={false}>
              <motion.div key={current.id} custom={dir} variants={exitVariants} initial="enter" animate="center" exit="exit" className="absolute inset-0">
                <DecisionCard
                  card={current}
                  flipped={flipped}
                  onFlip={() => setFlipped((f) => !f)}
                  onDecide={onDecide}
                  holdMs={holdMs}
                  pressDir={pressDir}
                  progress={progress}
                />
              </motion.div>
            </AnimatePresence>
          ) : (
            <AllDone decisions={decisions} cashProtected={cashProtected} onUndo={undoLast} />
          )}
        </div>

        {current && (
          <div className="hidden lg:block">
            <SideButton side="yes" {...sideProps} onConfirm={() => onDecide('approve', { x: 1, y: 0 })} />
          </div>
        )}
      </div>

      {current && (
        <div className="flex w-full max-w-[520px] items-center justify-between gap-3 lg:justify-center">
          <div className="lg:hidden">
            <SideButton side="no" round {...sideProps} onConfirm={() => onDecide('decline', { x: -1, y: 0 })} />
          </div>
          <div className="flex flex-col items-center gap-1.5">
            <button
              type="button"
              onClick={() => onDecide('later', { x: 0, y: 1 })}
              className="flex items-center gap-2 rounded-full bg-surface px-5 py-3 t-small text-text shadow-soft hover:bg-subtle"
            >
              <Clock3 className="h-4 w-4" /> Skip for now
            </button>
            {decisions.length > 0 && (
              <button type="button" onClick={undoLast} className="flex items-center gap-1 py-1 t-small text-text-muted hover:text-text">
                <Undo2 className="h-3.5 w-3.5" /> Undo last
              </button>
            )}
          </div>
          <div className="lg:hidden">
            <SideButton side="yes" round {...sideProps} onConfirm={() => onDecide('approve', { x: 1, y: 0 })} />
          </div>
        </div>
      )}
      <AgentStatus cards={queue} />
    </section>
  );
}
