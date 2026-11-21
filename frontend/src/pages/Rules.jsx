import React from 'react';
import { Bot, Hand, Lock, Mail, RotateCcw, ShieldCheck, Sparkles, Wallet } from 'lucide-react';
import { useAppState } from '../state/AppState.jsx';
import { Button, Chip, PageHeader } from '../components/ui/primitives.jsx';
import { cx, formatPLN } from '../utils/format.js';

function Switch({ checked, onChange, label, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cx('relative h-7 w-12 shrink-0 rounded-full transition-colors disabled:opacity-60', checked ? 'bg-green-700' : 'bg-line')}
    >
      <span className={cx('absolute left-0 top-1 h-5 w-5 rounded-full bg-surface shadow transition-transform', checked ? 'translate-x-6' : 'translate-x-1')} />
    </button>
  );
}

function Amount({ value, onChange, min, max, step, label, disabled }) {
  return (
    <div className={cx('flex flex-col gap-2', disabled && 'opacity-50')}>
      <div className="flex items-center justify-between gap-3">
        <span className="t-small text-text-muted">{label}</span>
        <span className="t-mono">{formatPLN(value)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label={label}
        className="h-8 w-full cursor-pointer accent-green-700"
      />
      <div className="flex justify-between t-small text-text-muted">
        <span>{formatPLN(min)}</span>
        <span>{formatPLN(max)}</span>
      </div>
    </div>
  );
}

function Rule({ icon: IconCmp, title, text, id, right, children, locked }) {
  return (
    <section className="card flex min-w-0 flex-col gap-4" aria-labelledby={`rule-${id}`}>
      <div className="flex items-start gap-3.5">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-green-100 text-green-700">
          <IconCmp className="h-5 w-5" strokeWidth={1.8} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 id={`rule-${id}`} className="t-title">{title}</h2>
            <span className="t-mono text-text-muted">{id}</span>
            {locked && <Chip tone="blue">Always on at the hackathon</Chip>}
          </div>
          <p className="mt-0.5 t-small text-text-muted">{text}</p>
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

/** Rules the agent must follow. The app checks them in code (policy-as-code), the model cannot override them. */
export default function Rules() {
  const { rules, setRule, resetDemo, showToast, company } = useAppState();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Rules" subtitle="What the agent may do on its own and what always waits for you · checked in code, not by the AI">
        <Button
          kind="ghost"
          icon={RotateCcw}
          onClick={() => {
            resetDemo();
            showToast({ tone: 'neutral', text: 'Demo reset: cards, History and rules are back to the start.' });
          }}
        >
          Reset demo
        </Button>
      </PageHeader>

      <div className="grid gap-5 xl:grid-cols-2">
        <Rule
          id="RULE-AUTO-01"
          icon={Bot}
          title="Autopilot"
          text={rules.autopilot ? `The agent handles safe actions under ${formatPLN(rules.autopilotLimit)} by itself and logs them in History.` : 'Off. Every action waits for your swipe.'}
          right={<Switch label="Autopilot" checked={rules.autopilot} onChange={(v) => setRule('autopilot', v)} />}
        >
          <Amount label="Acts alone below" value={rules.autopilotLimit} min={0} max={10000} step={500} disabled={!rules.autopilot} onChange={(v) => setRule('autopilotLimit', v)} />
        </Rule>

        <Rule
          id="RULE-HOLD-01"
          icon={Hand}
          title="Extra confirmation for big amounts"
          text={`Every decision needs a short hold (0.6 s). Above ${formatPLN(rules.extraConfirmAbove)} you hold twice as long (1.2 s), so a big payment never goes out by accident.`}
        >
          <Amount label="Longer hold above" value={rules.extraConfirmAbove} min={1000} max={100000} step={1000} onChange={(v) => setRule('extraConfirmAbove', v)} />
        </Rule>

        <Rule
          id="RULE-LIQ-01"
          icon={Wallet}
          title="Never go under the safety buffer"
          text={`The agent does not propose actions that would take the balance under ${formatPLN(rules.safetyBuffer)}.`}
          right={<Switch label="Never go under the safety buffer" checked={rules.keepBuffer} onChange={(v) => setRule('keepBuffer', v)} />}
        >
          <Amount label="Safety buffer" value={rules.safetyBuffer} min={50000} max={300000} step={10000} disabled={!rules.keepBuffer} onChange={(v) => setRule('safetyBuffer', v)} />
        </Rule>

        <Rule
          id="RULE-MAIL-01"
          icon={Mail}
          title="Email only known recipients"
          text="The agent writes only to companies it knows from your invoices and bank transfers. A new address always needs your OK."
          right={<Switch label="Email only known recipients" checked={rules.knownRecipientsOnly} onChange={(v) => setRule('knownRecipientsOnly', v)} />}
        />

        <Rule
          id="RULE-LEARN-01"
          icon={Sparkles}
          title="Learn from my swipes"
          text="After you make the same decision a few times, the agent proposes a rule, e.g. “Always take early-payment discounts above 2% if the buffer holds?”. You approve every rule."
          right={<Switch label="Learn from my swipes" checked={rules.learnFromSwipes} onChange={(v) => setRule('learnFromSwipes', v)} />}
        />

        <Rule
          id="RULE-BANK-01"
          icon={Lock}
          title="Bank actions are simulated"
          locked
          text={`Credit lines, transfers and deposits go to a simulated ${company.bankName || 'Commerzbank'} API and are marked SIMULATED. Nothing reaches a real bank.`}
          right={<Switch label="Bank actions are simulated" checked disabled onChange={() => {}} />}
        />
      </div>

      <p className="flex items-center gap-2 t-small text-green-700">
        <ShieldCheck className="h-4 w-4 shrink-0" /> Numbers on the cards come from the engine. The AI only explains them.
      </p>
    </div>
  );
}
