import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { alerts as initialAlerts, company, decisionCards, forecastSummary, invoices as initialInvoices, mails as initialMails } from '../data/mockData.js';

const AppState = createContext(null);

const nowTime = () => new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

/**
 * Front-end only state for the demo: decisions on cards, alerts, invoices and mails.
 * Every decision also lands in `ledger` so the audit log can be built on top of it later.
 */
export function AppStateProvider({ children }) {
  const [queue, setQueue] = useState(decisionCards.map((c) => c.id));
  const [decisions, setDecisions] = useState([]); // { cardId, choice: 'approve'|'decline'|'later', at }
  const [alerts, setAlerts] = useState(initialAlerts);
  const [invoices, setInvoices] = useState(initialInvoices);
  const [mails, setMails] = useState(initialMails);
  const [autopilot, setAutopilot] = useState(true);
  const [toast, setToast] = useState(null);

  const cardsById = useMemo(() => Object.fromEntries(decisionCards.map((c) => [c.id, c])), []);

  const showToast = useCallback((t) => {
    setToast({ ...t, key: Date.now() });
  }, []);

  const decide = useCallback((cardId, choice) => {
    const card = cardsById[cardId];
    setQueue((q) => {
      const rest = q.filter((id) => id !== cardId);
      return choice === 'later' ? [...rest, cardId] : rest;
    });
    if (choice === 'later') {
      showToast({ tone: 'neutral', text: `“${card.title}” moved to the end of the deck.` });
      return;
    }
    setDecisions((d) => [...d, { cardId, choice, at: nowTime() }]);
    if (choice === 'approve') {
      showToast({ tone: 'green', text: card.resultLabel, undo: true });
    } else {
      showToast({ tone: 'neutral', text: 'Declined. I will not suggest this again this week.', undo: true });
    }
  }, [cardsById, showToast]);

  const undoLast = useCallback(() => {
    setDecisions((d) => {
      if (!d.length) return d;
      const last = d[d.length - 1];
      setQueue((q) => [last.cardId, ...q.filter((id) => id !== last.cardId)]);
      return d.slice(0, -1);
    });
    setToast(null);
  }, []);

  const approved = decisions.filter((d) => d.choice === 'approve');
  const cashProtected = forecastSummary.cashProtectedThisMonth + approved.reduce((s, d) => s + (cardsById[d.cardId]?.protects || 0), 0);

  const dismissAlert = (id) => setAlerts((a) => a.filter((x) => x.id !== id));
  const markAllRead = () => setAlerts((a) => a.map((x) => ({ ...x, unread: false })));

  const payInvoice = (id) => setInvoices((list) => list.map((i) => (i.id === id ? { ...i, status: 'paid', selected: false } : i)));
  const scheduleInvoice = (id) => setInvoices((list) => list.map((i) => (i.id === id ? { ...i, status: i.status === 'scheduled' ? undefined : 'scheduled' } : i)));
  const toggleInvoice = (id) => setInvoices((list) => list.map((i) => (i.id === id ? { ...i, selected: !i.selected } : i)));
  const paySelected = () => setInvoices((list) => list.map((i) => (i.selected ? { ...i, status: 'paid', selected: false } : i)));

  const approveMail = (id) => setMails((list) => list.map((m) => (m.id === id ? { ...m, status: 'Sent', timeline: [...m.timeline, ['Approved by you', nowTime()], ['Sent', nowTime()]] } : m)));

  const value = {
    company,
    queue: queue.map((id) => cardsById[id]),
    decisions,
    decide,
    undoLast,
    cashProtected,
    alerts,
    dismissAlert,
    markAllRead,
    invoices,
    payInvoice,
    scheduleInvoice,
    toggleInvoice,
    paySelected,
    mails,
    approveMail,
    autopilot,
    setAutopilot,
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
