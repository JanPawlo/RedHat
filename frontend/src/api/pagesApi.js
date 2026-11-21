import { PAGE_ENDPOINTS } from '../const/api.js';
import { apiFetch } from './client.js';

export const getInvoicesPage = () => apiFetch(PAGE_ENDPOINTS.invoices);
export const getCashCalendar = () => apiFetch(PAGE_ENDPOINTS.calendar);
export const getRiskPage = () => apiFetch(PAGE_ENDPOINTS.risk);
export const getAdvisorFacts = () => apiFetch(PAGE_ENDPOINTS.advisorFacts);
