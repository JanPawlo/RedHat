import { DATE_LOCALE, DEFAULT_CURRENCY, MONEY_LOCALE } from '../const/format.js';

const shortDate = new Intl.DateTimeFormat(DATE_LOCALE, { day: 'numeric', month: 'short' });

export function formatMoney(amount, currency = DEFAULT_CURRENCY) {
  return new Intl.NumberFormat(MONEY_LOCALE, { style: 'currency', currency, maximumFractionDigits: 0 }).format(Number(amount));
}

export function formatSignedMoney(amount, currency = DEFAULT_CURRENCY) {
  const value = Number(amount);
  const sign = value > 0 ? '+' : '';
  return `${sign}${formatMoney(value, currency)}`;
}

export function formatShortDate(isoDate) {
  return shortDate.format(new Date(`${isoDate}T00:00:00`));
}

export function formatCompactMoney(amount) {
  return `${Math.round(Number(amount) / 1000)}k`;
}
