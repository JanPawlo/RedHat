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
