import { HEALTH_URL } from '../const/api.js';
import { apiFetch } from './client.js';

export function checkHealth() {
  return apiFetch(HEALTH_URL, { base: '' });
}
