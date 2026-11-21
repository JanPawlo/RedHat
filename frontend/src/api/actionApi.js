import { ACTIONS_ENDPOINT } from '../const/api.js';
import { apiFetch } from './client.js';

export function listActions({ status, agentType } = {}) {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (agentType) params.set('agent_type', agentType);

  const query = params.toString();
  return apiFetch(query ? `${ACTIONS_ENDPOINT}?${query}` : ACTIONS_ENDPOINT);
}

export function updateActionStatus(actionId, changes) {
  return apiFetch(`${ACTIONS_ENDPOINT}/${actionId}/update-status`, { method: 'POST', body: changes });
}

export function explainAction(actionId, question) {
  return apiFetch(`${ACTIONS_ENDPOINT}/${actionId}/explain`, {
    method: 'POST',
    body: question ? { question } : undefined,
  });
}
