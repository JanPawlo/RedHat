import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  alerts as initialAlerts,
  company,
  decisionCards,
  defaultRules,
  forecastSummary,
  invoiceGroups,
  invoices as initialInvoices,
  mails as initialMails,
  paidThisMonth,
  pastDecisions,
} from '../data/mockData.js';
import { getExplanation, prefetchExplanations } from './agentStore.js';
import { updateActionStatus } from '../api/actionApi.js';
import { listCards } from '../api/cardApi.js';
import { getCompanyProfile } from '../api/companyApi.js';
import { getForecast } from '../api/forecastApi.js';
import { getInvoicesPage } from '../api/pagesApi.js';
import { HOLD_BIG_MS, HOLD_MS } from '../const/cardMotion.js';
import { formatPLN, setDisplayCurrency } from '../utils/format.js';

const LIVE_HORIZON_DAYS = 90;
const LIVE_REFRESH_MS = 3000;
const BACKEND_STATUS = { approve: 'approved', decline: 'rejected', undo: 'pending' };

/** Company header data from the backend profile and the engine's forecast (falls back to the mock company). */
function liveCompany(profile, forecast) {
  if (!forecast) return company;

  const ownerName = profile?.settings?.owner_name || company.owner.firstName;
  const [firstName, lastName = ''] = ownerName.split(' ');
  const runway = forecast.scenarios?.base?.indicators?.runway_months;

  return {
    ...company,
    name: profile?.name || company.name,
    legalName: profile?.name || company.legalName,
    owner: { firstName, lastName, initials: `${firstName[0] || ''}${lastName[0] || ''}`.toUpperCase() },
    currency: forecast.currency,
    safetyBuffer: Number(forecast.safety_buffer),
    bankBalance: Number(forecast.opening_balance),
    runwayMonths: runway ? Number(runway) : '—',
  };
}

const shortDate = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });
const fmtDate = (iso) => shortDate.format(new Date(`${iso}T00:00:00`));

/** Alerts from the engine: liquidity gap, late-paying customers, and whether approved decisions close the gap. */
function liveAlerts(forecast) {
  const base = forecast.scenarios.base.indicators;
  const after = forecast.after_decisions?.indicators;
  const buffer = Number(forecast.safety_buffer);
  const alerts = [];

  if (base.first_below_buffer_date) {
    alerts.push({
      id: 'live-gap',
      type: after && !after.first_below_buffer_date ? 'info' : 'warning',
      unread: true,
      title: `You drop below your safety buffer in ${base.days_to_buffer_breach} days`,
      message: `Lowest point ${formatPLN(Number(base.lowest_balance))} on ${fmtDate(base.lowest_balance_date)} (buffer ${formatPLN(buffer)}), if you do nothing.`,
      action: 'Open card',
      to: '/#deck',
    });
  }

  forecast.late_payers.forEach((late) => {
    alerts.push({
      id: `live-late-${late.invoice_number}`,
      type: 'error',
      unread: true,
      title: `${late.counterparty} usually pays ${late.typical_delay_days} days late`,
      message: `Invoice ${late.invoice_number} (${formatPLN(Number(late.amount))}) is due ${fmtDate(late.due_date)}; the engine expects the money on ${fmtDate(late.expected_date)}.`,
      action: 'Open card',
      to: '/#deck',
    });
  });

  if (after && base.first_below_buffer_date && !after.first_below_buffer_date) {
    alerts.unshift({
      id: 'live-fixed',
      type: 'success',
      unread: true,
      title: 'Your decisions keep cash above the buffer',
      message: `With the approved cards the lowest point is ${formatPLN(Number(after.lowest_balance))} on ${fmtDate(after.lowest_balance_date)}.`,
      action: 'View',
      to: '/analysis',
    });
  }

  return alerts;
}

const sync = { version: 0, inFlight: 0 };

function syncStatus(card, status) {
  if (!card?.backendId) return Promise.resolve();

  sync.version += 1;
  sync.inFlight += 1;

  return updateActionStatus(card.backendId, { status }).finally(() => {
    sync.version += 1;
    sync.inFlight -= 1;
  });
}

const AppState = createContext(null);

const STORE = { history: 'redcaps.history.v1', queue: 'redcaps.queue.v1', rules: 'redcaps.rules.v1' };

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
  const { id, backendId, category, icon, title, proposal, left, right, confidence, recommendation, resultLabel, amount, bankProduct, agent, autonomy, protects } = card;
  return { id, backendId, category, icon, title, proposal, left, right, confidence, recommendation, resultLabel, amount, bankProduct, agent, autonomy, protects };
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
  const [invoicesMeta, setInvoicesMeta] = useState({ groups: invoiceGroups, paidThisMonth, live: false });
  const [mails, setMails] = useState(initialMails);
  const [toast, setToast] = useState(null);
  const [confirmation, setConfirmation] = useState(null); // id of the history entry just decided
  const [alertsOpen, setAlertsOpen] = useState(false);

  const [apiCards, setApiCards] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [profile, setProfile] = useState(null);
  const [liveError, setLiveError] = useState('');

  const allCards = apiCards || decisionCards;
  const cardsById = useMemo(() => Object.fromEntries(allCards.map((c) => [c.id, c])), [allCards]);

  useEffect(() => write(STORE.history, history), [history]);
  useEffect(() => write(STORE.queue, queue), [queue]);
  useEffect(() => write(STORE.rules, rules), [rules]);

  /** Cards, forecast and company from the backend; the engine recalculates after every decision. */
  const refreshLive = useCallback(async () => {
    try {
      const version = sync.version;
      const [cards, nextForecast, nextProfile] = await Promise.all([
        listCards(),
        getForecast(LIVE_HORIZON_DAYS),
        getCompanyProfile().catch(() => null),
      ]);

      if (sync.inFlight > 0 || version !== sync.version) return;

      setDisplayCurrency(nextForecast.currency);
      setApiCards(cards);
      setForecast(nextForecast);
      setProfile(nextProfile);
      setLiveError('');
    } catch (err) {
      setLiveError(err.message);
    }
  }, []);

  useEffect(() => {
    refreshLive();

    const timer = setInterval(refreshLive, LIVE_REFRESH_MS);
    window.addEventListener('focus', refreshLive);

    return () => {
      clearInterval(timer);
      window.removeEventListener('focus', refreshLive);
    };
  }, [refreshLive]);

  // Deck order follows the backend's pending cards; cards moved to "later" keep their place.
  useEffect(() => {
    if (!apiCards) return;
    const ids = apiCards.map((c) => c.id);
    setHistory((h) => h.filter((e) => e.past || !ids.includes(e.cardId)));
    setQueue((q) => {
      const kept = q.filter((id) => ids.includes(id));
      return [...kept, ...ids.filter((id) => !kept.includes(id))];
    });
  }, [apiCards]);

  useEffect(() => {
    if (forecast) setAlerts(liveAlerts(forecast));
  }, [forecast]);

  // Background analysis of every card as soon as the cards are known.
  useEffect(() => {
    if (apiCards) prefetchExplanations(apiCards);
  }, [apiCards]);

  // Open supplier invoices from the database; paying them stays a SIMULATED action in this session.
  useEffect(() => {
    getInvoicesPage()
      .then((page) => {
        setInvoices(page.invoices);
        setInvoicesMeta({ groups: page.groups, paidThisMonth: page.paidThisMonth, live: true });
      })
      .catch(() => {});
  }, []);

  const showToast = useCallback((t) => setToast({ ...t, key: Date.now() }), []);

  const holdMsFor = useCallback((card) => (card && card.amount > rules.extraConfirmAbove ? HOLD_BIG_MS : HOLD_MS), [rules.extraConfirmAbove]);

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

      syncStatus(card, BACKEND_STATUS[choice])
        .then(refreshLive)
        .catch((err) => showToast({ tone: 'neutral', text: `Could not save the decision: ${err.message}` }));
    },
    [cardsById, showToast, refreshLive],
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

      syncStatus(entry.card, BACKEND_STATUS.undo)
        .then(() => syncStatus(entry.card, BACKEND_STATUS[choice]))
        .then(refreshLive)
        .catch((err) => showToast({ tone: 'neutral', text: `Could not save the change: ${err.message}` }));
    },
    [history, showToast, refreshLive],
  );

  const undoLast = useCallback(() => {
    const last = history.find((e) => !e.past);
    if (!last) return;

    setHistory((h) => h.filter((e) => e.id !== last.id));
    setQueue((q) => [last.cardId, ...q.filter((id) => id !== last.cardId)]);
    setConfirmation(null);
    setToast(null);

    syncStatus(last.card, BACKEND_STATUS.undo).then(refreshLive).catch(() => {});
  }, [history, refreshLive]);

  const resetDemo = useCallback(() => {
    const decided = history.filter((e) => !e.past && e.card?.backendId);

    setHistory(pastDecisions);
    setQueue(allCards.map((c) => c.id));
    setRules(defaultRules);
    setConfirmation(null);

    Promise.all(decided.map((e) => syncStatus(e.card, BACKEND_STATUS.undo).catch(() => {}))).then(refreshLive);
  }, [history, allCards, refreshLive]);

  const sessionDecisions = history.filter((e) => !e.past);
  const baseProtected = apiCards ? 0 : forecastSummary.cashProtectedThisMonth;
  const cashProtected =
    baseProtected + sessionDecisions.filter((d) => d.choice === 'approve').reduce((s, d) => s + (d.card?.protects || cardsById[d.cardId]?.protects || 0), 0);

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
    company: forecast ? liveCompany(profile, forecast) : { ...company, safetyBuffer: rules.safetyBuffer },
    cards: allCards,
    forecast,
    liveError,
    refreshLive,
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
    invoicesMeta,
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
