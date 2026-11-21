import { TODAY } from '../data/mockData.js';

/**
 * Monotone cubic (Fritsch–Carlson) interpolation of [day, value] key points into one value per day.
 * Monotone so the curve never dips below a key point (the lowest balance stays exactly the engine's number).
 */
export function interpolateDaily(points, days) {
  const n = points.length;
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  const d = xs.slice(0, -1).map((x, i) => (ys[i + 1] - ys[i]) / (xs[i + 1] - x));
  const m = ys.map((_, i) => (i === 0 ? d[0] : i === n - 1 ? d[n - 2] : d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2));
  for (let i = 0; i < n - 1; i++) {
    if (d[i] === 0) {
      m[i] = 0;
      m[i + 1] = 0;
      continue;
    }
    const a = m[i] / d[i];
    const b = m[i + 1] / d[i];
    const s = a * a + b * b;
    if (s > 9) {
      const t = 3 / Math.sqrt(s);
      m[i] = t * a * d[i];
      m[i + 1] = t * b * d[i];
    }
  }
  const out = [];
  for (let day = 0; day <= days; day++) {
    let i = xs.findIndex((x, idx) => idx < n - 1 && day >= x && day <= xs[idx + 1]);
    if (i === -1) i = n - 2;
    const h = xs[i + 1] - xs[i];
    const t = (day - xs[i]) / h;
    const t2 = t * t;
    const t3 = t2 * t;
    const v = (2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h * m[i + 1];
    out.push(Math.round(v * 10) * 100); // thousands -> PLN, rounded to 100
  }
  return out;
}

const dayFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });

export function dateForOffset(offset) {
  const d = new Date(TODAY);
  d.setDate(d.getDate() + offset);
  return d;
}

/** "This week" for 0, then the Monday each later week starts on, e.g. "7 Dec". */
export function weekLabel(index) {
  if (index === 0) return 'This week';
  const monday = new Date(TODAY);
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7) + index * 7);
  return dayFmt.format(monday);
}

export function labelForOffset(offset) {
  return offset === 0 ? 'Today' : dayFmt.format(dateForOffset(offset));
}

/** Rows for the forecast chart: baseline, after approved actions and the red "below buffer" band. */
export function buildForecastRows(keyPoints, days, buffer) {
  const base = interpolateDaily(keyPoints.baseline, days);
  const after = interpolateDaily(keyPoints.afterActions, days);
  return base.map((balance, day) => ({
    day,
    label: labelForOffset(day),
    balance,
    after: day >= 10 ? after[day] : null,
    gap: balance < buffer ? [balance, buffer] : null,
  }));
}

const DAY_MS = 86400000;
const TICK_STEP_DAYS = 15;
const Y_PADDING = 0.1;

function isoToDate(iso) {
  return new Date(`${iso}T00:00:00`);
}

/**
 * Rows for the live chart from the forecast engine: past balances (bank statement) with negative day offsets,
 * then the engine's daily forecast ("do nothing") and the line after the approved decisions.
 */
export function buildLiveRows(forecast, horizon, pastDays) {
  const buffer = Number(forecast.safety_buffer);
  const asOf = isoToDate(forecast.as_of);
  const offsetOf = (iso) => Math.round((isoToDate(iso) - asOf) / DAY_MS);
  const after = forecast.after_decisions?.days;
  const opening = Number(forecast.opening_balance);

  const past = (forecast.history || [])
    .map((point) => ({ day: offsetOf(point.day), iso: point.day, past: Number(point.balance) }))
    .filter((point) => point.day >= -pastDays && point.day < 0)
    .map((point) => ({ day: point.day, label: dayFmt.format(isoToDate(point.iso)), past: point.past, balance: null, after: null, gap: null }));

  const today = { day: 0, label: 'Today', past: opening, balance: opening, after: after ? opening : null, gap: null };

  const future = forecast.scenarios.base.days.slice(0, horizon).map((day, index) => {
    const balance = Number(day.balance);
    return {
      day: index + 1,
      label: dayFmt.format(isoToDate(day.day)),
      past: null,
      balance,
      after: after ? Number(after[index].balance) : null,
      gap: balance < buffer ? [balance, buffer] : null,
      drivers: day.drivers,
    };
  });

  return [...past, today, ...future];
}

export function liveTicks(pastDays, horizon) {
  const ticks = [];
  for (let day = -pastDays; day <= horizon; day += TICK_STEP_DAYS) ticks.push(day);
  if (!ticks.includes(0)) ticks.push(0);
  return ticks.sort((a, b) => a - b);
}

export function liveDomain(rows, buffer) {
  const values = rows.flatMap((row) => [row.past, row.balance, row.after]).filter((value) => value !== null && value !== undefined);
  const min = Math.min(buffer, ...values);
  const max = Math.max(buffer, ...values);
  const pad = (max - min) * Y_PADDING;
  return [Math.floor((min - pad) / 1000) * 1000, Math.ceil((max + pad) / 1000) * 1000];
}
