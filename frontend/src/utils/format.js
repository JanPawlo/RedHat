const pln = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });

let displayCurrency = 'PLN';

/** Currency of the live data (set once the forecast is loaded); mock screens stay in PLN. */
export function setDisplayCurrency(code) {
  if (code) displayCurrency = code;
}

export function getDisplayCurrency() {
  return displayCurrency;
}

/** 14800 -> "14,800 PLN" (or the live data's currency) */
export function formatPLN(value, { sign = false } = {}) {
  const prefix = sign && value > 0 ? '+' : value < 0 ? '−' : '';
  return `${prefix}${pln.format(Math.abs(Math.round(value)))} ${displayCurrency}`;
}

/** 118400 -> "118k" */
export function formatK(value) {
  return `${Math.round(value / 1000)}k`;
}

export function cx(...parts) {
  return parts.filter(Boolean).join(' ');
}
