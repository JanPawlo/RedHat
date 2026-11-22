import { apiFetch } from './client.js';
import { HTTP_SERVICE_UNAVAILABLE, HTTP_TOO_MANY_REQUESTS } from '../const/api.js';
import { ADVISOR_MESSAGES } from '../const/advisor.js';

export const AGENT_MODEL = 'qwen3-8b';

const EXPLAIN_MODE = { card: 'card', advisor: 'advisor' };

/** True when the backend refused because of load (busy model or too many questions): worth retrying later. */
export function isAiLoadError(error) {
  return error?.status === HTTP_TOO_MANY_REQUESTS || error?.status === HTTP_SERVICE_UNAVAILABLE;
}

/** Text for the chat bubble: the server's own wording for 429 (it says how long to wait), friendly text otherwise. */
export function aiErrorMessage(error) {
  if (error?.status === HTTP_TOO_MANY_REQUESTS && error.message) return error.message;
  if (error?.status === HTTP_SERVICE_UNAVAILABLE && error.retryAfter) return ADVISOR_MESSAGES.modelBusy;
  return ADVISOR_MESSAGES.modelOffline;
}

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
 * Sends one chat request to the open-weights model on OpenShift AI through the backend
 * (JWT, system prompt and guardrails kept on the server: no illegal requests, no prompt injection,
 * personal and banking data masked). `history` = earlier turns as `{ role: 'user' | 'assistant', content }`.
 */
async function chat({ mode, facts, question, history = [] }) {
  const data = await apiFetch('/ai/explain', { method: 'POST', body: { mode, facts, question, history } });
  const answer = cleanLlmOutput(data.answer);
  if (!answer) throw new Error('Empty answer from the model');
  return { answer, model: data.model || AGENT_MODEL, source: data.response_source, guardrail: data.guardrail };
}

/**
 * Asks the model about one card; `history` = earlier turns of this card's chat, so follow-ups keep their context. Cards from the backend are explained from the forecast engine's facts
 * (server side, with a deterministic answer when the model is down); mock cards use the card's own facts.
 */
export async function askAgent(card, question, history = []) {
  if (card.backendId) {
    const data = await apiFetch(`/actions/${card.backendId}/explain`, { method: 'POST', body: { question, history } });
    const answer = cleanLlmOutput(data.answer);
    if (!answer) throw new Error('Empty answer from the model');
    return { answer, model: data.model || AGENT_MODEL, source: data.response_source, guardrail: data.guardrail };
  }

  return chat({ mode: EXPLAIN_MODE.card, facts: cardFacts(card), question, history });
}

/** General advisor chat: `facts` from the engine plus the owner's notes, `history` = earlier turns of this chat. */
export function askAdvisor({ facts, question, history }) {
  return chat({ mode: EXPLAIN_MODE.advisor, facts, question, history });
}
