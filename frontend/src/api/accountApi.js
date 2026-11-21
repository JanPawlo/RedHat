import { ACCOUNTS_ENDPOINT } from '../const/api.js';
import { apiFetch } from './client.js';

export function listAccounts() {
  return apiFetch(ACCOUNTS_ENDPOINT);
}

export function getAccount(accountId) {
  return apiFetch(`${ACCOUNTS_ENDPOINT}/${accountId}`);
}
