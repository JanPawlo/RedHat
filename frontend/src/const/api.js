export const API_BASE = '/api/v1';
export const HEALTH_URL = '/api/health';
export const TOKEN_KEY = 'cfo_access_token';
export const AUTH_SCHEME = 'Bearer';
export const HTTP_UNAUTHORIZED = 401;
export const HTTP_NO_CONTENT = 204;

export const AUTH_ENDPOINTS = {
  login: '/auth/login',
  register: '/auth/register',
  me: '/auth/me',
};

export const COMPANY_ENDPOINT = '/company';
export const ACCOUNTS_ENDPOINT = '/accounts';
export const ACTIONS_ENDPOINT = '/actions';

export const ACTION_STATUS = {
  pending: 'pending',
  approved: 'approved',
  rejected: 'rejected',
};

export const API_STATUS = {
  checking: 'checking',
  connected: 'connected',
  offline: 'offline',
};

export const FORECAST_ENDPOINT = '/forecast';
export const DEMO_RESET_ENDPOINT = '/demo/reset';
export const ANALYSIS_ENDPOINT = '/analysis';

export const DECIDED_ACTION_STATUSES = [ACTION_STATUS.approved, ACTION_STATUS.rejected];
export const PAGE_ENDPOINTS = {
  invoices: '/analysis/invoices',
  calendar: '/analysis/calendar',
  risk: '/analysis/risk',
  advisorFacts: '/analysis/advisor-facts',
};

export const BANK_CONNECTIONS_ENDPOINT = '/bank-connections';
