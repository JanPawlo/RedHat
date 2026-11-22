import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, FileText, Landmark, Lock, Mail, Percent, RotateCcw, Send, ShieldCheck, Sparkles } from 'lucide-react';
import { useAppState } from '../state/AppState.jsx';
import { analysis, defaultRules, learnedRules } from '../data/mockData.js';
import { Button, Chip, PageHeader, Segmented } from '../components/ui/primitives.jsx';
import { Amount, RuleRow, Section, Stepper, Switch } from '../components/rules/RuleParts.jsx';
import {
  ALERT_RULES,
  AUTOMATION_LEVELS,
  FIXED_COST_LABELS,
  LIMITS,
  MESSAGE_ACTIONS,
  MESSAGE_MODES,
  PAYMENT_ACTIONS,
  PAYMENT_MODES,
  SAFETY_RULES,
  TAX_LABELS,
  TAX_RESERVE_DAYS,
} from '../const/rules.js';
import { cx, formatPLN } from '../utils/format.js';

const ACTION_ICONS = { reminder: Mail, supplierMail: Send, invoicePay: FileText, earlyPay: Percent, bankProduct: Landmark };
const MONTH_DAYS = 30;

/** Taxes due in the next weeks (set aside, never used by the agent) and one month of fixed costs. */
function useMoneyFacts() {
  return useMemo(() => {
    const { events, today } = analysis.q4;
    const out = events.filter((e) => e.kind === 'out');
    const sum = (list) => list.reduce((s, e) => s + e.amount, 0);
    const taxes = out.filter((e) => e.day >= today && e.day < today + TAX_RESERVE_DAYS && TAX_LABELS.some((l) => e.label.startsWith(l)));
    const lastMonth = out.filter((e) => e.day < today && e.day >= today - MONTH_DAYS && FIXED_COST_LABELS.some((l) => e.label.startsWith(l)));
    return { taxReserve: sum(taxes), taxNames: taxes.map((e) => e.label).join(' + '), monthlyFixed: sum(lastMonth) };
  }, []);
}

function Card({ children, className }) {
  return <div className={cx('card flex flex-col divide-y divide-line py-1', className)}>{children}</div>;
}

function YourMoney({ rules, setRule }) {
  const { taxReserve, taxNames, monthlyFixed } = useMoneyFacts();
  const months = monthlyFixed ? (rules.safetyBuffer / monthlyFixed).toFixed(1) : null;
  return (
    <Section title="Your money" text="The limits the engine plans with. Every card and forecast respects them.">
      <Card>
        <div className="py-3.5">
          <RuleRow ruleId="RULE-LIQ-01" title="Safety buffer" text="The balance the agent never plans to go under." />
          <Amount
            label="Keep at least"
            value={rules.safetyBuffer}
            {...LIMITS.buffer}
            onChange={(v) => setRule('safetyBuffer', v)}
            hint={months && `≈ ${months} months of fixed costs (rent, payroll, ZUS: ${formatPLN(monthlyFixed)} a month)`}
          />
        </div>
        <RuleRow
          ruleId="RULE-TAX-01"
          title="Keep money for taxes"
          text={`${formatPLN(taxReserve)} for ${taxNames} in the next ${TAX_RESERVE_DAYS} days is set aside. Deposits and early payments never use it.`}
          control={<Switch label="Keep money for taxes" checked={rules.keepTaxReserve} onChange={(v) => setRule('keepTaxReserve', v)} />}
        />
      </Card>
    </Section>
  );
}

function ActionRow({ action, icon: IconCmp, options, value, onChange }) {
  return (
    <div className="flex flex-col gap-3 py-3.5 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-green-100 text-green-700">
          <IconCmp className="h-4 w-4" strokeWidth={1.8} />
        </span>
        <div className="min-w-0">
          <p className="t-body-m">
            {action.title} <span className="ml-1 t-mono text-[11px] text-text-muted">{action.ruleId}</span>
          </p>
          <p className="t-small text-text-muted">{action.text}</p>
        </div>
      </div>
      {action.locked ? (
        <Chip tone="blue" dot={false}>
          <Lock className="mr-1 inline h-3 w-3" />
          {action.locked}
        </Chip>
      ) : (
        <Segmented options={options} value={value} onChange={onChange} className="self-start lg:self-auto" />
      )}
    </div>
  );
}

/** Saved mode for an action, or the default when the stored value is not one of the options (older saves). */
function modeOf(rules, id, options) {
  const saved = rules.actions?.[id];
  return options.some((o) => o.value === saved) ? saved : defaultRules.actions[id];
}

function AgentActions({ rules, setRule }) {
  const setMode = (id, mode) => setRule('actions', { ...rules.actions, [id]: mode });
  const off = !rules.autopilot;
  return (
    <Section title="What the agent may do" text="It can send messages for you. It never sends money: payments are only prepared, and you approve them in your bank.">
      <div className="py-2">
        <RuleRow
          ruleId="RULE-AUTO-01"
          title="Automation level"
          text="When automated, decisions below big amounts execute automatically according to policy."
          control={
            <Segmented
              options={AUTOMATION_LEVELS}
              value={rules.automationLevel || 'automated'}
              onChange={(v) => setRule('automationLevel', v)}
            />
          }
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 px-1">
        <p className="t-overline text-text-muted">Messages</p>
        <label className="flex items-center gap-2.5 t-small">
          <Bot className="h-4 w-4 text-green-700" /> Autopilot for messages
          <Switch label="Autopilot for messages" checked={rules.autopilot} onChange={(v) => setRule('autopilot', v)} />
        </label>
      </div>
      {off && <p className="rounded-tile bg-status-amber-soft px-4 py-3 t-small">Autopilot is off, so every message waits for your OK. The choices below apply again when you turn it on.</p>}
      <Card className={cx(off && 'opacity-60')}>
        {MESSAGE_ACTIONS.map((a) => (
          <ActionRow key={a.id} action={a} icon={ACTION_ICONS[a.id]} options={MESSAGE_MODES} value={modeOf(rules, a.id, MESSAGE_MODES)} onChange={(v) => setMode(a.id, v)} />
        ))}
      </Card>

      <p className="mt-2 px-1 t-overline text-text-muted">Payments</p>
      <Card>
        {PAYMENT_ACTIONS.map((a) => (
          <ActionRow key={a.id} action={a} icon={ACTION_ICONS[a.id]} options={PAYMENT_MODES} value={modeOf(rules, a.id, PAYMENT_MODES)} onChange={(v) => setMode(a.id, v)} />
        ))}
        <div className="py-4">
          <RuleRow ruleId="RULE-HOLD-01" title="Big amount" text={`Above ${formatPLN(rules.extraConfirmAbove)} you hold the card twice as long to confirm, so a big payment is never approved by accident.`} />
          <Amount label="Big amount from" value={rules.extraConfirmAbove} {...LIMITS.bigAmount} onChange={(v) => setRule('extraConfirmAbove', v)} />
        </div>
      </Card>
    </Section>
  );
}

function AlwaysOn() {
  return (
    <Section title="Always on" text="Checked in code on every action. The AI cannot switch them off; when one stops an action, History shows “Blocked by” and the rule.">
      <div className="grid gap-3 md:grid-cols-2">
        {SAFETY_RULES.map((r) => (
          <div key={r.ruleId} className="flex items-start gap-3 rounded-tile bg-surface p-4">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-green-700" strokeWidth={1.8} />
            <div className="min-w-0">
              <p className="t-body-m">
                {r.title} <span className="ml-1 t-mono text-[11px] text-text-muted">{r.ruleId}</span>
              </p>
              <p className="t-small text-text-muted">{r.text}</p>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

function Alerts({ rules, setRule }) {
  return (
    <Section title="Warn me when" text="These go to the bell, top right.">
      <Card>
        {ALERT_RULES.map((a) => (
          <RuleRow
            key={a.key}
            ruleId={a.ruleId}
            title={a.title}
            control={<Stepper label={a.title} value={rules[a.key]} min={a.min} max={a.max} step={a.step} unit={a.unit} onChange={(v) => setRule(a.key, v)} />}
          />
        ))}
      </Card>
    </Section>
  );
}

function Learned({ rules, setRule }) {
  return (
    <Section
      title="Learned from your decisions"
      text="When you decide the same way a few times, the agent suggests a rule. Nothing applies until you turn it on."
      right={
        <label className="flex items-center gap-2.5 t-small">
          <Sparkles className="h-4 w-4 text-green-700" /> Suggest new rules
          <Switch label="Suggest new rules" checked={rules.learnFromSwipes} onChange={(v) => setRule('learnFromSwipes', v)} />
        </label>
      }
    >
      <Card>
        {learnedRules.map((r) => (
          <RuleRow
            key={r.id}
            ruleId={r.ruleId}
            title={r.text}
            text={r.basis}
            muted={!rules.learned?.[r.id]}
            control={<Switch label={r.text} checked={!!rules.learned?.[r.id]} onChange={(v) => setRule('learned', { ...rules.learned, [r.id]: v })} />}
          />
        ))}
      </Card>
    </Section>
  );
}

/** Rules the agent must follow. The app checks them in code (policy-as-code); the model cannot override them. */
export default function Rules() {
  const { rules, setRule } = useAppState();
  const navigate = useNavigate();

  return (
    <div className="flex max-w-[1040px] flex-col gap-8">
      <PageHeader title="Rules" subtitle="What the agent may do, what always waits for you, and when it warns you · checked in code, not by the AI">
        <Button kind="ghost" icon={RotateCcw} onClick={() => navigate('/demo-reset')}>
          Reset demo
        </Button>
      </PageHeader>

      <YourMoney rules={rules} setRule={setRule} />
      <AgentActions rules={rules} setRule={setRule} />
      <AlwaysOn />
      <Alerts rules={rules} setRule={setRule} />
      <Learned rules={rules} setRule={setRule} />

      <p className="flex items-center gap-2 t-small text-green-700">
        <ShieldCheck className="h-4 w-4 shrink-0" /> Numbers on the cards come from the engine. The AI only explains them.
      </p>
    </div>
  );
}
