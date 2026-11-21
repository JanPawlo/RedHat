import React, { useMemo, useState } from 'react';
import { Check, ChevronRight, Eye, FileText, Mail as MailIcon, Reply, SendHorizontal, ShieldCheck, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAppState } from '../state/AppState.jsx';
import { Button, Chip, Insight, PageHeader, Pill } from '../components/ui/primitives.jsx';
import { cx } from '../utils/format.js';

const STATUS_TONE = { Replied: 'dark', 'Needs OK': 'amber', Scheduled: 'blue', Opened: 'green', Sent: 'neutral' };
const STEP_ICON = { 'Drafted by AI': Sparkles, 'Approved by you': Check, Sent: SendHorizontal, Scheduled: SendHorizontal, Opened: Eye, Replied: Reply };

const TABS = [
  { id: 'all', label: 'All', count: (m) => m.length, match: () => true },
  { id: 'ok', label: 'Needs OK', count: (m) => m.filter((x) => x.status === 'Needs OK').length, match: (x) => x.status === 'Needs OK' },
  { id: 'scheduled', label: 'Scheduled', count: (m) => m.filter((x) => x.status === 'Scheduled').length, match: (x) => x.status === 'Scheduled' },
  { id: 'sent', label: 'Sent', count: (m) => m.filter((x) => ['Sent', 'Opened', 'Replied'].includes(x.status)).length, match: (x) => ['Sent', 'Opened', 'Replied'].includes(x.status) },
  { id: 'replies', label: 'Replies', count: (m) => m.filter((x) => x.status === 'Replied').length, match: (x) => x.status === 'Replied' },
];

function MailRow({ mail, selected, onSelect }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cx('flex w-full items-start gap-3.5 rounded-[18px] px-4 py-3.5 text-left transition-colors', selected ? 'bg-green-100' : 'hover:bg-subtle')}
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
    <ol className="flex flex-wrap items-center gap-2">
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
            {!last && <span className="h-0.5 min-w-[12px] flex-1 rounded-full bg-green-200" aria-hidden />}
          </React.Fragment>
        );
      })}
    </ol>
  );
}

function Preview({ mail, onApprove }) {
  const { company } = useAppState();
  return (
    <article className="card flex min-w-0 flex-1 flex-col gap-[18px]">
      <div className="flex items-center gap-3">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-green-700 t-title text-white">{mail.initials}</span>
        <div className="min-w-0 flex-1">
          <p className="t-body-m">To: {mail.to}</p>
          <p className="t-small text-text-muted">From: RedCaps CFO on behalf of {company.owner.firstName} {company.owner.lastName} · {mail.time}</p>
        </div>
        <Chip tone={STATUS_TONE[mail.status]}>{mail.status}</Chip>
      </div>
      <h2 className="t-display-l">{mail.subject}</h2>
      <div className="flex flex-wrap gap-2">
        <Chip tone="green">From card: {mail.card}</Chip>
        <Chip dot={false}>{mail.agent}</Chip>
        {mail.status !== 'Needs OK' && <Chip tone="blue">Approved by you</Chip>}
      </div>
      <div className="flex flex-col gap-2.5 rounded-[20px] bg-subtle p-5">
        {mail.body.map((p, i) => (
          <p key={i} className="whitespace-pre-line t-body">{p}</p>
        ))}
      </div>
      <Timeline steps={mail.timeline} />
      {mail.reply && (
        <div className="flex flex-col gap-2 rounded-[20px] p-[18px] ring-1 ring-inset ring-line">
          <p className="flex items-center gap-2 t-small text-text-muted">
            <Reply className="h-4 w-4" /> {mail.reply.from} replied · {mail.reply.time}
          </p>
          <p className="t-body">{mail.reply.text}</p>
        </div>
      )}
      {mail.effect && <Insight icon={Sparkles}>{mail.effect}</Insight>}
      <div className="flex flex-wrap gap-2.5">
        {mail.status === 'Needs OK' ? (
          <>
            <Button icon={Check} onClick={() => onApprove(mail)}>Approve & send</Button>
            <Button kind="ghost">Edit draft</Button>
          </>
        ) : (
          <Button icon={Reply}>Reply</Button>
        )}
        <Link to="/#deck"><Button kind="ghost" iconRight={ChevronRight}>Open card</Button></Link>
        <Link to="/history"><Button kind="ghost" icon={FileText}>View in History</Button></Link>
      </div>
    </article>
  );
}

export default function Mail() {
  const { mails, approveMail, showToast } = useAppState();
  const [tab, setTab] = useState('all');
  const [selectedId, setSelectedId] = useState(mails[0]?.id);
  const current = TABS.find((t) => t.id === tab);
  const list = useMemo(() => mails.filter(current.match), [mails, current]);
  const selected = mails.find((m) => m.id === selectedId) || list[0];
  const needsOk = mails.filter((m) => m.status === 'Needs OK');

  const approve = (mail) => {
    approveMail(mail.id);
    showToast({ tone: 'green', text: `Sent to ${mail.to} · test mailbox on the cluster` });
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Mail" subtitle="Emails I wrote from your decisions · they go to the test mailbox on the cluster">
        <Button kind="ghost" icon={MailIcon}>Open test mailbox</Button>
        <Button icon={Check} disabled={!needsOk.length} onClick={() => { setTab('ok'); setSelectedId(needsOk[0]?.id); }}>
          Review {needsOk.length} drafts
        </Button>
      </PageHeader>

      <div className="flex flex-wrap items-center gap-2">
        {TABS.map((t) => (
          <Pill key={t.id} active={tab === t.id} onClick={() => setTab(t.id)}>{t.label} · {t.count(mails)}</Pill>
        ))}
        <div className="flex-1" />
        <span className="flex items-center gap-1.5 t-small text-green-700">
          <ShieldCheck className="h-4 w-4" /> Only known recipients · nothing leaves without your OK
        </span>
      </div>

      <div className="flex flex-col items-stretch gap-6 xl:flex-row xl:items-start">
        <section className="flex w-full shrink-0 flex-col gap-1 rounded-card xl:w-[420px] 2xl:w-[480px] bg-surface p-3" aria-label="Mail list">
          {list.map((m) => (
            <MailRow key={m.id} mail={m} selected={selected?.id === m.id} onSelect={() => setSelectedId(m.id)} />
          ))}
          {!list.length && <p className="p-6 text-center t-small text-text-muted">No emails here.</p>}
        </section>
        {selected && <Preview mail={selected} onApprove={approve} />}
      </div>
    </div>
  );
}
