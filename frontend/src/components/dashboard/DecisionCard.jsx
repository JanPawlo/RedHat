import React, { useEffect, useRef, useState } from 'react';
import { animate, AnimatePresence, motion, useDragControls, useMotionValue, useMotionValueEvent, useTransform } from 'framer-motion';
import { Check, Copy, FileText, LineChart, Maximize2, Pointer, SendHorizontal, Sparkles } from 'lucide-react';
import { askAgent, AGENT_MODEL } from '../../api/agentApi.js';

// Earlier messages of this card's chat sent with each question (the backend keeps at most 8).
const CHAT_HISTORY_TURNS = 8;
import { useExplanation } from '../../state/agentStore.js';
import Icon from '../ui/Icon.jsx';
import { Chip } from '../ui/primitives.jsx';
import { OutcomeContent } from './DecisionOutcome.jsx';
import {
  CARD_RADIUS_PX,
  DESKTOP_GAP_PX,
  DRAG_ELASTIC,
  ENGAGE_AFTER_MS,
  LOCK_NUDGE_X,
  NUDGE_DURATION_S,
  NUDGE_EVERY_MS,
  NUDGE_X,
  PHONE_DRAG_SCALE,
  PHONE_DRAG_SHARE,
  PREVIEW_FULL_AT,
  PREVIEW_START,
  SWIPE_UP_MAX_MS,
  SWIPE_UP_Y,
  SWIPE_X,
  TAP_HINT_AFTER_MS,
  TAP_SLOP,
  WAVE_COUNT,
  WAVE_CYCLE_S,
  WAVE_GAP_S,
  WAVE_PRESS_SCALE,
  WAVE_REACH_PX,
  WAVE_RGB,
} from '../../const/cardMotion.js';
import { cx } from '../../utils/format.js';

// Elements that keep their own gestures: typing and the horizontal list of questions.
const NO_DRAG = 'input, textarea, select, [data-no-drag]';

/** True when the press lands on the scrollbar of a scrolling area (grabbing it must not drag the card). */
function onScrollbar(e) {
  const el = e.target;
  if (!(el instanceof HTMLElement) || el.scrollHeight <= el.clientHeight) return false;
  return e.clientX - el.getBoundingClientRect().left > el.clientWidth;
}
// Elements that handle a tap themselves, so the card does not flip.
const NO_FLIP = 'button, input, textarea, form, a, [data-no-flip]';
// The card side facing away from the user (phones and tablets only, see the flip in DecisionCard).
const HIDDEN_FACE = 'max-lg:pointer-events-none';

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

/** Opens the card in the large layer with all details. */
export function ExpandButton({ onClick, className }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-no-flip
      aria-label="Open the card with all details"
      title="Open the card with all details"
      className={cx('flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-subtle text-text-muted transition-colors hover:bg-line hover:text-text', className)}
    >
      <Maximize2 className="h-4 w-4" />
    </button>
  );
}

/** Card front: the matter to decide. Same look in the deck and in History. */
export function CardFace({ card, onWhy, onExpand, footer, compact = false, showProposal = true, className }) {
  return (
    <div className={cx('relative flex h-full flex-col items-center rounded-card bg-surface shadow-card', compact ? 'p-5' : 'p-5 sm:p-8 sm:[@media(max-height:860px)]:p-6', className)}>
      {/* Category, then the warning one line below; the expand button always stays in the top right corner. */}
      <div className={cx('relative flex w-full flex-col items-start gap-2', onExpand && 'pr-10')}>
        <Chip dot={false} className="max-w-full !whitespace-normal">{card.bankProduct ? `${card.category} · COMMERZBANK` : card.category}</Chip>
        {card.autonomy && <Chip tone="amber">{card.autonomy}</Chip>}
        {onExpand && <ExpandButton onClick={onExpand} className="absolute right-0 top-0" />}
      </div>
      {/* Scrolls (from the top) only when the card is too short for its content. */}
      <div className={cx('w-full', !compact && '-mx-1 min-h-0 flex-1 touch-pan-y overflow-y-auto px-1 scrollbar-thin')}>
        {/* The short-screen (max-height) sizes are for tablets and desktop only (sm:); phones keep their own smaller sizes. */}
        <div className={cx('flex min-h-full w-full flex-col items-center justify-center', compact ? 'gap-3 py-3' : 'gap-3 py-3 sm:gap-5 sm:[@media(max-height:860px)]:gap-3')}>
          <span
            className={cx(
              'flex shrink-0 items-center justify-center rounded-full bg-green-100 ring-[6px] ring-green-200',
              compact ? 'h-16 w-16' : 'h-[76px] w-[76px] sm:h-[120px] sm:w-[120px] sm:[@media(max-height:860px)]:!h-[96px] sm:[@media(max-height:860px)]:!w-[96px]',
            )}
          >
            <Icon name={card.icon} className={cx('text-green-700', compact ? 'h-7 w-7' : 'h-9 w-9 sm:h-14 sm:w-14 sm:[@media(max-height:860px)]:!h-11 sm:[@media(max-height:860px)]:!w-11')} />
          </span>
          <h3
            className={cx(
              'max-w-[420px] text-balance text-center font-display font-bold leading-tight',
              compact ? 'text-[20px]' : 'text-[22px] sm:text-[30px] sm:[@media(max-height:860px)]:!text-[26px]',
            )}
          >
            {card.title}
          </h3>
          <ConfidenceChip card={card} onClick={onWhy} />
          {showProposal && (
          <div className={cx('w-full max-w-[440px] rounded-[18px] bg-subtle text-center', compact ? 'px-4 py-3' : 'px-4 py-3.5 sm:px-6 sm:py-5 sm:[@media(max-height:860px)]:!py-3')}>
            <p className={cx('t-body', !compact && 'sm:!text-[16px] sm:[@media(max-height:860px)]:!text-[15px]')}>{card.proposal}</p>
          </div>
          )}
        </div>
      </div>
      {footer}
    </div>
  );
}

/** On the card back: opens the large card, where the 8-week cash chart for both decisions is. */
function ForecastLink({ onExpand }) {
  return (
    <button
      type="button"
      onClick={onExpand}
      className="flex items-center gap-3 rounded-2xl bg-subtle px-4 py-3 text-left transition-colors hover:bg-green-100"
    >
      <LineChart className="h-5 w-5 shrink-0 text-green-700" strokeWidth={1.8} />
      <span className="min-w-0 flex-1">
        <span className="block t-body-m">Cash in the next 8 weeks</span>
        <span className="block t-small text-text-muted">Chart: swipe left vs swipe right</span>
      </span>
      <Maximize2 className="h-4 w-4 shrink-0 text-text-muted" />
    </button>
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

/** Chat about one card with the model: messages, loading state and `ask`. */
function useCardChat(card) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => setMessages([]), [card.id]);

  const ask = async (q) => {
    const text = (q ?? draft).trim();
    if (!text || loading) return;
    setDraft('');
    setMessages((m) => [...m, { role: 'user', text }]);
    setLoading(true);
    try {
      const history = messages
        .filter((m) => !m.error)
        .slice(-CHAT_HISTORY_TURNS)
        .map((m) => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.text }));
      const { answer } = await askAgent(card, text, history);
      setMessages((m) => [...m, { role: 'ai', text: answer }]);
    } catch {
      setMessages((m) => [...m, { role: 'ai', error: true, text: 'Could not reach the model on OpenShift AI. Try again in a moment.' }]);
    } finally {
      setLoading(false);
    }
  };

  return { messages, draft, setDraft, loading, ask };
}

function ChatMessages({ chat }) {
  return (
    <>
      {chat.messages.map((m, i) => (
        <div
          key={i}
          data-no-flip
          className={cx('flex max-w-[90%] items-start gap-1 rounded-2xl px-3 py-2 t-small', m.role === 'user' ? 'self-end bg-green-700 text-white' : 'self-start bg-green-100 text-text')}
        >
          <span className="flex-1">{m.text}</span>
          {m.role === 'ai' && !m.error && <CopyButton text={m.text} className="-my-1.5 -mr-2" />}
        </div>
      ))}
      {chat.loading && <p className="max-w-[90%] self-start rounded-2xl bg-green-100 px-3 py-2 t-small italic text-text-muted">The agent is thinking…</p>}
    </>
  );
}

/** Suggested questions the owner has not asked yet (an asked one leaves the list). */
function openQuestions(card, chat) {
  const asked = new Set(chat.messages.filter((m) => m.role === 'user').map((m) => m.text));
  return card.back.questions.filter((q) => !asked.has(q));
}

/** Suggested questions and the input line. */
function ChatInput({ card, chat }) {
  const questions = openQuestions(card, chat);
  return (
    <>
      {questions.length > 0 && (
      <div data-no-flip data-no-drag className="-mx-1 flex touch-pan-x gap-1.5 overflow-x-auto px-1 pb-0.5 scrollbar-thin">
        {questions.map((q) => (
          <button key={q} type="button" onClick={() => chat.ask(q)} className="shrink-0 rounded-full bg-subtle px-3 py-2 t-small hover:bg-green-100">
            {q}
          </button>
        ))}
      </div>
      )}
      <form
        data-no-flip
        data-no-drag
        className="flex items-center gap-2 rounded-full bg-subtle py-1.5 pl-4 pr-1.5"
        onSubmit={(e) => {
          e.preventDefault();
          chat.ask();
        }}
      >
        <input
          value={chat.draft}
          onChange={(e) => chat.setDraft(e.target.value)}
          placeholder="Ask about this card…"
          className="min-w-0 flex-1 select-text bg-transparent text-[16px] outline-none placeholder:text-text-muted sm:text-[13px]"
        />
        <button type="submit" aria-label="Send question" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-green-700 text-white hover:bg-green-900">
          <SendHorizontal className="h-4 w-4" />
        </button>
      </form>
    </>
  );
}

/** The chat on its own (bottom of the large card): messages, suggested questions, input. */
export function CardChat({ card, className }) {
  const chat = useCardChat(card);
  const end = useRef(null);
  useEffect(() => {
    if (chat.messages.length) end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [chat.messages, chat.loading]);
  return (
    <section className={cx('flex flex-col gap-3 rounded-card bg-surface p-5 sm:p-7', className)} aria-label="Ask about this card">
      <span className="flex items-center gap-2">
        <Sparkles className="h-[18px] w-[18px] shrink-0 text-green-700" strokeWidth={1.8} />
        <span className="t-title">Ask about this card</span>
      </span>
      {(chat.messages.length > 0 || chat.loading) && (
        <div className="flex flex-col gap-3">
          <ChatMessages chat={chat} />
        </div>
      )}
      <ChatInput card={card} chat={chat} />
      <span ref={end} />
    </section>
  );
}

/**
 * Card back: the agent's answer, what it looked at and (with `chat`) a chat about this card.
 * Phones leave the chat out; it is at the bottom of the large card.
 */
export function Back({ card, onExpand, standalone = false, chat: withChat = true, className }) {
  const { back } = card;
  const chat = useCardChat(card);
  const scroller = useRef(null);

  useEffect(() => {
    scroller.current?.scrollTo({ top: 0 });
  }, [card.id]);

  // Scroll down only when the conversation grows; the back always opens at the top.
  useEffect(() => {
    if (chat.messages.length) scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: 'smooth' });
  }, [chat.messages, chat.loading]);

  return (
    <div
      className={cx(
        'flex flex-col gap-3 rounded-card bg-surface p-5 sm:p-7',
        standalone ? 'h-full min-h-0' : 'absolute inset-0 shadow-card backface-hidden [transform:rotateY(180deg)]',
        className,
      )}
    >
      {/* No Back button: a tap on the card flips it back. The expand button stays in the top right corner. */}
      <div className={cx('relative flex min-h-8 items-center', onExpand && 'pr-10')}>
        <span className="flex items-center gap-2">
          <Sparkles className="h-[18px] w-[18px] shrink-0 text-green-700" strokeWidth={1.8} />
          <span className="t-title">Why I suggest this</span>
        </span>
        {onExpand && <ExpandButton onClick={onExpand} className="absolute right-0 top-0" />}
      </div>

      <div ref={scroller} data-card-scroll className="-mr-2 flex min-h-0 flex-1 touch-pan-y flex-col gap-3 overflow-y-auto overscroll-contain pr-2 scrollbar-thin">
        <AgentAnswer card={card} />
        <dl>
          {back.facts.map(([k, v]) => (
            <div key={k} className="flex items-center justify-between gap-3 border-b border-line py-2">
              <dt className="t-small text-text-muted">{k}</dt>
              <dd className="text-right t-mono">{v}</dd>
            </div>
          ))}
        </dl>
        {onExpand && <ForecastLink onExpand={onExpand} />}
        <p className="flex items-center gap-1.5 t-small text-text-muted">
          <FileText className="h-3.5 w-3.5 shrink-0" /> {back.sources}
        </p>
        {withChat && <ChatMessages chat={chat} />}
      </div>

      {withChat && <ChatInput card={card} chat={chat} />}
    </div>
  );
}

/** An upward move, clearly more vertical than sideways. */
function isSwipeUp(dx, dy) {
  return dy < -SWIPE_UP_Y && Math.abs(dy) > Math.abs(dx) * 1.5;
}

/** The scrolling area under the finger is at its end (or does not scroll), so a flick up is not a scroll. */
function scrolledToEnd(target) {
  const area = target.closest?.('[data-card-scroll]');
  if (!area || area.scrollHeight <= area.clientHeight) return true;
  return area.scrollTop + area.clientHeight >= area.scrollHeight - 4;
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

/** Phone: colored glow on the side the card is dragged to (green right, red left). */
function glowShadow(v) {
  const strength = Math.min(1, Math.abs(v) / PREVIEW_FULL_AT);
  if (strength < 0.02) return '0 0 0 0 rgba(0,0,0,0)';
  const rgb = v > 0 ? '47,138,87' : '200,70,60';
  const offset = Math.sign(v) * Math.round(6 + strength * 14);
  return `${offset}px 0 ${Math.round(28 + strength * 22)}px ${Math.round(strength * 4)}px rgba(${rgb},${(0.2 + strength * 0.45).toFixed(2)})`;
}

/** Phone: while dragged, the card shows what the decision leads to instead of its normal face. */
function MobileOutcome({ card, x, progress, armedDir, ready }) {
  const yesOpacity = useTransform(x, [PREVIEW_START, PREVIEW_FULL_AT * 0.7], [0, 1]);
  const noOpacity = useTransform(x, [-PREVIEW_FULL_AT * 0.7, -PREVIEW_START], [1, 0]);
  return (
    <>
      {[
        ['yes', yesOpacity],
        ['no', noOpacity],
      ].map(([side, opacity]) => (
        <motion.div key={side} style={{ opacity }} className="pointer-events-none absolute inset-0 z-20 rounded-card bg-surface p-6" aria-hidden>
          <OutcomeContent compact side={side} card={card} progress={progress} armed={side === 'yes' ? armedDir > 0 : armedDir < 0} ready={ready} />
        </motion.div>
      ))}
    </>
  );
}

// Values for the CSS `tap-wave` / `tap-press` animations (index.css), taken from const/cardMotion.js.
const WAVE_CSS_VARS = {
  '--wave-cycle': `${WAVE_CYCLE_S}s`,
  '--wave-reach': `${WAVE_REACH_PX}px`,
  '--wave-radius-start': `${CARD_RADIUS_PX}px`,
  '--wave-radius-end': `${CARD_RADIUS_PX + WAVE_REACH_PX}px`,
  '--wave-rgb': WAVE_RGB,
  '--wave-press-scale': WAVE_PRESS_SCALE,
};

/** One soft wave: a card-shaped outline that grows from under the card edge and fades out (CSS `tap-wave`). */
function TapWave({ delay }) {
  return <span aria-hidden className="tap-wave" style={{ animationDelay: `${delay}s` }} />;
}

/** "Tap here": waves coming out from under the card, one after another. Rendered below the card faces. */
function TapWaves() {
  return (
    <motion.div style={WAVE_CSS_VARS} className="pointer-events-none absolute inset-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.6 }} aria-hidden>
      {Array.from({ length: WAVE_COUNT }, (_, i) => (
        <TapWave key={i} delay={i * WAVE_GAP_S} />
      ))}
    </motion.div>
  );
}

/**
 * The card on the main screen. Works the same on the front and on the back:
 * - Tap: flip (front ↔ why). Swipe up (either side) or the expand button: the large card with all details.
 * - Press anywhere, drag left/right past the edge and keep holding for `holdMs`, then release: decision.
 *   Released too early, the card slides back to the middle and nothing happens.
 * - `locked`: until the owner has looked at the back once, the card cannot be swiped (a hint says so).
 * While dragged, desktop shows the outcome in the side zones (the deck listens to `onDragX` / `onArmedChange`,
 * `onEngagedChange` fires after a short press so a plain tap does not flash them);
 * a phone switches the card to the outcome view with a colored glow.
 * `progress` (0..1) is the hold progress.
 */
export default function DecisionCard({ card, flipped, locked, onFlip, onExpand, onDecide, holdMs, progress, desktop, onDragX, onArmedChange, onEngagedChange }) {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-320, 320], [-12, 12]);
  // Phone: how far the finger is pulled sideways. The card itself moves only a little (PHONE_DRAG_SHARE)
  // and shrinks, so the YES / NO text stays on screen; the outcome view and the glow follow the finger.
  const pull = useMotionValue(0);
  const phoneScale = useTransform(pull, [-PREVIEW_FULL_AT, 0, PREVIEW_FULL_AT], [PHONE_DRAG_SCALE, 1, PHONE_DRAG_SCALE]);
  const boxShadow = useTransform(pull, glowShadow);
  // Whether the last press moved; a click after a moved press is not a tap.
  const pressMoved = useRef(false);
  const dragControls = useDragControls();
  const [ready, setReady] = useState(false);
  const [armedDir, setArmedDir] = useState(0);
  const armed = useRef(0);
  const armedAt = useRef(0);
  const buzzed = useRef(false);
  const raf = useRef(0);
  const dragging = useRef(false);
  const engageTimer = useRef(0);

  useMotionValueEvent(progress, 'change', (p) => setReady(p >= 1));
  useMotionValueEvent(x, 'change', (v) => onDragX?.(v));

  // Idle help: a tap hint while the card is locked, a sideways sway every 10 s once it can be swiped.
  const [tapHint, setTapHint] = useState(false);
  const root = useRef(null);
  const [dragLimit, setDragLimit] = useState(0);

  // Drag limits follow the card size (it changes with the window).
  useEffect(() => {
    const el = root.current;
    if (!el) return undefined;
    const update = () => setDragLimit(desktop ? el.offsetWidth + DESKTOP_GAP_PX : el.offsetWidth * PHONE_DRAG_SHARE);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [desktop]);
  useEffect(() => {
    let timer = 0;
    const nudge = () => {
      if (!dragging.current) animate(x, [0, -NUDGE_X, NUDGE_X, 0], { duration: NUDGE_DURATION_S, ease: 'easeInOut' });
      timer = setTimeout(nudge, NUDGE_EVERY_MS);
    };
    const restart = () => {
      clearTimeout(timer);
      setTapHint(false);
      if (locked) timer = setTimeout(() => setTapHint(true), TAP_HINT_AFTER_MS);
      else timer = setTimeout(nudge, NUDGE_EVERY_MS);
    };
    restart();
    window.addEventListener('pointerdown', restart);
    window.addEventListener('keydown', restart);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('pointerdown', restart);
      window.removeEventListener('keydown', restart);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locked]);

  const setArmed = (dir) => {
    setArmedDir(dir);
    onArmedChange?.(dir);
  };

  // Swiping a card whose back was not seen yet: show the same "tap here" waves instead of a text note.
  const showLockHint = () => setTapHint(true);

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
    pressMoved.current = false;
    if (target.closest?.(NO_DRAG) || onScrollbar(e)) {
      pressMoved.current = true;
      return;
    }

    const startX = e.clientX;
    const startY = e.clientY;
    let moved = false;
    let vertical = false;
    armed.current = 0;
    buzzed.current = false;

    if (!locked) {
      dragControls.start(e);
      dragging.current = true;
      cancelAnimationFrame(raf.current);
      raf.current = requestAnimationFrame(loop);
      // Front: show the NO / YES options after a short press, so a plain tap does not flash them.
      // Back: a press there is usually reading or scrolling, so they wait for a sideways move.
      clearTimeout(engageTimer.current);
      if (!flipped) engageTimer.current = setTimeout(() => !vertical && onEngagedChange?.(true), ENGAGE_AFTER_MS);
    }

    const move = (ev) => {
      const dx = ev.clientX - startX;
      const dy = ev.clientY - startY;
      if (!moved && (Math.abs(dx) > TAP_SLOP || Math.abs(dy) > TAP_SLOP)) {
        moved = true;
        pressMoved.current = true;
        vertical = Math.abs(dy) > Math.abs(dx);
        if (!locked) {
          // Scrolling never shows the options, even after a long press.
          clearTimeout(engageTimer.current);
          onEngagedChange?.(!vertical);
        }
      }
      if (locked || vertical) {
        if (locked && !vertical && Math.abs(dx) > LOCK_NUDGE_X) showLockHint();
        return;
      }
      if (!desktop) pull.set(dx);
      const dir = dx > SWIPE_X ? 1 : dx < -SWIPE_X ? -1 : 0;
      if (dir === armed.current) return;
      armed.current = dir;
      armedAt.current = performance.now();
      buzzed.current = false;
      setArmed(dir);
    };
    const end = (ev) => {
      stopTracking.current();
      const dir = armed.current;
      const released = ev.type === 'pointerup';
      const commit = !locked && released && dir !== 0 && performance.now() - armedAt.current >= holdMs;
      armed.current = 0;
      setArmed(0);
      progress.set(0);
      if (moved) suppressNextClick();
      if (commit) onDecide(dir > 0 ? 'approve' : 'decline', { x: dir, y: 0 });
      // Mouse: drag up (anywhere, either side) opens the large card. Fingers use `onTouchEnd`.
      else if (released && e.pointerType === 'mouse' && isSwipeUp(ev.clientX - startX, ev.clientY - startY)) onExpand?.();
      // A tap (no move) flips the card in `flipOnTap` (click), which iOS Safari delivers reliably.
    };
    stopTracking.current = () => {
      dragging.current = false;
      animate(pull, 0, { duration: 0.2 });
      clearTimeout(engageTimer.current);
      onEngagedChange?.(false);
      cancelAnimationFrame(raf.current);
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', end);
      window.removeEventListener('pointercancel', end);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', end);
    window.addEventListener('pointercancel', end);
  };

  // Phones: a quick flick up opens the large card. The back scrolls with normal moves; once it is
  // scrolled to the end, the next flick up opens the details.
  const touchStart = useRef(null);
  const onTouchStart = (e) => {
    const t = e.touches[0];
    touchStart.current = e.touches.length === 1 && !e.target.closest?.(NO_DRAG) ? { x: t.clientX, y: t.clientY, at: performance.now(), atEnd: scrolledToEnd(e.target) } : null;
  };
  const onTouchEnd = (e) => {
    const start = touchStart.current;
    touchStart.current = null;
    if (!start || !start.atEnd || performance.now() - start.at > SWIPE_UP_MAX_MS) return;
    const t = e.changedTouches[0];
    if (isSwipeUp(t.clientX - start.x, t.clientY - start.y)) onExpand?.();
  };

  const flipOnTap = (e) => {
    if (pressMoved.current || e.target.closest?.(NO_FLIP)) return;
    onFlip();
  };

  useEffect(
    () => () => {
      stopTracking.current();
      cancelAnimationFrame(raf.current);
      onDragX?.(0);
      onArmedChange?.(0);
      onEngagedChange?.(false);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  return (
    <motion.div
      className={cx('absolute inset-0 touch-pan-y select-none rounded-card', locked ? 'cursor-pointer' : 'cursor-grab active:cursor-grabbing')}
      style={{ x, rotate, perspective: 1600, boxShadow: desktop ? undefined : boxShadow, scale: desktop ? undefined : phoneScale }}
      drag={locked ? false : 'x'}
      dragControls={dragControls}
      dragListener={false}
      dragSnapToOrigin
      ref={root}
      dragConstraints={{ left: -dragLimit, right: dragLimit }}
      dragElastic={DRAG_ELASTIC}
      dragMomentum={false}
      onPointerDown={startTracking}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
      onClick={flipOnTap}
    >
      {/* Below the faces, so the waves seem to come from under the card. */}
      <AnimatePresence>{tapHint && <TapWaves key="tap-waves" />}</AnimatePresence>
      {/* While the waves run, the card shrinks by 1% each time a wave leaves it. */}
      <div style={WAVE_CSS_VARS} className={cx('relative h-full w-full preserve-3d', tapHint && 'tap-press')}>
      <motion.div className="relative h-full w-full preserve-3d" animate={{ rotateY: flipped ? 180 : 0 }} transition={{ type: 'spring', stiffness: 200, damping: 24 }}>
        {/* Phones (Safari) still hit-test the hidden face of a flipped card, so a tap landed on the invisible side:
            below lg the side facing away takes no touches. */}
        <div className={cx('absolute inset-0 backface-hidden', flipped && HIDDEN_FACE)}>
          <CardFace card={card} onWhy={onFlip} onExpand={onExpand} showProposal={false} />
        </div>
        <Back card={card} onExpand={onExpand} chat={desktop} className={cx(!flipped && HIDDEN_FACE)} />
      </motion.div>
      </div>
      {!desktop && <MobileOutcome card={card} x={pull} progress={progress} armedDir={armedDir} ready={ready && armedDir !== 0} />}
      <AnimatePresence>
        {tapHint && (
          <motion.div key="tap-hint" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="pointer-events-none absolute inset-0 z-30" role="status">
            <span className="absolute inset-x-0 bottom-5 flex justify-center">
              <span className="flex items-center gap-1.5 rounded-full bg-text-muted/90 px-3.5 py-1.5 t-small text-white shadow-soft">
                <Pointer className="h-4 w-4" /> Tap the card to see why
              </span>
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
