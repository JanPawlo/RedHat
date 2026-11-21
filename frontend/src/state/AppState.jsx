import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  alerts as initialAlerts,
  company,
  decisionCards,
  defaultRules,
  forecastSummary,
  invoices as initialInvoices,
  mails as initialMails,
  pastDecisions,
} from '../data/mockData.js';
import { getExplanation, prefetchExplanations } from './agentStore.js';

const AppState = createContext(null);

const STORE = { history: 'redcaps.history.v1', queue: 'redcaps.queue.v1', rules: 'redcaps.rules.v1' };
const BASE_HOLD_MS = 600;
const BIG_HOLD_MS = 1200;

const nowTime = () => new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

function read(key, fallback) {
  try {
    const v = localStorage.getItem(key);
    return v ? JSON.parse(v) : fallback;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage blocked: state lives for this session only */
  }
}

/** The parts of a card History needs, so an entry still renders if the card later disappears. */
function snapshot(card) {
  const { id, category, icon, title, proposal, left, right, confidence, recommendation, resultLabel, amount, bankProduct, agent, autonomy } = card;
  return { id, category, icon, title, proposal, left, right, confidence, recommendation, resultLabel, amount, bankProduct, agent, autonomy };
}

function initialQueue(history) {
  const decided = new Set(history.filter((d) => !d.past).map((d) => d.cardId));
  const all = decisionCards.map((c) => c.id);
  const saved = read(STORE.queue, null);
  if (!saved) return all.filter((id) => !decided.has(id));
  const known = saved.filter((id) => all.includes(id) && !decided.has(id));
  const fresh = all.filter((id) => !known.includes(id) && !decided.has(id));
  return [...known, ...fresh];
}

/**
 * Front-end state for the demo: card decisions (with History), rules, alerts, invoices and mails.
 * History, the deck order and the rules survive a page refresh (localStorage).
 */
export function AppStateProvider({ children }) {
  const [history, setHistory] = useState(() => read(STORE.history, pastDecisions));
  const [queue, setQueue] = useState(() => initialQueue(read(STORE.history, [])));
  const [rules, setRules] = useState(() => ({ ...defaultRules, ...read(STORE.rules, {}) }));
  const [alerts, setAlerts] = useState(initialAlerts);
  const [invoices, setInvoices] = useState(initialInvoices);
  const [mails, setMails] = useState(initialMails);
  const [toast, setToast] = useState(null);
  const [confirmation, setConfirmation] = useState(null); // id of the history entry just decided
  const [alertsOpen, setAlertsOpen] = useState(false);

  const cardsById = useMemo(() => Object.fromEntries(decisionCards.map((c) => [c.id, c])), []);

  useEffect(() => write(STORE.history, history), [history]);
  useEffect(() => write(STORE.queue, queue), [queue]);
  useEffect(() => write(STORE.rules, rules), [rules]);

  // Background analysis of every card as soon as the app is open.
  useEffect(() => {
    prefetchExplanations(queue.map((id) => cardsById[id]).filter(Boolean));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const showToast = useCallback((t) => setToast({ ...t, key: Date.now() }), []);

  const holdMsFor = useCallback((card) => (card && card.amount > rules.extraConfirmAbove ? BIG_HOLD_MS : BASE_HOLD_MS), [rules.extraConfirmAbove]);

  const decide = useCallback(
    (cardId, choice) => {
      const card = cardsById[cardId];
      if (!card) return;
      setQueue((q) => {
        const rest = q.filter((id) => id !== cardId);
        return choice === 'later' ? [...rest, cardId] : rest;
      });
      if (choice === 'later') {
        showToast({ tone: 'neutral', text: `“${card.title}” moved to the end of the deck.` });
        return;
      }
      const ai = getExplanation(card);
      const entry = {
        id: `${cardId}-${Date.now()}`,
        cardId,
        choice,
        at: new Date().toISOString(),
        card: snapshot(card),
        ai: ai ? { answer: ai.answer, model: ai.model } : null,
        fallback: card.back?.description,
        actions: [],
      };
      setHistory((h) => [entry, ...h]);
      setConfirmation(entry.id);
    },
    [cardsById, showToast],
  );

  /** Records a follow-up action from the Confirmation screen on the history entry. */
  const addEntryAction = useCallback((entryId, label) => {
    setHistory((h) => h.map((e) => (e.id === entryId ? { ...e, actions: [...(e.actions || []), label] } : e)));
  }, []);

  /** Changes a decision already in History (approve ↔ decline); the earlier choice is kept in `changes`. */
  const changeDecision = useCallback(
    (entryId, choice) => {
      const entry = history.find((e) => e.id === entryId);
      if (!entry || entry.choice === choice) return;
      const label = choice === 'approve' ? entry.card.right : entry.card.left;
      setHistory((h) =>
        h.map((e) =>
          e.id === entryId
            ? { ...e, choice, changes: [...(e.changes || []), { from: e.choice, to: choice, at: new Date().toISOString() }] }
            : e,
        ),
      );
      showToast({ tone: 'green', text: `Decision changed to “${label}” · SIMULATED actions updated` });
    },
    [history, showToast],
  );

  const undoLast = useCallback(() => {
    setHistory((h) => {
      const last = h.find((e) => !e.past);
      if (!last) return h;
      setQueue((q) => [last.cardId, ...q.filter((id) => id !== last.cardId)]);
      return h.filter((e) => e.id !== last.id);
    });
    setConfirmation(null);
    setToast(null);
  }, []);

  const resetDemo = useCallback(() => {
    setHistory(pastDecisions);
    setQueue(decisionCards.map((c) => c.id));
    setRules(defaultRules);
    setConfirmation(null);
  }, []);

  const sessionDecisions = history.filter((e) => !e.past);
  const cashProtected =
    forecastSummary.cashProtectedThisMonth + sessionDecisions.filter((d) => d.choice === 'approve').reduce((s, d) => s + (cardsById[d.cardId]?.protects || 0), 0);

  const dismissAlert = (id) => setAlerts((a) => a.filter((x) => x.id !== id));
  const markAllRead = () => setAlerts((a) => a.map((x) => ({ ...x, unread: false })));

  const payInvoice = (id) => setInvoices((list) => list.map((i) => (i.id === id ? { ...i, status: 'paid', selected: false } : i)));
  const scheduleInvoice = (id) => setInvoices((list) => list.map((i) => (i.id === id ? { ...i, status: i.status === 'scheduled' ? undefined : 'scheduled' } : i)));
  const toggleInvoice = (id) => setInvoices((list) => list.map((i) => (i.id === id ? { ...i, selected: !i.selected } : i)));
  const paySelected = () => setInvoices((list) => list.map((i) => (i.selected ? { ...i, status: 'paid', selected: false } : i)));

  const approveMail = (id) => setMails((list) => list.map((m) => (m.id === id ? { ...m, status: 'Sent', timeline: [...m.timeline, ['Approved by you', nowTime()], ['Sent', nowTime()]] } : m)));
  const addMail = useCallback((mail) => setMails((list) => [{ ...mail, id: `m-${Date.now()}` }, ...list]), []);

  const setRule = useCallback((key, value) => setRules((r) => ({ ...r, [key]: value })), []);

  const value = {
    company: { ...company, autopilotLimit: rules.autopilotLimit },
    cards: decisionCards,
    queue: queue.map((id) => cardsById[id]).filter(Boolean),
    decisions: sessionDecisions,
    history,
    decide,
    undoLast,
    resetDemo,
    cashProtected,
    holdMsFor,
    confirmation: history.find((e) => e.id === confirmation) || null,
    closeConfirmation: () => setConfirmation(null),
    addEntryAction,
    changeDecision,
    alerts,
    alertsOpen,
    setAlertsOpen,
    dismissAlert,
    markAllRead,
    invoices,
    payInvoice,
    scheduleInvoice,
    toggleInvoice,
    paySelected,
    mails,
    approveMail,
    addMail,
    rules,
    setRule,
    autopilot: rules.autopilot,
    toast,
    clearToast: () => setToast(null),
    showToast,
  };
  return <AppState.Provider value={value}>{children}</AppState.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppState);
  if (!ctx) throw new Error('useAppState must be used inside <AppStateProvider>');
  return ctx;
}
