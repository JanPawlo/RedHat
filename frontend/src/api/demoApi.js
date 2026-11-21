import { DEMO_RESET_ENDPOINT } from '../const/api.js';
import { apiFetch } from './client.js';

export function resetDemo() {
  return apiFetch(DEMO_RESET_ENDPOINT, { method: 'POST' });
}
