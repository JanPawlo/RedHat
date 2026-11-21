import { COMPANY_ENDPOINT } from '../const/api.js';
import { apiFetch } from './client.js';

export function getCompanyProfile() {
  return apiFetch(COMPANY_ENDPOINT);
}

export function updateCompanyProfile(changes) {
  return apiFetch(COMPANY_ENDPOINT, { method: 'PUT', body: changes });
}
