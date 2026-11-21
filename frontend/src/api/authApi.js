import { AUTH_ENDPOINTS } from '../const/api.js';
import { apiFetch, saveToken } from './client.js';

async function authenticate(path, payload) {
  const data = await apiFetch(path, { method: 'POST', body: payload });
  saveToken(data.access_token);
  return data.user;
}

export function login(email, password) {
  return authenticate(AUTH_ENDPOINTS.login, { email, password });
}

export function register(email, password, fullName) {
  return authenticate(AUTH_ENDPOINTS.register, { email, password, full_name: fullName || null });
}

export function fetchCurrentUser() {
  return apiFetch(AUTH_ENDPOINTS.me);
}
