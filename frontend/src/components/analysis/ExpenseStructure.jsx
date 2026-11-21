import React, { useState } from 'react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { Sparkles } from 'lucide-react';
import { useAnalysis } from '../../state/analysisStore.js';
import { Bar, Insight } from '../ui/primitives.jsx';
import { cx, formatPLN } from '../../utils/format.js';

function share(amount, total) {
  return Math.round((amount / total) * 100);
}

function SliceTooltip({ active, payload, total }) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="rounded-2xl bg-surface p-3 shadow-card ring-1 ring-line">
      <p className="t-small font-semibold">{item.label}</p>
      <p className="t-small text-text-muted">
        {formatPLN(item.amount)} · {share(item.amount, total)}%
      </p>
    </div>
  );
}

/**
 * Where the money goes: expense categories as a donut (with the total in the middle) and a list.
 * `variant="bars"` shows only the list with bars; `stacked` keeps the donut above the list (narrow columns).
 */
export default function ExpenseStructure({ variant = 'donut', stacked = false, className }) {
  const { breakdown } = useAnalysis();
  const total = breakdown.items.reduce((s, i) => s + i.amount, 0);
  const max = Math.max(...breakdown.items.map((i) => i.amount));
  const [active, setActive] = useState(null);
  const donut = variant === 'donut';

  return (
    <section className={cx('card flex min-w-0 flex-col gap-4', className)} aria-label="Where the money goes">
      <div>
        <h2 className="t-title">Where the money goes</h2>
        <p className="t-small text-text-muted">
          Expenses by category · {breakdown.period} · {formatPLN(total)}
        </p>
      </div>

      <div className={cx('flex flex-col gap-5', donut && !stacked && 'md:flex-row md:items-center')}>
        {donut && (
          <div className="relative mx-auto h-[220px] w-[220px] shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={breakdown.items}
                  dataKey="amount"
                  nameKey="label"
                  innerRadius={68}
                  outerRadius={104}
                  paddingAngle={2}
                  cornerRadius={6}
                  stroke="none"
                  isAnimationActive={false}
                  onMouseEnter={(_, i) => setActive(i)}
                  onMouseLeave={() => setActive(null)}
                  onClick={(_, i) => setActive(i)}
                >
                  {breakdown.items.map((i, idx) => (
                    <Cell key={i.label} fill={i.hex} fillOpacity={active === null || active === idx ? 1 : 0.35} />
                  ))}
                </Pie>
                <Tooltip content={<SliceTooltip total={total} />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
              <span className="t-overline text-text-muted">{active === null ? 'Total' : breakdown.items[active].label}</span>
              <span className="t-title">{formatPLN(active === null ? total : breakdown.items[active].amount)}</span>
              {active !== null && <span className="t-small text-text-muted">{share(breakdown.items[active].amount, total)}%</span>}
            </div>
          </div>
        )}

        <ul className="flex min-w-0 flex-1 flex-col gap-2.5">
          {breakdown.items.map((i, idx) => (
            <li
              key={i.label}
              className={cx('flex flex-col gap-1.5 rounded-xl transition-opacity', active !== null && active !== idx && 'opacity-50')}
              onMouseEnter={() => setActive(idx)}
              onMouseLeave={() => setActive(null)}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="flex min-w-0 items-center gap-2 t-small">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: i.hex }} />
                  <span className="truncate">{i.label}</span>
                </span>
                <span className="shrink-0 t-small text-text-muted">
                  {formatPLN(i.amount)} · {share(i.amount, total)}%
                </span>
              </div>
              {!donut && <Bar pct={(i.amount / max) * 100} color={i.color} height={10} />}
            </li>
          ))}
        </ul>
      </div>

      <Insight icon={Sparkles}>{breakdown.insight}</Insight>
    </section>
  );
}
