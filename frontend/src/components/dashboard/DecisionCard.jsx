import React, { useEffect, useRef, useState } from 'react';
import { motion, useDragControls, useMotionValue, useMotionValueEvent, useTransform } from 'framer-motion';
import { Check, Copy, FileText, SendHorizontal, Sparkles } from 'lucide-react';
import { askAgent, AGENT_MODEL } from '../../api/agentApi.js';
import { useExplanation } from '../../state/agentStore.js';
import Icon from '../ui/Icon.jsx';
import { Chip } from '../ui/primitives.jsx';
import { cx } from '../../utils/format.js';

// How far the card has to be dragged before holding starts to count.
const SWIPE_X = 110;
// Movement (px) under which a press still counts as a tap (flip).
const TAP_SLOP = 8;
// Elements that keep their own gestures: typing and the horizontal list of questions.
const NO_DRAG = 'input, textarea, select, [data-no-drag]';
// Elements that handle a tap themselves, so the card does not flip.
const NO_FLIP = 'button, input, textarea, form, a, [data-no-flip]';

/** "I'd swipe right · 78% confident": the agent's proposal; tapping it shows the why (flips the card). */
export function ConfidenceChip({ card, onClick, className }) {
  const text = `I'd swipe ${card.recommendation === 'right' ? 'right' : 'left'} · ${card.confidence}% confident`;
  const Tag = onClick ? 'button' : 'span';
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      className={cx(
        'inline-flex items-center gap-2 whitespace-nowrap rounded-full bg-status-green-soft px-3.5 py-1.5 t-small text-status-green',
        onClick && 'transition hover:brightness-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-700',
        className,
      )}
      title={onClick ? 'Why? Tap to see what the agent looked at' : undefined}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-status-green" />
      {text}
    </Tag>
  );
}

/** Copies only the text written by the AI agent. */
export function CopyButton({ text, className }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = document.createElement('textarea');
      area.value = text;
      document.body.appendChild(area);
      area.select();
      document.execCommand('copy');
      area.remove();
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button
      type="button"
      onClick={copy}
      data-no-flip
      aria-label={copied ? 'Copied' : 'Copy the AI answer'}
      title={copied ? 'Copied' : 'Copy the AI answer'}
      className={cx('flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-green-700 transition-colors hover:bg-green-200', className)}
    >
      {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
    </button>
  );
}

/** Card front: the matter to decide. Same look in the deck and in History. */
export function CardFace({ card, onWhy, footer, compact = false, className }) {
  return (
    <div className={cx('relative flex h-full flex-col items-center rounded-card bg-surface shadow-card', compact ? 'p-5' : 'p-5 sm:p-8 sm:[@media(max-height:860px)]:p-6', className)}>
      <div className="flex w-full flex-wrap items-start justify-between gap-2">
        <Chip dot={false}>{card.bankProduct ? `${card.category} · COMMERZBANK` : card.category}</Chip>
        {card.autonomy && <Chip tone="amber">{card.autonomy}</Chip>}
      </div>
      {/* Scrolls (from the top) only when the card is too short for its content. */}
      <div className={cx('w-full', !compact && '-mx-1 min-h-0 flex-1 touch-pan-y overflow-y-auto px-1 scrollbar-thin')}>
        <div className={cx('flex min-h-full w-full flex-col items-center justify-center', compact ? 'gap-3 py-3' : 'gap-4 py-3 sm:gap-5 [@media(max-height:860px)]:gap-3')}>
          <span
            className={cx(
              'flex shrink-0 items-center justify-center rounded-full bg-green-100 ring-[6px] ring-green-200',
              compact ? 'h-16 w-16' : 'h-[88px] w-[88px] sm:h-[120px] sm:w-[120px] [@media(max-height:860px)]:!h-[96px] [@media(max-height:860px)]:!w-[96px]',
            )}
          >
            <Icon name={card.icon} className={cx('text-green-700', compact ? 'h-7 w-7' : 'h-10 w-10 sm:h-14 sm:w-14 [@media(max-height:860px)]:!h-11 [@media(max-height:860px)]:!w-11')} />
          </span>
          <h3
            className={cx(
              'max-w-[420px] text-balance text-center font-display font-bold leading-tight',
              compact ? 'text-[20px]' : 'text-[24px] sm:text-[30px] [@media(max-height:860px)]:!text-[26px]',
            )}
          >
            {card.title}
          </h3>
          <ConfidenceChip card={card} onClick={onWhy} />
          <div className={cx('w-full max-w-[440px] rounded-[18px] bg-subtle text-center', compact ? 'px-4 py-3' : 'px-4 py-3.5 sm:px-6 sm:py-5 [@media(max-height:860px)]:!py-3')}>
            <p className={cx('t-body', !compact && 'sm:!text-[16px] [@media(max-height:860px)]:!text-[15px]')}>{card.proposal}</p>
          </div>
        </div>
      </div>
      {footer}
    </div>
  );
}

function MiniForecast({ back }) {
  const [ifSwipe, setIfSwipe] = useState(false);
  const weeks = ifSwipe ? back.weeksIfApproved : back.weeks;
  const lowest = Math.min(...weeks);
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="t-small text-text-muted">Cash · next 8 weeks</span>
        <button type="button" onClick={() => setIfSwipe((v) => !v)} className="t-small text-green-700 hover:underline">
          <span className={cx(!ifSwipe && 'font-semibold')}>now</span> / <span className={cx(ifSwipe && 'font-semibold')}>if you swipe right</span>
        </button>
      </div>
      <div className="relative flex h-[80px] items-end justify-between gap-1.5">
        {weeks.map((v, i) => {
          const low = v === lowest;
          const near = !low && v < back.bufferLevel + 8;
          return (
            <motion.span
              key={i}
              className={cx('flex-1 rounded-b-[3px] rounded-t-lg', low ? 'bg-status-red' : near ? 'bg-status-amber' : 'bg-green-200')}
              animate={{ height: v * 1.1 }}
              transition={{ type: 'spring', stiffness: 260, damping: 26 }}
            />
          );
        })}
        <span className="absolute inset-x-0 h-[1.5px] bg-text/50" style={{ bottom: back.bufferLevel * 1.1 }} title="Safety buffer" />
      </div>
    </div>
  );
}

function AgentAnswer({ card }) {
  const { status, answer, model } = useExplanation(card);
  const waiting = status === 'loading' || status === 'queued' || status === 'idle';
  const text = status === 'ready' ? answer : status === 'error' ? card.back.description : '';
  return (
    <div className="rounded-2xl bg-green-100/70 px-4 py-3">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="t-small font-semibold text-green-700">{status === 'error' ? 'Engine note' : `OpenShift AI · ${model || AGENT_MODEL}`}</span>
        {text && <CopyButton text={text} className="-my-1.5 -mr-2" />}
      </div>
      {text && <p className="t-body text-text">{text}</p>}
      {waiting && <p className="t-small italic text-text-muted">{status === 'loading' ? 'The agent is writing the explanation…' : 'Waiting in the analysis queue…'}</p>}
    </div>
  );
}

/** Card back: the agent's answer, what it looked at, and a chat about this card. */
function Back({ card, onFlip }) {
  const { back } = card;
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(false);
  const scroller = useRef(null);

  useEffect(() => {
    setMessages([]);
    scroller.current?.scrollTo({ top: 0 });
  }, [card.id]);

  // Scroll down only when the conversation grows; the back always opens at the top.
  useEffect(() => {
    if (messages.length) scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  const ask = async (q) => {
    const text = (q ?? draft).trim();
    if (!text || loading) return;
    setDraft('');
    setMessages((m) => [...m, { role: 'user', text }]);
    setLoading(true);
    try {
      const { answer } = await askAgent(card, text);
      setMessages((m) => [...m, { role: 'ai', text: answer }]);
    } catch {
      setMessages((m) => [...m, { role: 'ai', error: true, text: 'Could not reach the model on OpenShift AI. Try again in a moment.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="absolute inset-0 flex flex-col gap-3 rounded-card bg-surface p-5 shadow-card backface-hidden [transform:rotateY(180deg)] sm:p-7">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2">
          <Sparkles className="h-[18px] w-[18px] text-green-700" strokeWidth={1.8} />
          <span className="t-title">Why I suggest this</span>
        </span>
        <button type="button" onClick={onFlip} className="rounded-full bg-subtle px-3.5 py-2 t-small text-text-muted hover:bg-line hover:text-text">
          Back
        </button>
      </div>

      <div ref={scroller} className="-mr-2 flex min-h-0 flex-1 touch-pan-y flex-col gap-3 overflow-y-auto overscroll-contain pr-2 scrollbar-thin">
        <AgentAnswer card={card} />
        <dl>
          {back.facts.map(([k, v]) => (
            <div key={k} className="flex items-center justify-between gap-3 border-b border-line py-2">
              <dt className="t-small text-text-muted">{k}</dt>
              <dd className="text-right t-mono">{v}</dd>
            </div>
          ))}
        </dl>
        <MiniForecast back={back} />
        <p className="flex items-center gap-1.5 t-small text-text-muted">
          <FileText className="h-3.5 w-3.5 shrink-0" /> {back.sources}
        </p>
        {messages.map((m, i) => (
          <div
            key={i}
            data-no-flip
            className={cx('flex max-w-[90%] items-start gap-1 rounded-2xl px-3 py-2 t-small', m.role === 'user' ? 'self-end bg-green-700 text-white' : 'self-start bg-green-100 text-text')}
          >
            <span className="flex-1">{m.text}</span>
            {m.role === 'ai' && !m.error && <CopyButton text={m.text} className="-my-1.5 -mr-2" />}
          </div>
        ))}
        {loading && <p className="max-w-[90%] self-start rounded-2xl bg-green-100 px-3 py-2 t-small italic text-text-muted">The agent is thinking…</p>}
      </div>

      <div data-no-flip data-no-drag className="-mx-1 flex touch-pan-x gap-1.5 overflow-x-auto px-1 pb-0.5 scrollbar-thin">
        {back.questions.map((q) => (
          <button key={q} type="button" onClick={() => ask(q)} className="shrink-0 rounded-full bg-subtle px-3 py-2 t-small hover:bg-green-100">
            {q}
          </button>
        ))}
      </div>
      <form
        data-no-flip
        data-no-drag
        className="flex items-center gap-2 rounded-full bg-subtle py-1.5 pl-4 pr-1.5"
        onSubmit={(e) => {
          e.preventDefault();
          ask();
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about this card…"
          className="min-w-0 flex-1 select-text bg-transparent text-[16px] outline-none placeholder:text-text-muted sm:text-[13px]"
        />
        <button type="submit" aria-label="Send question" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-green-700 text-white hover:bg-green-900">
          <SendHorizontal className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}


/**
 * Layer over the card while it is dragged to one side: a soft green (right) or red (left) gradient
 * with the decision it will make, and how long to keep holding.
 */
function DecisionOverlay({ side, label, opacity, progress, armed, ready }) {
  const yes = side === 'yes';
  const width = useTransform(progress, (p) => `${p * 100}%`);
  const hint = ready ? 'Release to confirm' : armed ? 'Keep holding…' : `Drag further ${yes ? 'right' : 'left'} and hold`;
  return (
    <motion.div
      style={{ opacity }}
      className={cx(
        'pointer-events-none absolute inset-0 z-20 flex items-center overflow-hidden rounded-card p-5 sm:p-7',
        // The label sits on the side that stays on screen while the card slides away.
        yes
          ? 'justify-start bg-gradient-to-l from-status-green/80 via-status-green/45 to-status-green/10'
          : 'justify-end bg-gradient-to-r from-status-red/80 via-status-red/45 to-status-red/10',
      )}
      aria-hidden
    >
      <div
        className={cx(
          'flex w-[min(100%,280px)] flex-col gap-2 rounded-[22px] px-5 py-4 text-white shadow-card backdrop-blur-sm transition-colors',
          yes ? 'items-start text-left' : 'items-end text-right',
          ready ? (yes ? 'bg-status-green' : 'bg-status-red') : 'bg-ink/55',
        )}
      >
        <span className="t-overline opacity-90">
          {yes ? 'Yes · swipe right' : 'No · swipe left'}
        </span>
        <span className="font-display text-[22px] font-bold leading-tight sm:text-[26px]">{label}</span>
        <span className="relative mt-1 h-1.5 w-full overflow-hidden rounded-full bg-white/25">
          <motion.span className="absolute inset-y-0 left-0 rounded-full bg-white" style={{ width }} />
        </span>
        <span className="t-small opacity-90">{hint}</span>
      </div>
    </motion.div>
  );
}

/** After a drag, the browser may still send a click to the button under the finger: swallow it. */
function suppressNextClick() {
  const swallow = (e) => {
    e.stopPropagation();
    e.preventDefault();
  };
  window.addEventListener('click', swallow, { capture: true, once: true });
  setTimeout(() => window.removeEventListener('click', swallow, { capture: true }), 0);
}

/**
 * The card on the main screen. Works the same on the front and on the back:
 * - Tap: flip (front ↔ why).
 * - Press anywhere, drag left/right past the edge and keep holding for `holdMs`, then release: decision.
 *   Released too early, the card slides back to the middle and nothing happens.
 * `progress` (0..1) is the hold progress shown on the overlay.
 */
export default function DecisionCard({ card, flipped, onFlip, onDecide, holdMs, progress }) {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-320, 320], [-12, 12]);
  const yesOpacity = useTransform(x, [15, 90], [0, 1]);
  const noOpacity = useTransform(x, [-90, -15], [1, 0]);
  const dragControls = useDragControls();
  const [ready, setReady] = useState(false);
  const [armedDir, setArmedDir] = useState(0);
  const armed = useRef(0);
  const armedAt = useRef(0);
  const buzzed = useRef(false);
  const raf = useRef(0);
  const dragging = useRef(false);

  useMotionValueEvent(progress, 'change', (p) => setReady(p >= 1));

  const loop = (now) => {
    if (!dragging.current) return;
    const p = armed.current ? Math.min(1, (now - armedAt.current) / holdMs) : 0;
    progress.set(p);
    if (p >= 1 && !buzzed.current) {
      buzzed.current = true;
      navigator.vibrate?.(15);
    }
    raf.current = requestAnimationFrame(loop);
  };

  // The decision is tracked from plain pointer events (not animation frames), so it is exact
  // even when the browser skips frames: past the edge for `holdMs`, then released = decided.
  const stopTracking = useRef(() => {});
  const startTracking = (e) => {
    if (e.button > 0) return;
    const target = e.target;
    if (target.closest?.(NO_DRAG)) return;

    dragControls.start(e);
    const startX = e.clientX;
    const startY = e.clientY;
    let moved = false;
    dragging.current = true;
    armed.current = 0;
    buzzed.current = false;
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(loop);

    const move = (ev) => {
      const dx = ev.clientX - startX;
      if (Math.abs(dx) > TAP_SLOP || Math.abs(ev.clientY - startY) > TAP_SLOP) moved = true;
      const dir = dx > SWIPE_X ? 1 : dx < -SWIPE_X ? -1 : 0;
      if (dir === armed.current) return;
      armed.current = dir;
      armedAt.current = performance.now();
      buzzed.current = false;
      setArmedDir(dir);
    };
    const end = (ev) => {
      stopTracking.current();
      const dir = armed.current;
      const released = ev.type === 'pointerup';
      const commit = released && dir !== 0 && performance.now() - armedAt.current >= holdMs;
      armed.current = 0;
      setArmedDir(0);
      progress.set(0);
      if (moved) suppressNextClick();
      if (commit) onDecide(dir > 0 ? 'approve' : 'decline', { x: dir, y: 0 });
      else if (released && !moved && !target.closest?.(NO_FLIP)) onFlip();
    };
    stopTracking.current = () => {
      dragging.current = false;
      cancelAnimationFrame(raf.current);
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', end);
      window.removeEventListener('pointercancel', end);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', end);
    window.addEventListener('pointercancel', end);
  };

  useEffect(
    () => () => {
      stopTracking.current();
      cancelAnimationFrame(raf.current);
    },
    [],
  );

  return (
    <motion.div
      className="absolute inset-0 cursor-grab touch-pan-y select-none active:cursor-grabbing"
      style={{ x, rotate, perspective: 1600 }}
      drag="x"
      dragControls={dragControls}
      dragListener={false}
      dragSnapToOrigin
      dragElastic={0.75}
      dragMomentum={false}
      onPointerDown={startTracking}
    >
      <motion.div className="relative h-full w-full preserve-3d" animate={{ rotateY: flipped ? 180 : 0 }} transition={{ type: 'spring', stiffness: 200, damping: 24 }}>
        <div className="absolute inset-0 backface-hidden">
          <CardFace card={card} onWhy={onFlip} />
        </div>
        <Back card={card} onFlip={onFlip} />
      </motion.div>
      <DecisionOverlay side="yes" label={card.right} opacity={yesOpacity} progress={progress} armed={armedDir > 0} ready={ready && armedDir > 0} />
      <DecisionOverlay side="no" label={card.left} opacity={noOpacity} progress={progress} armed={armedDir < 0} ready={ready && armedDir < 0} />
    </motion.div>
  );
}
