import React, { useEffect, useRef, useState } from 'react';
import { motion, useMotionValue, useTransform } from 'framer-motion';
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, FileText, Maximize2, SendHorizontal, Sparkles } from 'lucide-react';
import { apiFetch } from '../../api/client.js';
import Icon from '../ui/Icon.jsx';
import { Button, Chip } from '../ui/primitives.jsx';
import { cx } from '../../utils/format.js';

export const CARD_W = 360;
export const CARD_H = 536;
// Size of the card in the focus layer (bigger, so the back side needs no scrolling).
export const LARGE_W = 520;
export const LARGE_H = 780;
const SWIPE_X = 130;
const SWIPE_Y = 110;

/** Approve button that needs a press-and-hold for money-moving actions (friction for big amounts). */
export function HoldButton({ children, onConfirm, className }) {
  const [progress, setProgress] = useState(0);
  const raf = useRef(0);
  const start = useRef(0);
  const HOLD_MS = 900;

  const stop = () => {
    cancelAnimationFrame(raf.current);
    setProgress(0);
  };
  const tick = (now) => {
    const p = Math.min(1, (now - start.current) / HOLD_MS);
    setProgress(p);
    if (p >= 1) {
      stop();
      onConfirm();
      return;
    }
    raf.current = requestAnimationFrame(tick);
  };
  const begin = (e) => {
    e.preventDefault();
    start.current = performance.now();
    raf.current = requestAnimationFrame(tick);
  };
  useEffect(() => () => cancelAnimationFrame(raf.current), []);

  return (
    <button
      type="button"
      onPointerDown={begin}
      onPointerUp={stop}
      onPointerLeave={stop}
      onPointerCancel={stop}
      className={cx('relative inline-flex select-none items-center justify-center gap-2 overflow-hidden rounded-full bg-green-700 px-[18px] py-[11px] t-small text-white', className)}
      title="Press and hold to approve"
    >
      <span className="absolute inset-y-0 left-0 bg-green-900" style={{ width: `${progress * 100}%` }} aria-hidden />
      <span className="relative flex items-center gap-2">
        {progress > 0 ? 'Keep holding…' : children}
        <ArrowRight className="h-4 w-4" strokeWidth={2} />
      </span>
    </button>
  );
}

function Front({ card, onDecide, onFlip, onLater, onEnlarge, large }) {
  const hint = card.recommendation === 'right' ? `I'd swipe right · ${card.confidence}% confident` : `I'd swipe left · ${card.confidence}% confident`;
  return (
    <div className={cx('absolute inset-0 flex flex-col items-center rounded-card bg-surface shadow-card backface-hidden', large ? 'justify-center gap-6 p-10' : 'gap-3.5 p-[22px]')}>
      <div className={cx('flex w-full items-center justify-between gap-2', large && 'absolute inset-x-10 top-8 w-auto')}>
        <Chip dot={false}>{card.bankProduct ? `${card.category} · COMMERZBANK` : card.category}</Chip>
        <Chip tone="amber">{card.autonomy}</Chip>
      </div>
      <span className={cx('mt-1.5 flex shrink-0 items-center justify-center rounded-full bg-green-100 ring-[6px] ring-green-200', large ? 'h-[140px] w-[140px]' : 'h-[104px] w-[104px]')}>
        <Icon name={card.icon} className={cx('text-green-700', large ? 'h-16 w-16' : 'h-11 w-11')} />
      </span>
      <h3 className={cx('mt-1 text-center t-display-l', large && '!text-[32px]')}>{card.title}</h3>
      <Chip tone="green">{hint}</Chip>
      <div className={cx('w-full rounded-[18px] bg-subtle text-center', large ? 'px-6 py-5' : 'px-4 py-3.5')}>
        <p className={cx('t-body', large && '!text-[17px]')}>{card.proposal}</p>
      </div>
      {!large && (
      <>
      <div className="flex-1" />
      <div className="flex w-full gap-2.5">
        <Button kind="danger" icon={ArrowLeft} className="flex-1 whitespace-nowrap !px-3" onClick={() => onDecide('decline')}>
          {card.left}
        </Button>
        {card.holdToConfirm ? (
          <HoldButton className="flex-1 whitespace-nowrap !px-3" onConfirm={() => onDecide('approve')}>{card.right}</HoldButton>
        ) : (
          <Button kind="primary" iconRight={ArrowRight} className="flex-1 whitespace-nowrap !px-3" onClick={() => onDecide('approve')}>
            {card.right}
          </Button>
        )}
      </div>
      <div className="flex items-center gap-5">
        <button type="button" onClick={onFlip} className="flex items-center gap-1 t-small text-text-muted hover:text-text">
          <ArrowUp className="h-3.5 w-3.5" /> Ask why
        </button>
        <button type="button" onClick={onLater} className="flex items-center gap-1 t-small text-text-muted hover:text-text">
          <ArrowDown className="h-3.5 w-3.5" /> Later
        </button>
        {onEnlarge && (
          <button type="button" onClick={onEnlarge} className="flex items-center gap-1 t-small text-text-muted hover:text-text">
            <Maximize2 className="h-3.5 w-3.5" /> Enlarge
          </button>
        )}
      </div>
      </>
      )}
    </div>
  );
}

function MiniForecast({ back, scale = 1 }) {
  const [ifSwipe, setIfSwipe] = useState(false);
  const weeks = ifSwipe ? back.weeksIfApproved : back.weeks;
  const lowest = Math.min(...weeks);
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="t-small text-text-muted">Cash · next 8 weeks</span>
        <button type="button" onClick={() => setIfSwipe((v) => !v)} className="t-small text-green-700 hover:underline">
          <span className={cx(!ifSwipe && 'font-semibold')}>now</span> / <span className={cx(ifSwipe && 'font-semibold')}>if you swipe →</span>
        </button>
      </div>
      <div className="relative flex items-end justify-between" style={{ height: 70 * scale }}>
        {weeks.map((v, i) => {
          const low = v === lowest;
          const near = !low && v < back.bufferLevel + 8;
          return (
            <motion.span
              key={i}
              layout
              className={cx('rounded-b-[3px] rounded-t-lg', low ? 'bg-status-red' : near ? 'bg-status-amber' : 'bg-green-200')}
              style={{ width: 30 * scale }}
              animate={{ height: v * scale }}
              transition={{ type: 'spring', stiffness: 260, damping: 26 }}
            />
          );
        })}
        <span className="absolute inset-x-0 h-[1.5px] bg-text/50" style={{ bottom: back.bufferLevel * scale }} title="Safety buffer" />
      </div>
    </div>
  );
}

const SYSTEM_PROMPT =
  'You are an Autonomous CFO assistant for small and medium-sized business owners. ' +
  'Explain financial recommendations in simple, friendly, plain language without corporate jargon. ' +
  'STRICT RULE: Never invent or calculate any numbers yourself. Use ONLY the exact numbers provided in FACTS. ' +
  'Keep your answer concise (2-3 short sentences).';

// The first "why" answer per card, shared by the small and the enlarged card so the model is asked once.
const explanationCache = new Map();

function cleanLlmOutput(text) {
  if (!text) return '';
  return text.replace(/<think>[\s\S]*?<\/think>/gi, '').replace(/<\/?think>/gi, '').trim();
}

async function askRHOAIModel(card, question) {
  const facts = {
    title: card.title,
    category: card.category,
    autonomy: card.autonomy,
    recommendation: card.recommendation === 'right' ? card.right : card.left,
    confidence_percent: card.confidence,
    proposal_summary: card.proposal,
    context_description: card.back?.description,
    deterministic_facts: Object.fromEntries(card.back?.facts || []),
    sources: card.back?.sources,
  };

  const modelId = 'qwen3-8b';

  // 1. Direct fast path via Vite /vllm proxy to OpenShift AI port-forward (127.0.0.1:8080)
  try {
    const vllmRes = await fetch('/vllm/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: modelId,
        temperature: 0.2,
        max_tokens: 150,
        chat_template_kwargs: { enable_thinking: false },
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          {
            role: 'user',
            content: `FACTS:\n${JSON.stringify(facts)}\n\nQUESTION:\n${question}`,
          },
        ],
      }),
    });

    if (vllmRes.ok) {
      const vllmData = await vllmRes.json();
      const raw = vllmData.choices?.[0]?.message?.content?.trim() || 'No response from model.';
      return { answer: cleanLlmOutput(raw) || raw, model: modelId };
    }
  } catch {
    // Fallback to FastAPI backend if /vllm proxy is not used
  }

  // 2. Fallback: FastAPI backend (/api/v1/ai/explain)
  const data = await apiFetch('/ai/explain', { method: 'POST', body: { facts, question } });
  return { answer: cleanLlmOutput(data.answer), model: data.model || modelId };
}

function Back({ card, flipped, onDecide, onFlip, large }) {
  const { back } = card;
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(false);
  const [liveExplanation, setLiveExplanation] = useState('');
  const [activeModel, setActiveModel] = useState('qwen3-8b');
  const [loadingInitial, setLoadingInitial] = useState(false);
  const scroller = useRef(null);

  const fetchedForCardRef = useRef(null);

  useEffect(() => {
    setMessages([]);
    setLiveExplanation('');
    setLoadingInitial(false);
    fetchedForCardRef.current = null;
  }, [card.id]);

  useEffect(() => {
    if (!flipped || fetchedForCardRef.current === card.id) return;
    fetchedForCardRef.current = card.id;
    if (explanationCache.has(card.id)) {
      setLiveExplanation(explanationCache.get(card.id));
      return undefined;
    }
    let cancelled = false;
    setLoadingInitial(true);
    askRHOAIModel(
      card,
      `Why do you recommend "${card.right}" for "${card.title}" and how does it affect our cash and safety buffer?`
    )
      .then(({ answer, model }) => {
        explanationCache.set(card.id, answer);
        if (!cancelled) {
          setLiveExplanation(answer);
          if (model) setActiveModel(model);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLiveExplanation(
            `${back.description} (RHOAI model offline — make sure oc port-forward on port 8080 is active.)`
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingInitial(false);
      });
    return () => {
      cancelled = true;
    };
  }, [flipped, card.id]);

  const ask = async (q) => {
    const text = (q ?? draft).trim();
    if (!text || loading) return;
    setDraft('');
    setMessages((m) => [...m, { role: 'user', text }]);
    setLoading(true);
    try {
      const { answer, model } = await askRHOAIModel(card, text);
      if (model) setActiveModel(model);
      setMessages((m) => [...m, { role: 'ai', text: answer }]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: 'ai',
          text: 'Could not reach model on OpenShift AI. Check if oc port-forward on port 8080 is running.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading, liveExplanation]);

  return (
    <div className={cx('absolute inset-0 flex flex-col rounded-card bg-surface shadow-card backface-hidden [transform:rotateY(180deg)]', large ? 'gap-4 p-8' : 'gap-3 p-[22px]')}>
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2">
          <Sparkles className="h-[18px] w-[18px] text-green-700" strokeWidth={1.8} />
          <span className="t-title">Why I suggest this</span>
        </span>
        <button type="button" onClick={onFlip} className="rounded-full bg-subtle px-2.5 py-1 t-small text-text-muted hover:bg-line hover:text-text">
          Back
        </button>
      </div>

      <div ref={scroller} className="-mr-2 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-2 scrollbar-thin">
        <div className="rounded-2xl bg-green-100/70 px-3.5 py-2.5">
          <div className="mb-1 flex items-center justify-between">
            <span className="t-small font-semibold text-green-700">OpenShift AI · {activeModel}</span>
          </div>
          {loadingInitial ? (
            <p className="t-small italic text-text-muted">Generating explanation from OpenShift AI…</p>
          ) : (
            <p className={cx('text-text', large ? 't-body' : 't-small')}>{liveExplanation || back.description}</p>
          )}
        </div>
        <dl>
          {back.facts.map(([k, v]) => (
            <div key={k} className="flex items-center justify-between border-b border-line py-2">
              <dt className="t-small text-text-muted">{k}</dt>
              <dd className="t-mono">{v}</dd>
            </div>
          ))}
        </dl>
        <MiniForecast back={back} scale={large ? 1.3 : 1} />
        <p className="flex items-center gap-1.5 t-small text-text-muted">
          <FileText className="h-3.5 w-3.5" /> {back.sources}
        </p>
        {messages.map((m, i) => (
          <p key={i} className={cx('max-w-[90%] rounded-2xl px-3 py-2 t-small', m.role === 'user' ? 'self-end bg-green-700 text-white' : 'self-start bg-green-100 text-text')}>
            {m.text}
          </p>
        ))}
        {loading && (
          <p className="max-w-[90%] self-start rounded-2xl bg-green-100 px-3 py-2 t-small italic text-text-muted">
            Asking {activeModel}…
          </p>
        )}
      </div>

      <div className={cx('-mx-1 flex gap-1.5 px-1 pb-0.5', large ? 'flex-wrap' : 'overflow-x-auto scrollbar-thin')}>
        {back.questions.map((q) => (
          <button key={q} type="button" onClick={() => ask(q)} className="shrink-0 rounded-full bg-subtle px-3 py-1.5 t-small hover:bg-green-100">
            {q}
          </button>
        ))}
      </div>
      <form
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
          className="min-w-0 flex-1 bg-transparent t-small outline-none placeholder:text-text-muted"
          data-card-input
        />
        <button type="submit" aria-label="Send question" className="flex h-[34px] w-[34px] items-center justify-center rounded-full bg-green-700 text-white hover:bg-green-900">
          <SendHorizontal className="h-4 w-4" />
        </button>
      </form>
      {!large && (
      <div className="flex gap-2">
        <Button kind="danger" size="sm" icon={ArrowLeft} className="flex-1 whitespace-nowrap" onClick={() => onDecide('decline')}>{card.left}</Button>
        {card.holdToConfirm ? (
          <HoldButton className="flex-1 whitespace-nowrap !px-3 !py-2" onConfirm={() => onDecide('approve')}>{card.right}</HoldButton>
        ) : (
          <Button kind="primary" size="sm" iconRight={ArrowRight} className="flex-1 whitespace-nowrap" onClick={() => onDecide('approve')}>{card.right}</Button>
        )}
      </div>
      )}
    </div>
  );
}

/**
 * Top card of the deck: drag left/right to decide, up to ask why (flip), down for later.
 * `onSwipe(choice, dir)` is called once the gesture or a button commits.
 */
export default function DecisionCard({ card, flipped, onFlip, onSwipe, onHoldHint, onTap, onEnlarge, large = false }) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotate = useTransform(x, [-320, 320], [-14, 14]);
  const yesOpacity = useTransform(x, [30, 120], [0, 1]);
  const noOpacity = useTransform(x, [-120, -30], [1, 0]);

  const handleDragEnd = (_, info) => {
    const { offset, velocity } = info;
    if (offset.x > SWIPE_X || velocity.x > 800) {
      if (card.holdToConfirm) onHoldHint();
      else onSwipe('approve', { x: 1, y: 0 });
    } else if (offset.x < -SWIPE_X || velocity.x < -800) onSwipe('decline', { x: -1, y: 0 });
    else if (offset.y < -SWIPE_Y) onFlip();
    else if (offset.y > SWIPE_Y) onSwipe('later', { x: 0, y: 1 });
  };

  return (
    <motion.div
      className="absolute left-0 top-0 cursor-grab touch-none active:cursor-grabbing"
      style={{ x, y, rotate, width: large ? LARGE_W : CARD_W, height: large ? LARGE_H : CARD_H, perspective: 1600, zIndex: 10 }}
      drag={!flipped}
      dragSnapToOrigin
      dragElastic={0.9}
      onDragEnd={handleDragEnd}
      whileDrag={{ scale: 1.02 }}
      onTap={(e) => {
        // A plain click on the card (not on its buttons or the chat input).
        if (onTap && !e.target.closest?.('button, input, form, a')) onTap();
      }}
    >
      <motion.div
        className="relative h-full w-full preserve-3d"
        animate={{ rotateY: flipped ? 180 : 0 }}
        transition={{ type: 'spring', stiffness: 200, damping: 24 }}
      >
        <Front card={card} large={large} onEnlarge={onEnlarge} onDecide={(c) => onSwipe(c, { x: c === 'approve' ? 1 : -1, y: 0 })} onFlip={onFlip} onLater={() => onSwipe('later', { x: 0, y: 1 })} />
        <Back card={card} flipped={flipped} large={large} onDecide={(c) => onSwipe(c, { x: c === 'approve' ? 1 : -1, y: 0 })} onFlip={onFlip} />
      </motion.div>
      {!flipped && (
        <>
          <motion.span style={{ opacity: yesOpacity }} className="pointer-events-none absolute left-6 top-16 -rotate-12 rounded-xl border-[3px] border-status-green px-3 py-1 font-display text-2xl font-black text-status-green">
            YES
          </motion.span>
          <motion.span style={{ opacity: noOpacity }} className="pointer-events-none absolute right-6 top-16 rotate-12 rounded-xl border-[3px] border-status-red px-3 py-1 font-display text-2xl font-black text-status-red">
            NO
          </motion.span>
        </>
      )}
    </motion.div>
  );
}
