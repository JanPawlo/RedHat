import React, { useMemo, useRef, useState } from 'react';
import { ArrowUp, Check, ChevronRight, Eye, FileText, Reply, SendHorizontal, ShieldCheck, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAppState } from '../state/AppState.jsx';
import { Button, Chip, Insight, PageHeader, Pill } from '../components/ui/primitives.jsx';
import { cx } from '../utils/format.js';
import MockupButton from '../components/ui/MockupButton.jsx';

const STATUS_TONE = { Replied: 'dark', 'Needs OK': 'amber', Scheduled: 'blue', Opened: 'green', Sent: 'neutral' };
const STEP_ICON = { 'Drafted by AI': Sparkles, 'Approved by you': Check, Sent: SendHorizontal, Scheduled: SendHorizontal, Opened: Eye, Replied: Reply };

// Scheduled first: it is what goes out next, so Mail opens on it.
const DEFAULT_TAB = 'scheduled';
const TABS = [
  { id: 'scheduled', label: 'Scheduled', count: (m) => m.filter((x) => x.status === 'Scheduled').length, match: (x) => x.status === 'Scheduled' },
  { id: 'ok', label: 'Needs OK', count: (m) => m.filter((x) => x.status === 'Needs OK').length, match: (x) => x.status === 'Needs OK' },
  { id: 'all', label: 'All', count: (m) => m.length, match: () => true },
  { id: 'sent', label: 'Sent', count: (m) => m.filter((x) => ['Sent', 'Opened', 'Replied'].includes(x.status)).length, match: (x) => ['Sent', 'Opened', 'Replied'].includes(x.status) },
  { id: 'replies', label: 'Replies', count: (m) => m.filter((x) => x.status === 'Replied').length, match: (x) => x.status === 'Replied' },
];

function MailRow({ mail, selected, onSelect }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cx('flex w-full items-start gap-3 rounded-[18px] px-3 py-3 text-left transition-colors sm:gap-3.5 sm:px-4 sm:py-3.5', selected ? 'bg-green-100' : 'hover:bg-subtle')}
    >
      <span className={cx('flex h-10 w-10 shrink-0 items-center justify-center rounded-full t-small', selected ? 'bg-green-700 text-white' : 'bg-subtle')}>{mail.initials}</span>
      <span className="min-w-0 flex-1">
        <span className="block truncate t-body-m">{mail.to}</span>
        <span className="block t-small">{mail.subject}</span>
        <span className="block truncate t-small text-text-muted">{mail.snippet}</span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-2">
        <span className="t-small text-text-muted">{mail.time}</span>
        <Chip tone={STATUS_TONE[mail.status]}>{mail.status}</Chip>
      </span>
    </button>
  );
}

function Timeline({ steps }) {
  return (
    <ol className="flex flex-col items-start gap-1 sm:flex-row sm:flex-wrap sm:items-center sm:gap-2">
      {steps.map(([label, time], i) => {
        const IconCmp = STEP_ICON[label] || Check;
        const last = i === steps.length - 1;
        return (
          <React.Fragment key={label + i}>
            <li className="flex items-center gap-2">
              <span className={cx('flex h-8 w-8 items-center justify-center rounded-full', last ? 'bg-green-700 text-white' : 'bg-green-100 text-green-700')}>
                <IconCmp className="h-[15px] w-[15px]" strokeWidth={1.9} />
              </span>
              <span className="whitespace-nowrap">
                <span className="block t-small">{label}</span>
                <span className="block t-small text-text-muted">{time}</span>
              </span>
            </li>
            {!last && <span className="ml-[15px] h-3 w-0.5 rounded-full bg-green-200 sm:ml-0 sm:h-0.5 sm:w-auto sm:min-w-[12px] sm:flex-1" aria-hidden />}
          </React.Fragment>
        );
      })}
    </ol>
  );
}

const Preview = React.forwardRef(function Preview({ mail, onApprove, onBack }, ref) {
  const { company } = useAppState();
  return (
    <article ref={ref} className="card flex min-w-0 flex-1 scroll-mt-20 flex-col gap-[18px]">
      <button type="button" onClick={onBack} className="flex items-center gap-1.5 self-start t-small text-text-muted hover:text-text xl:hidden">
        <ArrowUp className="h-4 w-4" /> Back to the list
      </button>
      <div className="flex flex-wrap items-center gap-3">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-green-700 t-title text-white">{mail.initials}</span>
        <div className="min-w-0 flex-1 basis-[180px]">
          <p className="break-words t-body-m">To: {mail.to}</p>
          <p className="t-small text-text-muted">From: RedCaps CFO on behalf of {company.owner.firstName} {company.owner.lastName} · {mail.time}</p>
        </div>
        <Chip tone={STATUS_TONE[mail.status]}>{mail.status}</Chip>
      </div>
      <h2 className="break-words text-[22px] t-display-l sm:text-[26px]">{mail.subject}</h2>
      <div className="flex flex-wrap gap-2">
        <Chip tone="green">From card: {mail.card}</Chip>
        <Chip dot={false}>{mail.agent}</Chip>
        {mail.status !== 'Needs OK' && <Chip tone="blue">Approved by you</Chip>}
      </div>
      <div className="flex flex-col gap-2.5 rounded-[20px] bg-subtle p-4 sm:p-5">
        {mail.body.map((p, i) => (
          <p key={i} className="whitespace-pre-line t-body">{p}</p>
        ))}
      </div>
      <Timeline steps={mail.timeline} />
      {mail.reply && (
        <div className="flex flex-col gap-2 rounded-[20px] p-[18px] ring-1 ring-inset ring-line">
          <p className="flex items-start gap-2 t-small text-text-muted">
            <Reply className="mt-0.5 h-4 w-4 shrink-0" /> {mail.reply.from} replied · {mail.reply.time}
          </p>
          <p className="t-body">{mail.reply.text}</p>
        </div>
      )}
      {mail.effect && <Insight icon={Sparkles}>{mail.effect}</Insight>}
      <div className="flex flex-wrap gap-2.5">
        {mail.status === 'Needs OK' ? (
          <>
            <Button icon={Check} onClick={() => onApprove(mail)}>Approve & send</Button>
            <MockupButton>Edit draft</MockupButton>
          </>
        ) : (
          <MockupButton icon={Reply}>Reply</MockupButton>
        )}
        <Link to="/#deck"><Button kind="ghost" iconRight={ChevronRight}>Open card</Button></Link>
        <Link to="/history"><Button kind="ghost" icon={FileText}>View in History</Button></Link>
      </div>
    </article>
  );
});

export default function Mail() {
  const { mails, approveMail } = useAppState();
  const [tab, setTab] = useState(DEFAULT_TAB);
  const [selectedId, setSelectedId] = useState(() => mails.find(TABS[0].match)?.id ?? mails[0]?.id);
  const current = TABS.find((t) => t.id === tab);
  const list = useMemo(() => mails.filter(current.match), [mails, current]);
  const selected = mails.find((m) => m.id === selectedId) || list[0];
  const needsOk = mails.filter((m) => m.status === 'Needs OK');
  const listRef = useRef(null);
  const previewRef = useRef(null);
  // Below xl the list and the preview are stacked: show the opened email right away.
  const stacked = () => !window.matchMedia('(min-width: 1280px)').matches;

  const open = (id) => {
    setSelectedId(id);
    if (stacked()) requestAnimationFrame(() => previewRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  };

  const approve = (mail) => approveMail(mail.id);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Mail" subtitle="Emails I wrote from your decisions">
        <Button icon={Check} disabled={!needsOk.length} onClick={() => { setTab('ok'); setSelectedId(needsOk[0]?.id); }}>
          Review {needsOk.length} drafts
        </Button>
      </PageHeader>

      <div className="flex flex-wrap items-center gap-2">
        <div className="-mx-4 flex w-[calc(100%+32px)] gap-2 overflow-x-auto px-4 pb-0.5 scrollbar-thin lg:mx-0 lg:w-auto lg:flex-wrap lg:px-0">
          {TABS.map((t) => (
            <Pill key={t.id} active={tab === t.id} onClick={() => setTab(t.id)}>{t.label} · {t.count(mails)}</Pill>
          ))}
        </div>
        <div className="hidden flex-1 lg:block" />
        <span className="flex items-start gap-1.5 t-small text-green-700">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" /> Only known recipients
        </span>
      </div>

      <div className="flex flex-col items-stretch gap-6 xl:flex-row xl:items-start">
        <section ref={listRef} className="flex w-full shrink-0 scroll-mt-20 flex-col gap-1 rounded-card bg-surface p-2 sm:p-3 xl:w-[420px] 2xl:w-[480px]" aria-label="Mail list">
          {list.map((m) => (
            <MailRow key={m.id} mail={m} selected={selected?.id === m.id} onSelect={() => open(m.id)} />
          ))}
          {!list.length && (
            <p className="p-6 text-center t-small text-text-muted">
              {mails.length ? 'No emails here.' : 'No emails yet. Approve a card and choose “Schedule your mail” to write one.'}
            </p>
          )}
        </section>
        {selected && (
          <Preview ref={previewRef} mail={selected} onApprove={approve} onBack={() => listRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })} />
        )}
      </div>
    </div>
  );
}
