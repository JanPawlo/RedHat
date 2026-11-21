import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check, LayoutGrid, Sparkles } from 'lucide-react';
import { useAppState } from '../state/AppState.jsx';
import { CardFace, CopyButton } from '../components/dashboard/DecisionCard.jsx';
import { Button, Chip, PageHeader, Pill } from '../components/ui/primitives.jsx';
import { cx, formatPLN } from '../utils/format.js';

const GROUPS = [
  { id: 'today', label: 'Today' },
  { id: 'yesterday', label: 'Yesterday' },
  { id: 'week', label: 'This week' },
  { id: 'earlier', label: 'Earlier' },
];

function groupOf(iso) {
  const day = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((day(new Date()) - day(new Date(iso))) / 86400000);
  if (diff <= 0) return 'today';
  if (diff === 1) return 'yesterday';
  if (diff < 7) return 'week';
  return 'earlier';
}

const timeLabel = (iso) =>
  new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(iso));

/** One saved decision, shown as the card it was, with the agent's answer kept at decision time. */
function HistoryCard({ entry }) {
  const approved = entry.choice === 'approve';
  const answer = entry.ai?.answer;
  return (
    <article className="flex min-w-0 flex-col">
      <CardFace
        compact
        card={{ ...entry.card, autonomy: null }}
        className="!shadow-soft"
        footer={
          <div className="mt-1 flex w-full flex-col gap-3">
            <div className={cx('flex items-center gap-3 rounded-[18px] px-4 py-3', approved ? 'bg-green-700 text-white' : 'bg-status-red-soft text-status-red')}>
              {approved ? <ArrowRight className="h-5 w-5 shrink-0" /> : <ArrowLeft className="h-5 w-5 shrink-0" />}
              <span className="min-w-0 flex-1">
                <span className="block t-overline opacity-80">{approved ? 'You swiped right' : 'You swiped left'}</span>
                <span className="block t-body-m">{approved ? entry.card.right : entry.card.left}</span>
              </span>
              <span className="shrink-0 t-small opacity-80">{timeLabel(entry.at)}</span>
            </div>

            <div className="rounded-2xl bg-green-100/70 px-4 py-3 text-left">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="flex items-center gap-1.5 t-small font-semibold text-green-700">
                  <Sparkles className="h-3.5 w-3.5" /> {answer ? `Agent's answer · ${entry.ai.model}` : 'Engine note (model was offline)'}
                </span>
                {answer && <CopyButton text={answer} className="-my-1.5 -mr-2" />}
              </div>
              <p className="t-small text-text">{answer || entry.fallback || '—'}</p>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {approved && entry.card.resultLabel && <Chip tone={/SIMULATED/.test(entry.card.resultLabel) ? 'blue' : 'green'}>{entry.card.resultLabel}</Chip>}
              {approved && entry.card.amount ? <Chip dot={false}>{formatPLN(entry.card.amount)}</Chip> : null}
              {(entry.actions || []).map((a) => (
                <Chip key={a} tone="neutral" dot={false} className="!whitespace-normal">
                  <Check className="h-3 w-3" /> {a}
                </Chip>
              ))}
            </div>
          </div>
        }
      />
    </article>
  );
}

export default function History() {
  const { history } = useAppState();
  const [filter, setFilter] = useState('all');

  const grouped = useMemo(() => {
    const by = Object.fromEntries(GROUPS.map((g) => [g.id, []]));
    [...history].sort((a, b) => b.at.localeCompare(a.at)).forEach((e) => by[groupOf(e.at)].push(e));
    return by;
  }, [history]);

  const visible = GROUPS.filter((g) => grouped[g.id].length && (filter === 'all' || filter === g.id));
  const approved = history.filter((e) => e.choice === 'approve').length;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="History" subtitle={`Every decision you made, with the agent's answer at that moment · ${history.length} decisions, ${approved} approved`}>
        <Link to="/">
          <Button kind="ghost" icon={LayoutGrid}>Back to cards</Button>
        </Link>
      </PageHeader>

      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 scrollbar-thin lg:mx-0 lg:flex-wrap lg:px-0">
        <Pill active={filter === 'all'} onClick={() => setFilter('all')}>All · {history.length}</Pill>
        {GROUPS.filter((g) => grouped[g.id].length).map((g) => (
          <Pill key={g.id} active={filter === g.id} onClick={() => setFilter(g.id)}>
            {g.label} · {grouped[g.id].length}
          </Pill>
        ))}
      </div>

      {!history.length && <p className="card text-center t-body text-text-muted">No decisions yet. Swipe a card on the main screen and it shows up here.</p>}

      {visible.map((g) => (
        <section key={g.id} className="flex flex-col gap-3" aria-label={g.label}>
          <h2 className="t-overline text-text-muted">{g.label}</h2>
          <div className="grid gap-5 md:grid-cols-2 2xl:grid-cols-3">
            {grouped[g.id].map((e) => (
              <HistoryCard key={e.id} entry={e} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
