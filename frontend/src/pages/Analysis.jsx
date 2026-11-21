import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Bar as RBar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ChevronRight, FileText, ShieldAlert, Sparkles } from 'lucide-react';
import { analysis, risk } from '../data/mockData.js';
import { Bar, Button, Chip, Insight, PageHeader, Segmented } from '../components/ui/primitives.jsx';
import Gauge from '../components/ui/Gauge.jsx';
import Icon from '../components/ui/Icon.jsx';
import { cx, formatK, formatPLN } from '../utils/format.js';

function KpiTile({ kpi }) {
  const hi = kpi.highlight;
  return (
    <div className={cx('flex flex-1 flex-col gap-1.5 rounded-tile p-5', hi ? 'bg-green-700' : 'bg-surface')}>
      <div className="flex items-center gap-2.5">
        <span className={cx('flex h-9 w-9 items-center justify-center rounded-full', hi ? 'bg-green-500 text-white' : 'bg-green-100 text-green-700')}>
          <Icon name={kpi.icon} className="h-4 w-4" />
        </span>
        <span className={cx('t-small', hi ? 'text-green-200' : 'text-text-muted')}>{kpi.label}</span>
      </div>
      <p className={cx('t-display-l', hi && 'text-white')}>{kpi.value}</p>
      <p className={cx('t-small', hi ? 'text-green-200' : 'text-text-muted')}>{kpi.sub}</p>
    </div>
  );
}

function MoneyTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const r = payload[0].payload;
  return (
    <div className="rounded-2xl bg-surface p-3 shadow-card ring-1 ring-line">
      <p className="t-overline text-text-muted">{label}{r.partial ? ' · so far' : ''}</p>
      <p className="t-small">Revenue <b>{formatPLN(r.revenue)}</b></p>
      <p className="t-small">Expenses <b>{formatPLN(r.expenses)}</b></p>
      <p className="t-small text-status-green">Profit {formatPLN(r.revenue - r.expenses)}</p>
    </div>
  );
}

function RevenueChart() {
  return (
    <section className="card flex min-w-0 flex-1 flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="t-title">Revenue vs expenses</h2>
          <p className="t-small text-text-muted">Last 6 months · PLN · November so far</p>
        </div>
        <div className="flex items-center gap-3.5">
          <span className="flex items-center gap-1.5 t-small text-text-muted"><span className="h-3 w-3 rounded bg-green-700" />Revenue</span>
          <span className="flex items-center gap-1.5 t-small text-text-muted"><span className="h-3 w-3 rounded bg-heat-3" />Expenses</span>
        </div>
      </div>
      <div className="h-[230px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={analysis.months} barGap={6} barCategoryGap="28%" margin={{ top: 8, right: 0, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="#E6E4DE" />
            <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fill: '#6B716C', fontSize: 13, fontFamily: 'Red Hat Text' }} dy={6} />
            <YAxis tickFormatter={formatK} ticks={[50000, 100000, 150000, 200000]} domain={[0, 200000]} tickLine={false} axisLine={false} width={40} tick={{ fill: '#6B716C', fontSize: 13, fontFamily: 'Red Hat Text' }} />
            <Tooltip content={<MoneyTooltip />} cursor={{ fill: '#E7EFE8', radius: 12 }} />
            <RBar dataKey="revenue" radius={[9, 9, 3, 3]} maxBarSize={26}>
              {analysis.months.map((m) => <Cell key={m.month} fill="#3F5E4A" fillOpacity={m.partial ? 0.65 : 1} />)}
            </RBar>
            <RBar dataKey="expenses" radius={[9, 9, 3, 3]} maxBarSize={26}>
              {analysis.months.map((m) => <Cell key={m.month} fill="#F3E9CF" fillOpacity={m.partial ? 0.65 : 1} />)}
            </RBar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap gap-3">
        {analysis.totals.map((t) => (
          <div key={t.label} className="flex flex-1 flex-col gap-1 rounded-[18px] bg-subtle px-4 py-3">
            <p className="t-small text-text-muted">{t.label}</p>
            <p className={cx('t-title', t.positive && 'text-status-green')}>{t.value}</p>
            <Chip tone={t.tone} dot={false} className="self-start">{t.chip}</Chip>
          </div>
        ))}
      </div>
    </section>
  );
}

function Breakdown() {
  const { breakdown } = analysis;
  const max = Math.max(...breakdown.items.map((i) => i.pct));
  return (
    <section className="card flex w-[368px] shrink-0 flex-col gap-3.5">
      <div>
        <h2 className="t-title">Where the money goes</h2>
        <p className="t-small text-text-muted">November expenses · {breakdown.total}</p>
      </div>
      {breakdown.items.map((i) => (
        <div key={i.label} className="flex flex-col gap-1.5">
          <div className="flex justify-between">
            <span className="t-small">{i.label}</span>
            <span className="t-small text-text-muted">{i.amount} PLN · {i.pct}%</span>
          </div>
          <Bar pct={(i.pct / max) * 100} color={i.color} height={10} />
        </div>
      ))}
      <div className="flex-1" />
      <Insight icon={Sparkles}>{breakdown.insight}</Insight>
    </section>
  );
}

function TeamTable() {
  return (
    <section className="card flex min-w-0 flex-1 flex-col gap-1">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="t-title">Team & payroll</h2>
          <p className="t-small text-text-muted">Who works, who is off, and what leaves on payday</p>
        </div>
        <Chip tone="dark" dot={false}>Payday 10 Dec</Chip>
      </div>
      <table className="w-full border-separate border-spacing-0">
        <thead>
          <tr className="text-left">
            {['Name', 'Role', 'Status', 'This month'].map((h, i) => (
              <th key={h} className={cx('bg-subtle px-3 py-2 t-overline text-text-muted', i === 0 && 'rounded-l-xl', i === 3 && 'rounded-r-xl text-right')}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {analysis.team.map((p) => (
            <tr key={p.name}>
              <td className="border-b border-line px-3 py-2.5 t-body-m">{p.name}</td>
              <td className="border-b border-line px-3 py-2.5 t-small">{p.role}</td>
              <td className="border-b border-line px-3 py-2.5"><Chip tone={p.tone}>{p.status}</Chip></td>
              <td className="whitespace-nowrap border-b border-line px-3 py-2.5 text-right t-small">{p.pay}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center justify-between px-3 py-3">
        <button type="button" className="t-small text-green-700 hover:underline">+ {analysis.teamMore} more people</button>
        <span className="t-body-m">Total {analysis.teamTotal}</span>
      </div>
      <Insight tone="amber" icon={Sparkles}>{analysis.teamInsight}</Insight>
    </section>
  );
}

function InvoiceGauge() {
  const g = analysis.invoiceGauge;
  return (
    <section className="card flex w-[368px] shrink-0 flex-col gap-3.5">
      <div>
        <h2 className="t-title">Invoices</h2>
        <p className="t-small text-text-muted">November · paid vs still to pay</p>
      </div>
      <Gauge pct={g.paidPct}>
        <p className="t-display-xl">{g.paidPct}%</p>
        <p className="t-small text-text-muted">paid · {g.paidCount} of {g.totalCount}</p>
      </Gauge>
      {g.rows.map((r) => (
        <div key={r.label} className="flex items-center gap-2">
          <span className={cx('h-2.5 w-2.5 rounded-full', r.color)} />
          <span className="flex-1 t-small">{r.label}</span>
          <span className="t-mono">{r.amount}</span>
        </div>
      ))}
      <div className="flex-1" />
      <Link to="/invoices">
        <Button className="w-full" iconRight={ChevronRight}>Open pending invoices</Button>
      </Link>
    </section>
  );
}

export default function Analysis() {
  const [period, setPeriod] = useState('month');
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Analysis" subtitle="November 2026 · how the money moves in Piekarnia Kowalski">
        <Segmented onSurface value={period} onChange={setPeriod} options={[{ value: 'month', label: 'Month' }, { value: 'quarter', label: 'Quarter' }, { value: 'year', label: 'Year' }]} />
        <Button kind="ghost" icon={FileText}>Export for accountant</Button>
      </PageHeader>

      <div className="flex flex-wrap gap-4">
        {analysis.kpis.map((k) => <KpiTile key={k.label} kpi={k} />)}
      </div>

      <div className="flex gap-6">
        <RevenueChart />
        <Breakdown />
      </div>

      <div className="flex gap-6">
        <TeamTable />
        <InvoiceGauge />
      </div>

      <div className="flex flex-wrap gap-4">
        {analysis.meters.map((m) => (
          <div key={m.label} className="flex min-w-[170px] flex-1 flex-col gap-2 rounded-tile bg-surface p-[18px]">
            <div className="flex items-center gap-2 text-text-muted">
              <Icon name={m.icon} className="h-[18px] w-[18px]" />
              <span className="t-overline">{m.label}</span>
            </div>
            <p className="t-title">{m.value}</p>
            <Bar pct={m.pct} color={m.warn ? 'bg-status-amber' : 'bg-green-700'} />
            <p className="t-small text-text-muted">{m.sub}</p>
          </div>
        ))}
        <Link to="/risk" className="flex min-w-[170px] flex-1 flex-col gap-2 rounded-tile bg-green-900 p-[18px] transition-transform hover:-translate-y-0.5">
          <div className="flex items-center gap-2 text-green-200">
            <ShieldAlert className="h-[18px] w-[18px]" strokeWidth={1.8} />
            <span className="t-overline">Risk score</span>
          </div>
          <p className="flex items-baseline gap-1.5"><span className="t-title text-white">{risk.score}</span><span className="t-small text-green-200">/ 100 · low</span></p>
          <p className="t-small text-white">{risk.counts.watchlist} companies to watch</p>
          <p className="t-small text-green-200">See Risk ›</p>
        </Link>
      </div>
    </div>
  );
}

