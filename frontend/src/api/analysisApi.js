import { ANALYSIS_ENDPOINT } from '../const/api.js';
import { apiFetch } from './client.js';

export function getAnalysis() {
  return apiFetch(ANALYSIS_ENDPOINT);
}
