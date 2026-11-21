import { useSyncExternalStore } from 'react';
import { askAgent, whyQuestion } from '../api/agentApi.js';

/**
 * "Why" answers of the AI agent, one per card.
 * - Prefetched in the background for every card as soon as the app loads (2 requests at a time:
 *   one L4 GPU, so more in parallel only makes each answer slower).
 * - Persisted in localStorage per card id + a hash of the card's facts, so after a refresh the agent
 *   does not answer again or change its mind. If the card's data changes, the hash changes and the
 *   card is asked again.
 * - Failed answers are not stored, so the next start tries again.
 */

const STORAGE_KEY = 'redcaps.agent.v2';
const MODEL_SOURCE = 'model';
const CONCURRENCY = 2;

function hashCard(card) {
  const text = JSON.stringify([card.title, card.proposal, card.right, card.left, card.back?.facts, card.back?.description]);
  let h = 5381;
  for (let i = 0; i < text.length; i += 1) h = ((h << 5) + h + text.charCodeAt(i)) | 0;
  return (h >>> 0).toString(36);
}

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function persist(done) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(done));
  } catch {
    /* storage full or blocked: answers stay in memory for this session */
  }
}

// cardId -> { hash, answer, model, at }  (only finished answers)
const done = load();
// cardId -> 'queued' | 'loading' | 'error'
const pending = {};
const queue = [];
let running = 0;
const listeners = new Set();
let version = 0;

function emit() {
  version += 1;
  listeners.forEach((l) => l());
}

function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function cached(card) {
  const entry = done[card.id];
  return entry && entry.hash === hashCard(card) ? entry : null;
}

function pump() {
  while (running < CONCURRENCY && queue.length) {
    const card = queue.shift();
    running += 1;
    pending[card.id] = 'loading';
    emit();
    askAgent(card, whyQuestion(card))
      .then(({ answer, model, source }) => {
        if (source && source !== MODEL_SOURCE) {
          pending[card.id] = 'error';
          return;
        }

        done[card.id] = { hash: hashCard(card), answer, model, at: Date.now() };
        delete pending[card.id];
        persist(done);
      })
      .catch(() => {
        pending[card.id] = 'error';
      })
      .finally(() => {
        running -= 1;
        emit();
        pump();
      });
  }
}

/** Queue the cards that have no stored answer yet. `first` jumps the queue (the card the user is looking at). */
export function prefetchExplanations(cards, first) {
  const ordered = first ? [first, ...cards.filter((c) => c.id !== first.id)] : cards;
  ordered.forEach((card) => {
    if (!card || cached(card) || pending[card.id] === 'queued' || pending[card.id] === 'loading') return;
    pending[card.id] = 'queued';
    queue.push(card);
  });
  if (first) {
    const i = queue.findIndex((c) => c.id === first.id);
    if (i > 0) queue.unshift(...queue.splice(i, 1));
  }
  emit();
  pump();
}

/** Ask again for one card (after an error). */
export function retryExplanation(card) {
  delete pending[card.id];
  prefetchExplanations([card], card);
}

/** Stored answer for a card, if any (used when a decision is saved to History). */
export function getExplanation(card) {
  return cached(card);
}

/** `{ status: 'ready' | 'loading' | 'queued' | 'error' | 'idle', answer, model }` for one card. */
export function useExplanation(card) {
  useSyncExternalStore(subscribe, () => version);
  if (!card) return { status: 'idle' };
  const entry = cached(card);
  if (entry) return { status: 'ready', answer: entry.answer, model: entry.model };
  return { status: pending[card.id] || 'idle' };
}

/** Progress of the background analysis, for a small status line. */
export function useAgentProgress(cards) {
  useSyncExternalStore(subscribe, () => version);
  const ready = cards.filter((c) => cached(c)).length;
  const failed = cards.filter((c) => pending[c.id] === 'error').length;
  return { ready, failed, total: cards.length };
}

export function clearExplanations() {
  Object.keys(done).forEach((k) => delete done[k]);
  persist(done);
  emit();
}
