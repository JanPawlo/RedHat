const pln = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });

/** 14800 -> "14,800 PLN" */
export function formatPLN(value, { sign = false } = {}) {
  const prefix = sign && value > 0 ? '+' : value < 0 ? '−' : '';
  return `${prefix}${pln.format(Math.abs(Math.round(value)))} PLN`;
}

/** 118400 -> "118k" */
export function formatK(value) {
  return `${Math.round(value / 1000)}k`;
}

export function cx(...parts) {
  return parts.filter(Boolean).join(' ');
}
