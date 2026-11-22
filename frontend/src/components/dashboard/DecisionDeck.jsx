import React, { useCallback, useLayoutEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion, useMotionValue, useMotionValueEvent } from 'framer-motion';
import { BarChart3, CheckCheck, Clock3, History, Sparkles, Undo2 } from 'lucide-react';
import DecisionCard from './DecisionCard.jsx';
import CardDetails from './CardDetails.jsx';
import { DecisionBackdrop, DecisionZone } from './DecisionOutcome.jsx';
import { useMediaQuery } from '../../hooks/useMediaQuery.js';
import { DESKTOP_QUERY } from '../../const/layout.js';
import { DESKTOP_GAP_PX, DESKTOP_TEXT_CLEARANCE_PX } from '../../const/cardMotion.js';
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
        <Link to="/analysis">
          <Button kind="ghost" icon={BarChart3}>Analysis</Button>
        </Link>
      </div>
      {decisions.length > 0 && (
        <button type="button" onClick={onUndo} className="t-small text-text-muted hover:text-text">Undo last decision</button>
      )}
    </motion.div>
  );
}

function AgentStatus({ cards }) {
  const { ready, failed, total } = useAgentProgress(cards);
  const analysing = total - ready - failed;
  if (analysing <= 0) return null;
  const text = `Agent analysing cards · ${ready}/${total} ready`;
  return (
    <span className="flex items-center gap-1 text-text-muted" title={text} aria-label={text}>
      <Sparkles className="h-3.5 w-3.5 animate-pulse text-green-700" />
      <span className="hidden t-small xl:inline">{ready}/{total}</span>
    </span>
  );
}

/** Desktop: how far the card may go each way, so its edge stops just before the NO / YES text. */
function measureDragLimits(stage) {
  const limitFor = (side) => {
    const text = stage.querySelector(`[data-outcome-text="${side}"]`);
    const zone = text?.closest('.deck-slot');
    if (!zone) return 0;
    // The text is centered in its zone; layout sizes (offsetWidth) ignore the zone's show/hide animation.
    const besideText = (zone.offsetWidth - text.offsetWidth) / 2;
    return Math.max(0, DESKTOP_GAP_PX + besideText - DESKTOP_TEXT_CLEARANCE_PX);
  };
  return { left: limitFor('no'), right: limitFor('yes') };
}

function useDragLimits(stageRef, active, cardId) {
  const [limits, setLimits] = useState(null);

  useLayoutEffect(() => {
    const stage = stageRef.current;
    if (!active || !stage) return undefined;

    const update = () => setLimits(measureDragLimits(stage));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(stage);
    return () => observer.disconnect();
  }, [stageRef, active, cardId]);

  return active ? limits : null;
}

/**
 * The current card with its enter / exit animation. Memoized on purpose: AnimatePresence gives its children a
 * new context on every render, and framer-motion then re-measures the draggable card, resetting a flipped
 * card's rotateY(180deg) to none for a moment, so the screen blinked whenever the deck re-rendered
 * (opening or closing notifications and More details). With stable props it re-renders only when the card changes.
 */
const DeckCard = React.memo(function DeckCard({ card, dir, ...cardProps }) {
  return (
    <AnimatePresence custom={dir} initial={false}>
      <motion.div key={card.id} custom={dir} variants={exitVariants} initial="enter" animate="center" exit="exit" className="absolute inset-0">
        <DecisionCard card={card} {...cardProps} />
      </motion.div>
    </AnimatePresence>
  );
});

/** Main screen: one card in the middle. Tap to flip, drag and hold to decide (front or back). */
export default function DecisionDeck() {
  const { queue, decide, decisions, undoLast, cashProtected, holdMsFor } = useAppState();
  const [flipped, setFlipped] = useState(false);
  const [dir, setDir] = useState({ x: 1, y: 0 });
  const progress = useMotionValue(0);
  const dragX = useMotionValue(0);
  const [armedDir, setArmedDir] = useState(0);
  const [ready, setReady] = useState(false);
  // NO / YES frames are shown only while the card is pressed or dragged.
  const [engaged, setEngaged] = useState(false);
  // Card opened large (the expand button).
  const [expanded, setExpanded] = useState(null);
  // Cards whose back ("why") the owner has seen; only those can be swiped.
  const [seen, setSeen] = useState(() => new Set());
  const desktop = useMediaQuery(DESKTOP_QUERY);
  const current = queue[0];
  const total = queue.length + decisions.length;
  const position = decisions.length + 1;
  const holdMs = holdMsFor(current);
  const stageRef = useRef(null);
  const dragLimits = useDragLimits(stageRef, desktop && Boolean(current), current?.id);
  const markSeen = useCallback((card) => card && setSeen((s) => (s.has(card.id) ? s : new Set(s).add(card.id))), []);

  // Stable callbacks, so the memoized DecisionCard does not re-render when only other app state changes.
  const flip = useCallback(() => {
    if (!flipped) markSeen(current);
    setFlipped((f) => !f);
  }, [flipped, current, markSeen]);

  const expand = useCallback(() => {
    markSeen(current);
    setExpanded(current);
  }, [current, markSeen]);

  const onDragX = useCallback((v) => dragX.set(v), [dragX]);

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

  useMotionValueEvent(progress, 'change', (p) => setReady(p >= 1));

  const zoneProps = current && { card: current, dragX, progress };

  return (
    <section className="flex min-h-0 flex-1 flex-col items-center gap-2 sm:gap-3" aria-label="Decision card">
      {/* The stage is a size container: the card (and on desktop the two zones) get the largest 2:3 size that fits. */}
      <div ref={stageRef} className="deck-stage relative min-h-[380px] w-full flex-1">
        {/* Desktop: NO and YES backgrounds, each half of the stage, behind everything. */}
        {desktop && current && (
          <>
            <DecisionBackdrop side="no" dragX={dragX} visible={engaged} fullAt={dragLimits?.left} />
            <DecisionBackdrop side="yes" dragX={dragX} visible={engaged} fullAt={dragLimits?.right} />
          </>
        )}
        <div className="relative flex h-full w-full items-center justify-center gap-6 lg:gap-14">
          {desktop && current && (
            <motion.div
              className="deck-slot"
              aria-hidden={!engaged}
              initial={false}
              animate={engaged ? { opacity: 1, x: 0, scale: 1 } : { opacity: 0, x: 40, scale: 0.96 }}
              transition={{ type: 'spring', stiffness: 320, damping: 30 }}
              style={{ pointerEvents: engaged ? 'auto' : 'none' }}
            >
              <DecisionZone side="no" {...zoneProps} fullAt={dragLimits?.left} armed={armedDir < 0} ready={ready && armedDir < 0} />
            </motion.div>
          )}

          {/* Above the zones, so the dragged card slides over them. */}
          <div className="deck-slot relative z-10">
            {current ? (
              <DeckCard
                card={current}
                dir={dir}
                flipped={flipped}
                onFlip={flip}
                locked={!seen.has(current.id)}
                onDecide={onDecide}
                holdMs={holdMs}
                progress={progress}
                desktop={desktop}
                dragLimits={dragLimits}
                onDragX={onDragX}
                onArmedChange={setArmedDir}
                onEngagedChange={setEngaged}
                onExpand={expand}
              />
            ) : (
              <AllDone decisions={decisions} cashProtected={cashProtected} onUndo={undoLast} />
            )}
          </div>

          {desktop && current && (
            <motion.div
              className="deck-slot"
              aria-hidden={!engaged}
              initial={false}
              animate={engaged ? { opacity: 1, x: 0, scale: 1 } : { opacity: 0, x: -40, scale: 0.96 }}
              transition={{ type: 'spring', stiffness: 320, damping: 30 }}
              style={{ pointerEvents: engaged ? 'auto' : 'none' }}
            >
              <DecisionZone side="yes" {...zoneProps} fullAt={dragLimits?.right} armed={armedDir > 0} ready={ready && armedDir > 0} />
            </motion.div>
          )}
        </div>
      </div>

      {/* One line under the card: progress, Skip / Undo, counter. Kept low so the card can be bigger. */}
      <div className="relative z-0 grid w-full max-w-[640px] grid-cols-[1fr_auto_1fr] items-center gap-2 px-1">
        <div className="flex items-center gap-1.5" aria-hidden>
          {Array.from({ length: total }).map((_, i) => (
            <span
              key={i}
              className={cx(
                'h-1.5 rounded-full',
                i === position - 1 && current ? 'w-6 bg-green-700 sm:w-7' : i < decisions.length ? 'w-3 bg-green-500 sm:w-4' : 'w-3 bg-green-200 sm:w-4',
              )}
            />
          ))}
        </div>

        <div className="flex items-center gap-1">
          {current && (
            <button
              type="button"
              onClick={() => onDecide('later', { x: 0, y: 1 })}
              className="flex items-center gap-1.5 whitespace-nowrap rounded-full bg-surface px-3.5 py-2 t-small text-text shadow-soft hover:bg-subtle sm:gap-2 sm:px-5 sm:py-2.5"
            >
              <Clock3 className="h-4 w-4" />
              <span>
                Skip<span className="hidden sm:inline"> for now</span>
              </span>
            </button>
          )}
          {decisions.length > 0 && (
            <button
              type="button"
              onClick={undoLast}
              aria-label="Undo last decision"
              title="Undo last decision"
              className="flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-2 t-small text-text-muted hover:text-text sm:px-3 sm:py-2.5"
            >
              <Undo2 className="h-3.5 w-3.5" /> <span className="hidden sm:inline">Undo last</span>
            </button>
          )}
        </div>

        <div className="flex items-center justify-end gap-2">
          <AgentStatus cards={queue} />
          <span className="whitespace-nowrap t-small text-text-muted">{current ? `Card ${position} of ${total}` : 'Nothing waiting'}</span>
        </div>
      </div>
      <CardDetails card={expanded} onClose={() => setExpanded(null)} />
    </section>
  );
}
