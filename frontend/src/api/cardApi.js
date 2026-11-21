import { apiFetch } from './client.js';

const CARDS_ENDPOINT = '/cards';

/** Pending decision cards in the DecisionCard format, with the forecast engine's effect of each one. */
export function listCards() {
  return apiFetch(CARDS_ENDPOINT);
}

/** Lets the agents create cards from the current forecast (existing ones are kept). */
export function generateCards() {
  return apiFetch(`${CARDS_ENDPOINT}/generate`, { method: 'POST' });
}
