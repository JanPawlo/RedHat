import { FORECAST_ENDPOINT } from '../const/api.js';
import { apiFetch } from './client.js';

function withHorizon(path, horizonDays) {
  return horizonDays ? `${path}?horizon_days=${horizonDays}` : path;
}

export function getForecast(horizonDays) {
  return apiFetch(withHorizon(FORECAST_ENDPOINT, horizonDays));
}

export function previewAction(actionId, horizonDays) {
  return apiFetch(withHorizon(`${FORECAST_ENDPOINT}/actions/${actionId}/preview`, horizonDays));
}

export function simulateForecast(changes, horizonDays) {
  return apiFetch(withHorizon(`${FORECAST_ENDPOINT}/simulate`, horizonDays), { method: 'POST', body: { changes } });
}
