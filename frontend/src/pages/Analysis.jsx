import React from 'react';
import { CalendarRange, FileText, Sparkles, TriangleAlert } from 'lucide-react';
import { useAnalysis } from '../state/analysisStore.js';
import { Bar, Button, Chip, Insight, PageHeader } from '../components/ui/primitives.jsx';
import Icon from '../components/ui/Icon.jsx';
import ForecastCard from '../components/dashboard/ForecastCard.jsx';
import CashFlowQ4 from '../components/analysis/CashFlowQ4.jsx';
import ExpenseStructure from '../components/analysis/ExpenseStructure.jsx';
import { cx } from '../utils/format.js';

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

function TeamTable() {
  const analysis = useAnalysis();
  return (
    <section className="card flex min-w-0 flex-1 flex-col gap-1">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="t-title">Team & payroll</h2>
          <p className="t-small text-text-muted">Who works, who is off, and what leaves on payday</p>
        </div>
        <Chip tone="dark" dot={false}>Next payroll {analysis.kpis[0].value}</Chip>
      </div>
      <div className="-mx-1 overflow-x-auto px-1 scrollbar-thin"><table className="w-full border-separate border-spacing-0 min-w-[520px]">
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
      </table></div>
      <div className="flex items-center justify-between px-3 py-3">
        {analysis.teamMore > 0 ? <button type="button" className="t-small text-green-700 hover:underline">+ {analysis.teamMore} more people</button> : <span />}
        <span className="t-body-m">Total {analysis.teamTotal}</span>
      </div>
      <Insight tone="amber" icon={Sparkles}>{analysis.teamInsight}</Insight>
    </section>
  );
}

function DataQualityNotice({ quality }) {
  if (!quality || !quality.issues || quality.issues.length === 0) return null;
  const details = quality.issues.map((i) => `${i.count} ${i.label}`).join(' · ');
  return (
    <Insight tone="amber" icon={TriangleAlert}>
      Bank data check ({quality.checked} transactions this quarter): {details}. Numbers below may be less accurate until this is fixed.
    </Insight>
  );
}

export default function Analysis() {
  const analysis = useAnalysis();
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Analysis" subtitle={`${analysis.label || 'Q4 2026 (October – December)'} · how the money moves in ${analysis.company || 'Piekarnia Kowalski'}`}>
        <span className="inline-flex items-center gap-2 rounded-full bg-surface px-4 py-2.5 t-small">
          <CalendarRange className="h-4 w-4 text-green-700" /> {analysis.range || 'Q4 · 1 Oct – 31 Dec'}
        </span>
        <Button kind="ghost" icon={FileText}>Export for accountant</Button>
      </PageHeader>

      <DataQualityNotice quality={analysis.dataQuality} />

      <ForecastCard />

      <div className="flex flex-wrap gap-4">
        {analysis.kpis.map((k) => <KpiTile key={k.label} kpi={k} />)}
      </div>

      <CashFlowQ4 />

      <div className="flex flex-col gap-6 xl:flex-row xl:items-start">
        <TeamTable />
        <ExpenseStructure stacked className="w-full shrink-0 xl:w-[400px]" />
      </div>

      <div className="flex flex-wrap gap-4">
        {analysis.meters.map((m) => (
          <div key={m.label} className="flex min-w-[150px] flex-1 flex-col gap-2 rounded-tile bg-surface p-[18px]">
            <div className="flex items-center gap-2 text-text-muted">
              <Icon name={m.icon} className="h-[18px] w-[18px]" />
              <span className="t-overline">{m.label}</span>
            </div>
            <p className="t-title">{m.value}</p>
            <Bar pct={m.pct} color={m.warn ? 'bg-status-amber' : 'bg-green-700'} />
            <p className="t-small text-text-muted">{m.sub}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

