import { API_BASE, AUTH_SCHEME, CLIENT_ID_HEADER, CLIENT_ID_KEY, HTTP_NO_CONTENT, HTTP_UNAUTHORIZED, RETRY_AFTER_HEADER, TOKEN_KEY } from '../const/api.js';

let unauthorizedHandler = null;

export class ApiError extends Error {
  constructor(message, status, retryAfter = null) {
    super(message);
    this.status = status;
    this.retryAfter = retryAfter;
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

function readRetryAfter(res) {
  const seconds = Number(res.headers.get(RETRY_AFTER_HEADER));
  return Number.isFinite(seconds) && seconds > 0 ? seconds : null;
}

/**
 * A random id for this browser. People who share one login (the demo admin) get separate AI limits with it;
 * it is not a secret and not a security feature.
 */
let clientId = null;
function getClientId() {
  if (clientId) return clientId;
  try {
    clientId = localStorage.getItem(CLIENT_ID_KEY);
  } catch {
    clientId = null;
  }
  if (!clientId) {
    // crypto.randomUUID needs HTTPS; the cluster route is plain HTTP.
    clientId = Array.from({ length: 4 }, () => Math.random().toString(36).slice(2, 10)).join('-');
    try {
      localStorage.setItem(CLIENT_ID_KEY, clientId);
    } catch {
      // private mode: the id lives until the page is closed
    }
  }
  return clientId;
}

function buildHeaders(body, headers) {
  const result = { ...headers, [CLIENT_ID_HEADER]: getClientId() };

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
  if (!res.ok) throw new ApiError(await readError(res), res.status, readRetryAfter(res));

  if (res.status === HTTP_NO_CONTENT) return null;
  return res.json();
}
