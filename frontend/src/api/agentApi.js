import { apiFetch } from './client.js';

export const AGENT_MODEL = 'qwen3-8b';

const SYSTEM_PROMPT =
  'You are an Autonomous CFO assistant for small and medium-sized business owners. ' +
  'Explain financial recommendations in simple, friendly, plain language without corporate jargon. ' +
  'STRICT RULE: Never invent or calculate any numbers yourself. Use ONLY the exact numbers provided in FACTS. ' +
  'Keep your answer concise (2-3 short sentences).';

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

const ADVISOR_PROMPT =
  'You are the CFO advisor of a small business owner. You read FACTS (numbers from the forecast engine) and NOTES ' +
  "(the owner's own notes, voice messages and meeting summaries). Answer in plain, friendly language. " +
  'When the owner plans a purchase or expense: say when is the safest time to pay, based on the lowest balance and the safety buffer; ' +
  'warn about risks; and if the expense is large, ask them to confirm they really want it. ' +
  'STRICT RULE: use ONLY numbers that appear in FACTS or NOTES, never calculate or invent new ones. ' +
  'Answer in the language of the question. Keep it to 3-5 short sentences.';

/**
 * Sends one chat request to the open-weights model on OpenShift AI.
 * 1) vLLM directly through the Vite /vllm proxy (oc port-forward on 8080), 2) the backend explain endpoint.
 */
async function chat({ system, facts, question, history = [], maxTokens }) {
  try {
    const res = await fetch('/vllm/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: AGENT_MODEL,
        temperature: 0.2,
        max_tokens: maxTokens,
        chat_template_kwargs: { enable_thinking: false },
        messages: [
          { role: 'system', content: system },
          ...history,
          { role: 'user', content: `FACTS:\n${JSON.stringify(facts)}\n\nQUESTION:\n${question}` },
        ],
      }),
    });
    if (res.ok) {
      const data = await res.json();
      const raw = data.choices?.[0]?.message?.content?.trim() || '';
      const answer = cleanLlmOutput(raw) || raw;
      if (answer) return { answer, model: AGENT_MODEL };
    }
  } catch {
    // no port-forward: try the backend
  }
  const data = await apiFetch('/ai/explain', { method: 'POST', body: { facts, question } });
  const answer = cleanLlmOutput(data.answer);
  if (!answer) throw new Error('Empty answer from the model');
  return { answer, model: data.model || AGENT_MODEL };
}

/** Asks the model about one card. */
export function askAgent(card, question) {
  return chat({ system: SYSTEM_PROMPT, facts: cardFacts(card), question, maxTokens: 150 });
}

/**
 * General advisor chat: `facts` from the engine plus the owner's notes; `history` = earlier turns
 * as `{ role: 'user' | 'assistant', content }`.
 */
export function askAdvisor({ facts, question, history }) {
  return chat({ system: ADVISOR_PROMPT, facts, question, history, maxTokens: 320 });
}
