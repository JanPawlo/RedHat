import { apiFetch } from './client.js';

export const AGENT_MODEL = 'qwen3-8b';

function cleanLlmOutput(text) {
  if (!text) return '';
  return text.replace(/<think>[\s\S]*?<\/think>/gi, '').replace(/<\/?think>/gi, '').trim();
}

/** Deterministic facts the model may use; the engine's numbers, never the model's. */
export function cardFacts(card) {
  return {
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
}

export function whyQuestion(card) {
  return `Why do you recommend "${card.right}" for "${card.title}" and how does it affect our cash and safety buffer?`;
}

/**
 * Sends one question to the backend. The system prompt and the guardrails (no illegal requests,
 * no prompt injection, personal and banking data masked) live on the server, so the browser never
 * talks to the model directly.
 */
async function chat(path, body) {
  const data = await apiFetch(path, { method: 'POST', body });
  const answer = cleanLlmOutput(data.answer);
  if (!answer) throw new Error('Empty answer from the model');
  return { answer, model: data.model || AGENT_MODEL, source: data.response_source };
}

/**
 * Asks the model about one card. Cards from the backend are explained from the forecast engine's facts
 * (server side, with a deterministic answer when the model is down); mock cards use the card's own facts.
 */
export async function askAgent(card, question) {
  if (card.backendId) return chat(`/actions/${card.backendId}/explain`, { question });

  return chat('/ai/explain', { facts: cardFacts(card), question });
}

/**
 * General advisor chat: `facts` from the engine plus the owner's notes; `history` = earlier turns
 * as `{ role: 'user' | 'assistant', content }`.
 */
export function askAdvisor({ facts, question, history }) {
  return chat('/ai/advisor', { facts, question, history });
}
