import { API_BASE, AUTH_SCHEME, HTTP_NO_CONTENT, HTTP_UNAUTHORIZED, TOKEN_KEY } from '../const/api.js';

let unauthorizedHandler = null;

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function saveToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* storage unavailable - session-only login */
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

async function readError(res) {
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail.map((d) => d.msg).join(', ');
    }
  } catch {
    /* non-JSON error */
  }
  return `Request failed (${res.status})`;
}

function buildHeaders(body, headers) {
  const result = { ...headers };

  const token = getToken();
  if (token) result.Authorization = `${AUTH_SCHEME} ${token}`;

  if (body !== undefined && !(body instanceof FormData)) {
    result['Content-Type'] = 'application/json';
  }

  return result;
}

function serializeBody(body) {
  if (body === undefined || body instanceof FormData) return body;
  return JSON.stringify(body);
}

function handleUnauthorized() {
  clearToken();
  if (unauthorizedHandler) unauthorizedHandler();
}

export async function apiFetch(path, { method = 'GET', body, headers = {}, base = API_BASE } = {}) {
  const res = await fetch(`${base}${path}`, {
    method,
    headers: buildHeaders(body, headers),
    body: serializeBody(body),
  });

  if (res.status === HTTP_UNAUTHORIZED) handleUnauthorized();
  if (!res.ok) throw new ApiError(await readError(res), res.status);

  if (res.status === HTTP_NO_CONTENT) return null;
  return res.json();
}
