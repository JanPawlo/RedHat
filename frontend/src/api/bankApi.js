import { BANK_CONNECTIONS_ENDPOINT } from '../const/api.js';
import { apiFetch } from './client.js';

export function fetchBankConnections() {
  return apiFetch(BANK_CONNECTIONS_ENDPOINT);
}

export function connectBank(bankId) {
  return apiFetch(`${BANK_CONNECTIONS_ENDPOINT}/${bankId}`, { method: 'POST' });
}

export function syncBank(bankId) {
  return apiFetch(`${BANK_CONNECTIONS_ENDPOINT}/${bankId}/sync`, { method: 'POST' });
}

export function disconnectBank(bankId) {
  return apiFetch(`${BANK_CONNECTIONS_ENDPOINT}/${bankId}`, { method: 'DELETE' });
}
