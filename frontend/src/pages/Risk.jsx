import React, { useState } from 'react';
import { Info, Landmark, Plus, Sparkles } from 'lucide-react';
import { risk } from '../data/mockData.js';
import { useAppState } from '../state/AppState.jsx';
import { Button, Chip, IconCircle, Insight, PageHeader, Pill, TONE_DOT } from '../components/ui/primitives.jsx';
import Gauge from '../components/ui/Gauge.jsx';
import { cx } from '../utils/format.js';

const LEVEL_TONE = { Low: 'green', Medium: 'amber', High: 'red' };
const SIGNALS = [
  ['google', 'Google'],
  ['krz', 'KRZ debtors'],
  ['payments', 'Payments'],
  ['statements', 'Statements'],
  ['account', 'Bank account'],
];

function Signal({ value }) {
  const [text, tone] = value;
  return (
    <span className="flex items-center gap-1.5">
      <span className={cx('h-2 w-2 shrink-0 rounded-full', TONE_DOT[tone])} />
      <span className={cx('t-small', tone === 'red' ? 'text-status-red' : 'text-text')}>{text}</span>
    </span>
  );
}

export default function Risk() {
  const { showToast } = useAppState();
  const [filter, setFilter] = useState('all');
  const rows = risk.counterparties.filter((c) =>
    filter === 'all' ? true : filter === 'watch' ? c.watch : filter === 'clients' ? c.role === 'Client' : c.role === 'Supplier',
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Risk" subtitle="Signals about your business and the companies you work with · updated today 07:00">
        <Button kind="ghost" icon={Info}>How we score</Button>
      </PageHeader>

      <div className="flex flex-col gap-6 xl:flex-row">
        <section className="card flex w-full shrink-0 xl:w-[400px] flex-col gap-3">
          <div>
            <h2 className="t-title">Your business risk</h2>
            <p className="t-small text-text-muted">Rules on your own data · 0 = calm, 100 = act now</p>
          </div>
          <Gauge size={352} stroke={22} marker={risk.score / 100} segments={[[0, 0.395, '#4E8A62'], [0.405, 0.695, '#E2B45C'], [0.705, 1, '#D9574B']]}>
            <p className="t-display-xl">{risk.score}</p>
            <p className="t-small text-status-green">{risk.label}</p>
          </Gauge>
          <ul>
            {risk.factors.map((f) => (
              <li key={f.label} className="flex items-center gap-2.5 border-b border-line py-2.5 last:border-0">
                <div className="min-w-0 flex-1">
                  <p className="t-body-m">{f.label}</p>
                  <p className="t-small text-text-muted">{f.note}</p>
                </div>
                <Chip tone={LEVEL_TONE[f.level]}>{f.level}</Chip>
              </li>
            ))}
          </ul>
        </section>

        <section className="card flex min-w-0 flex-1 flex-col gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <IconCircle icon={Landmark} size={48} />
            <div className="min-w-0 flex-1 basis-[180px]">
              <h2 className="t-title">How a lender sees you</h2>
              <p className="t-small text-text-muted">The same numbers a bank checks before an overdraft or a loan</p>
            </div>
            <Chip tone="green">{risk.lender.rating}</Chip>
          </div>
          <div className="grid grid-cols-1 gap-3 min-[400px]:grid-cols-2">
            {risk.lender.metrics.map((m) => (
              <div key={m.label} className="flex flex-col gap-1 rounded-[18px] bg-subtle px-4 py-3.5">
                <span className="flex items-center gap-1.5 t-small text-text-muted">
                  <span className={cx('h-2 w-2 rounded-full', TONE_DOT[m.tone])} />
                  {m.label}
                </span>
                <p className="t-title">{m.value}</p>
                <p className="t-small text-text-muted">{m.note}</p>
              </div>
            ))}
          </div>
          <Insight icon={Sparkles}>{risk.lender.insight}</Insight>
          <div className="flex flex-wrap gap-2">
            <Chip tone="blue">Commerzbank product · disclosed</Chip>
            <Chip>Not investment advice</Chip>
          </div>
        </section>
      </div>

      <section className="card flex flex-col gap-1">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <div className="w-full min-w-0 lg:w-auto lg:flex-1">
            <h2 className="t-title">Companies you work with</h2>
            <p className="t-small text-text-muted">One score per client or supplier, built from 5 public and own signals</p>
          </div>
          <div className="-mx-1 flex w-full gap-2 overflow-x-auto px-1 pb-0.5 scrollbar-thin lg:mx-0 lg:w-auto lg:px-0">
          {[
            ['all', `All · ${risk.counts.all}`],
            ['clients', `Clients · ${risk.counts.clients}`],
            ['suppliers', `Suppliers · ${risk.counts.suppliers}`],
            ['watch', `Watchlist · ${risk.counts.watchlist}`],
          ].map(([id, label]) => (
            <Pill key={id} muted active={filter === id} onClick={() => setFilter(id)}>{label}</Pill>
          ))}
          </div>
        </div>

        {/* Phones and tablets: one small card per company instead of the wide table. */}
        <ul className="flex flex-col gap-2.5 lg:hidden">
          {rows.map((c) => (
            <li key={c.name} className="flex flex-col gap-3 rounded-[18px] bg-subtle p-4">
              <div className="flex items-start gap-2">
                <div className="min-w-0 flex-1">
                  <p className="break-words t-body-m">{c.name}</p>
                  <p className="t-small text-text-muted">{c.role}</p>
                </div>
                <Chip tone={LEVEL_TONE[c.score]}>{c.score}</Chip>
              </div>
              <dl className="grid grid-cols-1 gap-x-4 gap-y-2 min-[380px]:grid-cols-2">
                {SIGNALS.map(([key, label]) => (
                  <div key={key} className="flex min-w-0 flex-col gap-0.5">
                    <dt className="t-overline text-text-muted">{label}</dt>
                    <dd className="min-w-0"><Signal value={c[key]} /></dd>
                  </div>
                ))}
              </dl>
            </li>
          ))}
        </ul>

        <div className="hidden overflow-x-auto scrollbar-thin lg:block">
          <table className="w-full min-w-[980px] border-separate border-spacing-0">
            <thead>
              <tr className="text-left">
                {['Company', 'Role', 'Score', 'Google', 'KRZ debtors', 'Payments', 'Statements', 'Bank account'].map((h, i, arr) => (
                  <th key={h} className={cx('bg-subtle px-3 py-2 t-overline text-text-muted', i === 0 && 'rounded-l-xl', i === arr.length - 1 && 'rounded-r-xl')}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.name} className="transition-colors hover:bg-subtle/60">
                  <td className="border-b border-line px-3 py-3 t-body-m">{c.name}</td>
                  <td className="border-b border-line px-3 py-3 t-small text-text-muted">{c.role}</td>
                  <td className="border-b border-line px-3 py-3"><Chip tone={LEVEL_TONE[c.score]}>{c.score}</Chip></td>
                  <td className="border-b border-line px-3 py-3"><Signal value={c.google} /></td>
                  <td className="border-b border-line px-3 py-3"><Signal value={c.krz} /></td>
                  <td className="border-b border-line px-3 py-3"><Signal value={c.payments} /></td>
                  <td className="border-b border-line px-3 py-3"><Signal value={c.statements} /></td>
                  <td className="border-b border-line px-3 py-3"><Signal value={c.account} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="flex flex-col gap-6 xl:flex-row">
        <section className="card flex min-w-0 flex-1 flex-col gap-3">
          <h2 className="t-title">Watchlist · what I would do</h2>
          {risk.watchlist.map((w) => (
            <div key={w.title} className={cx('flex flex-wrap items-center gap-3.5 rounded-[20px] p-4', w.tone === 'red' ? 'bg-status-red-soft' : 'bg-status-amber-soft')}>
              <IconCircle name={w.icon} tone="white" />
              <div className="min-w-0 flex-1 basis-[200px]">
                <p className="t-body-m">{w.title}</p>
                <p className="t-small text-text-muted">{w.note}</p>
              </div>
              <Button kind="dark" icon={Plus} className="w-full sm:w-auto" onClick={() => showToast({ tone: 'green', text: 'Card added to your deck (demo).' })}>Make a card</Button>
            </div>
          ))}
        </section>
        <section className="card flex w-full shrink-0 xl:w-[400px] flex-col gap-2.5">
          <h2 className="t-title">Where signals come from</h2>
          {risk.sources.map((s) => (
            <div key={s.label} className="flex items-center gap-2.5">
              <IconCircle name={s.icon} size={32} />
              <div>
                <p className="t-small">{s.label}</p>
                <p className="t-small text-text-muted">{s.note}</p>
              </div>
            </div>
          ))}
          <p className="mt-1 t-small text-green-700">Scores come from fixed rules, not from the AI. The AI only explains them.</p>
        </section>
      </div>
    </div>
  );
}
