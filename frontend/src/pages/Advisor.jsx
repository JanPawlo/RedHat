import React, { useEffect, useRef, useState } from 'react';
import { AudioLines, FileAudio, Mic, NotebookPen, Plus, SendHorizontal, Sparkles, Square, Trash2, Upload, Video } from 'lucide-react';
import { aiErrorMessage, askAdvisor, AGENT_MODEL, isAiLoadError } from '../api/agentApi.js';
import { CopyButton } from '../components/dashboard/DecisionCard.jsx';
import { Button, Chip, IconCircle, PageHeader, Segmented } from '../components/ui/primitives.jsx';
import {
  ADVISOR_HISTORY_TURNS,
  ADVISOR_MAX_UPLOAD_MB,
  ADVISOR_MESSAGES,
  ADVISOR_NOTE_MAX_LENGTH,
  ADVISOR_QUESTION_MAX_LENGTH,
  ADVISOR_TITLE_MAX_LENGTH,
  MATERIAL_KIND,
  RESPONSE_SOURCE_BUSY_FALLBACK,
} from '../const/advisor.js';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder.js';
import { advisorFacts, advisorNotes, useAdvisorMaterials } from '../state/advisorStore.js';
import { cx } from '../utils/format.js';

const KIND = {
  [MATERIAL_KIND.note]: { label: 'Note', icon: NotebookPen, tone: 'green' },
  [MATERIAL_KIND.voice]: { label: 'Voice message', icon: AudioLines, tone: 'blue' },
  [MATERIAL_KIND.meeting]: { label: 'Meeting recording', icon: Video, tone: 'amber' },
};

const SUGGESTIONS = [
  'When is the best time to buy the second oven?',
  'Can I take the Frankfurter Hof catering order?',
  'What should I watch out for in January?',
  'Do I really need the overdraft line?',
];

const whenFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

function duration(sec) {
  if (!sec && sec !== 0) return '';
  const m = Math.floor(sec / 60);
  const s = String(Math.round(sec % 60)).padStart(2, '0');
  return `${m}:${s}`;
}

function TextArea({ value, onChange, placeholder, rows = 4, maxLength = ADVISOR_NOTE_MAX_LENGTH }) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      maxLength={maxLength}
      className="w-full resize-y rounded-2xl bg-subtle px-4 py-3 text-[16px] outline-none ring-green-500 placeholder:text-text-muted focus:ring-2 sm:text-[15px]"
    />
  );
}

function TitleInput({ value, onChange, placeholder }) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      maxLength={ADVISOR_TITLE_MAX_LENGTH}
      className="w-full rounded-full bg-subtle px-4 py-2.5 text-[16px] outline-none ring-green-500 placeholder:text-text-muted focus:ring-2 sm:text-[15px]"
    />
  );
}

function NoteForm({ onSave }) {
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');
  const save = () => {
    onSave({ kind: MATERIAL_KIND.note, title: title.trim() || 'Note', text: text.trim() });
    setTitle('');
    setText('');
  };
  return (
    <div className="flex flex-col gap-3">
      <TitleInput value={title} onChange={setTitle} placeholder="Title (optional)" />
      <TextArea value={text} onChange={setText} placeholder="e.g. I want to buy a delivery scooter in February, about 4,000 EUR…" />
      <Button icon={Plus} className="self-end" disabled={!text.trim()} onClick={save}>Add note</Button>
    </div>
  );
}

function VoiceForm({ onSave }) {
  const rec = useVoiceRecorder();
  const [title, setTitle] = useState('');
  const recording = rec.status === 'recording';

  const save = () => {
    onSave({ kind: MATERIAL_KIND.voice, title: title.trim() || 'Voice message', text: rec.transcript.trim(), audioUrl: rec.audioUrl, durationSec: rec.seconds });
    setTitle('');
    rec.reset();
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-4 rounded-2xl bg-subtle p-4">
        <button
          type="button"
          onClick={recording ? rec.stop : rec.start}
          aria-label={recording ? 'Stop recording' : 'Start recording'}
          className={cx(
            'relative flex h-16 w-16 shrink-0 items-center justify-center rounded-full text-white shadow-soft transition-transform active:scale-95',
            recording ? 'bg-status-red' : 'bg-green-700 hover:bg-green-900',
          )}
        >
          {recording && <span className="absolute inset-0 animate-ping rounded-full bg-status-red/40" aria-hidden />}
          {recording ? <Square className="relative h-6 w-6" fill="currentColor" /> : <Mic className="h-7 w-7" />}
        </button>
        <div className="min-w-0 flex-1">
          <p className="t-body-m">{recording ? 'Recording…' : rec.status === 'done' ? 'Recorded' : 'Tap to record a voice message'}</p>
          <p className="t-small text-text-muted">
            {recording || rec.status === 'done' ? duration(rec.seconds) : rec.canTranscribe ? 'Transcript is written live while you speak' : 'Max 3 minutes'}
          </p>
        </div>
        {rec.audioUrl && <audio controls src={rec.audioUrl} className="h-10 w-full max-w-[320px]" />}
      </div>
      {rec.error && <p className="t-small text-status-red">{rec.error}</p>}
      {(recording || rec.status === 'done') && (
        <>
          <TitleInput value={title} onChange={setTitle} placeholder="Title (optional)" />
          <TextArea
            value={rec.transcript}
            onChange={rec.setTranscript}
            rows={3}
            placeholder={rec.canTranscribe ? 'Transcript appears here…' : 'Write what you said, so the agent can use it'}
          />
        </>
      )}
      {rec.status === 'done' && (
        <div className="flex flex-wrap justify-end gap-2">
          <Button kind="ghost" onClick={rec.reset}>Discard</Button>
          <Button icon={Plus} onClick={save}>Add voice message</Button>
        </div>
      )}
    </div>
  );
}

function MeetingForm({ onSave }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');

  const pick = (f) => {
    setError('');
    if (!f) return;
    if (f.size > ADVISOR_MAX_UPLOAD_MB * 1024 * 1024) {
      setError(ADVISOR_MESSAGES.fileTooBig);
      return;
    }
    const url = URL.createObjectURL(f);
    const media = document.createElement(f.type.startsWith('video') ? 'video' : 'audio');
    media.preload = 'metadata';
    media.onloadedmetadata = () => setFile((cur) => (cur?.url === url ? { ...cur, durationSec: media.duration } : cur));
    media.src = url;
    setFile({ name: f.name, sizeMb: f.size / 1024 / 1024, url, video: f.type.startsWith('video') });
    setTitle(f.name.replace(/\.[^.]+$/, ''));
  };

  const save = () => {
    onSave({ kind: MATERIAL_KIND.meeting, title: title.trim() || file.name, text: text.trim(), audioUrl: file.url, fileName: file.name, durationSec: file.durationSec });
    setFile(null);
    setTitle('');
    setText('');
  };

  return (
    <div className="flex flex-col gap-3">
      <label
        className="flex cursor-pointer flex-col items-center gap-2 rounded-2xl border-2 border-dashed border-green-200 bg-subtle px-4 py-6 text-center transition-colors hover:bg-green-100"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          pick(e.dataTransfer.files?.[0]);
        }}
      >
        <Upload className="h-6 w-6 text-green-700" />
        <span className="t-body-m">{file ? file.name : 'Drop a meeting recording or tap to choose'}</span>
        <span className="t-small text-text-muted">
          {file ? `${file.sizeMb.toFixed(1)} MB${file.durationSec ? ` · ${duration(file.durationSec)}` : ''}` : `Audio or video · up to ${ADVISOR_MAX_UPLOAD_MB} MB`}
        </span>
        <input type="file" accept="audio/*,video/*" className="sr-only" onChange={(e) => pick(e.target.files?.[0])} />
      </label>
      {error && <p className="t-small text-status-red">{error}</p>}
      {file && (
        <>
          <TitleInput value={title} onChange={setTitle} placeholder="Meeting title" />
          <TextArea value={text} onChange={setText} rows={3} placeholder="Key points: what was agreed, amounts, dates…" />
          <p className="t-small text-text-muted">{ADVISOR_MESSAGES.noTranscript}</p>
          <div className="flex flex-wrap justify-end gap-2">
            <Button kind="ghost" onClick={() => setFile(null)}>Discard</Button>
            <Button icon={Plus} onClick={save}>Add recording</Button>
          </div>
        </>
      )}
    </div>
  );
}

function AddMaterial({ onAdd }) {
  const [kind, setKind] = useState(MATERIAL_KIND.note);
  const options = Object.entries(KIND).map(([value, k]) => ({ value, label: k.label }));
  return (
    <section className="card flex flex-col gap-4" aria-label="Add context">
      <div>
        <h2 className="t-title">Add context</h2>
        <p className="t-small text-text-muted">Plans, worries, what a supplier or the bank told you · the agent reads it with your numbers</p>
      </div>
      <div className="-mx-1 overflow-x-auto px-1 pb-0.5 scrollbar-thin">
        <Segmented value={kind} onChange={setKind} options={options} />
      </div>
      {kind === MATERIAL_KIND.note && <NoteForm onSave={onAdd} />}
      {kind === MATERIAL_KIND.voice && <VoiceForm onSave={onAdd} />}
      {kind === MATERIAL_KIND.meeting && <MeetingForm onSave={onAdd} />}
    </section>
  );
}

function MaterialItem({ item, onToggle, onRemove }) {
  const k = KIND[item.kind];
  const [open, setOpen] = useState(false);
  const long = (item.text || '').length > 160;
  return (
    <li className="flex flex-col gap-2.5 rounded-[20px] bg-subtle p-4">
      <div className="flex items-start gap-3">
        <IconCircle icon={k.icon} tone={k.tone} size={40} />
        <div className="min-w-0 flex-1">
          <p className="break-words t-body-m">{item.title}</p>
          <p className="t-small text-text-muted">
            {k.label} · {whenFmt.format(new Date(item.at))}
            {item.durationSec ? ` · ${duration(item.durationSec)}` : ''}
          </p>
        </div>
        <button type="button" onClick={onRemove} aria-label={`Delete ${item.title}`} className="-mr-1 shrink-0 rounded-full p-2 text-text-muted hover:bg-surface hover:text-status-red">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      {item.audioUrl && <audio controls src={item.audioUrl} className="h-10 w-full" />}
      {!item.audioUrl && item.kind !== MATERIAL_KIND.note && (
        <p className="flex items-center gap-1.5 t-small text-text-muted">
          <FileAudio className="h-3.5 w-3.5 shrink-0" /> {item.fileName || 'Recording'} · only the text is kept after a refresh
        </p>
      )}
      {item.text ? (
        <p className={cx('break-words t-small text-text', !open && long && 'line-clamp-3')}>{item.text}</p>
      ) : (
        <p className="t-small italic text-text-muted">No text yet · the agent cannot use this one</p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-2">
        {long ? (
          <button type="button" onClick={() => setOpen((v) => !v)} className="t-small text-green-700 hover:underline">
            {open ? 'Show less' : 'Show more'}
          </button>
        ) : (
          <span />
        )}
        <label className="flex cursor-pointer items-center gap-2 t-small">
          <input type="checkbox" checked={item.useInChat} onChange={(e) => onToggle(e.target.checked)} className="h-4 w-4 accent-green-700" />
          Use in chat
        </label>
      </div>
    </li>
  );
}

function Chat({ materials }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(false);
  const scroller = useRef(null);
  const notes = advisorNotes(materials);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  const ask = async (q) => {
    const text = (q ?? draft).trim().slice(0, ADVISOR_QUESTION_MAX_LENGTH);
    if (!text || loading) return;
    const history = messages
      .filter((m) => !m.error)
      .slice(-ADVISOR_HISTORY_TURNS)
      .map((m) => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.text }));
    setDraft('');
    setMessages((m) => [...m, { role: 'user', text }]);
    setLoading(true);
    try {
      const facts = await advisorFacts();
      const { answer, source } = await askAdvisor({ facts: { ...facts, notes }, question: text, history });
      const note = source === RESPONSE_SOURCE_BUSY_FALLBACK ? ADVISOR_MESSAGES.busyFallback : null;
      setMessages((m) => [...m, { role: 'ai', text: answer, note }]);
    } catch (error) {
      setMessages((m) => [...m, { role: 'ai', error: true, busy: isAiLoadError(error), text: aiErrorMessage(error) }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card flex min-h-[520px] min-w-0 flex-col gap-3 xl:h-[calc(100dvh-170px)] xl:min-h-[560px]" aria-label="Advisor chat">
      <div className="flex flex-wrap items-center gap-3">
        <IconCircle icon={Sparkles} tone="solid" size={40} />
        <div className="min-w-0 flex-1">
          <h2 className="t-title">Ask your advisor</h2>
          <p className="t-small text-text-muted">OpenShift AI · {AGENT_MODEL} · reads {notes.length} of your notes and the cash forecast</p>
        </div>
        {messages.length > 0 && (
          <button type="button" onClick={() => setMessages([])} className="t-small text-text-muted hover:text-text">Clear</button>
        )}
      </div>

      <div ref={scroller} className="-mr-2 flex min-h-[260px] flex-1 flex-col gap-2.5 overflow-y-auto pr-2 scrollbar-thin">
        {!messages.length && (
          <div className="flex flex-col gap-2 rounded-2xl bg-green-100/70 px-4 py-3">
            <p className="t-body">
              Hi! Tell me what you plan to buy or what worries you. I check it against your cash, the safety buffer and the payments coming up, and tell you when it is safe to spend.
            </p>
            <p className="t-small text-text-muted">Numbers come from the forecast engine. I only explain them.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={cx(
              'flex max-w-[88%] items-start gap-1 whitespace-pre-line break-words rounded-2xl px-3.5 py-2.5 t-small',
              m.role === 'user' ? 'self-end bg-green-700 text-white' : m.busy ? 'self-start bg-status-amber-soft text-status-amber' : m.error ? 'self-start bg-status-red-soft text-status-red' : 'self-start bg-green-100 text-text',
            )}
          >
            <span className="min-w-0 flex-1">
              {m.note && <span className="mb-1 block font-semibold text-status-amber">{m.note}</span>}
              {m.text}
            </span>
            {m.role === 'ai' && !m.error && <CopyButton text={m.text} className="-my-1.5 -mr-2" />}
          </div>
        ))}
        {loading && <p className="max-w-[88%] self-start rounded-2xl bg-green-100 px-3.5 py-2.5 t-small italic text-text-muted">The advisor is thinking…</p>}
      </div>

      <div className="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-0.5 scrollbar-thin">
        {SUGGESTIONS.map((q) => (
          <button key={q} type="button" onClick={() => ask(q)} disabled={loading} className="shrink-0 rounded-full bg-subtle px-3 py-2 t-small hover:bg-green-100 disabled:opacity-50">
            {q}
          </button>
        ))}
      </div>
      <form
        className="flex items-center gap-2 rounded-full bg-subtle py-1.5 pl-4 pr-1.5"
        onSubmit={(e) => {
          e.preventDefault();
          ask();
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          maxLength={ADVISOR_QUESTION_MAX_LENGTH}
          placeholder="e.g. Should I buy the oven now or in February?"
          className="min-w-0 flex-1 bg-transparent text-[16px] outline-none placeholder:text-text-muted sm:text-[14px]"
        />
        <button type="submit" disabled={loading || !draft.trim()} aria-label="Send question" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-green-700 text-white hover:bg-green-900 disabled:opacity-50">
          <SendHorizontal className="h-4 w-4" />
        </button>
      </form>
    </section>
  );
}

/** Advisor: the owner adds notes, voice messages and meeting recordings; the AI reads them with the forecast and answers. */
export default function Advisor() {
  const { materials, add, update, remove } = useAdvisorMaterials();
  const used = materials.filter((m) => m.useInChat).length;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Advisor" subtitle="Your notes, voice messages and meetings · the agent checks them against your cash before you spend">
        <Chip tone="green">{used} used in chat</Chip>
      </PageHeader>

      {/* Phones: add → chat → list. Desktop: add and list on the left, chat on the right. */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[440px_minmax(0,1fr)] xl:items-start">
        <div className="min-w-0 xl:col-start-1 xl:row-start-1">
          <AddMaterial onAdd={add} />
        </div>
        <div className="min-w-0 xl:sticky xl:top-6 xl:col-start-2 xl:row-span-2 xl:row-start-1">
          <Chat materials={materials} />
        </div>
        <section className="card flex min-w-0 flex-col gap-3 xl:col-start-1 xl:row-start-2" aria-label="Your materials">
          <div className="flex items-center justify-between gap-2">
            <h2 className="t-title">Your materials</h2>
            <span className="t-small text-text-muted">{materials.length}</span>
          </div>
          {!materials.length && <p className="py-6 text-center t-small text-text-muted">Nothing yet. Add a note or record a voice message.</p>}
          <ul className="flex flex-col gap-2.5">
            {materials.map((m) => (
              <MaterialItem key={m.id} item={m} onToggle={(v) => update(m.id, { useInChat: v })} onRemove={() => remove(m.id)} />
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
