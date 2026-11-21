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

/**
 * Asks the open-weights model on OpenShift AI about one card.
 * 1) vLLM directly through the Vite /vllm proxy (oc port-forward on 8080), 2) the backend explain endpoint.
 */
export async function askAgent(card, question) {
  if (card.backendId) {
    const data = await apiFetch(`/actions/${card.backendId}/explain`, { method: 'POST', body: { question } });
    const answer = cleanLlmOutput(data.answer);
    if (!answer) throw new Error('Empty answer from the model');
    return { answer, model: data.model || AGENT_MODEL, source: data.response_source };
  }

  const facts = cardFacts(card);
  try {
    const res = await fetch('/vllm/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: AGENT_MODEL,
        temperature: 0.2,
        max_tokens: 150,
        chat_template_kwargs: { enable_thinking: false },
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
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
