import { useCallback, useEffect, useState } from 'react';
import { ADVISOR_STORAGE_KEY, MATERIAL_KIND } from '../const/advisor.js';
import { getAdvisorFacts } from '../api/pagesApi.js';
import { analysis, company, forecastSummary } from '../data/mockData.js';

/** Example materials so the page is not empty in the demo (Pizzeria Amalfi, amounts in EUR). */
const SEED = [
  {
    id: 'seed-oven',
    kind: MATERIAL_KIND.note,
    title: 'Second pizza oven',
    text: 'Thinking about buying a second stone pizza oven for about 9,000 EUR. The supplier says the price goes up 6% in February.',
    at: '2025-12-29T18:40:00',
    useInChat: true,
  },
  {
    id: 'seed-voice',
    kind: MATERIAL_KIND.voice,
    title: 'Voice message · Frankfurter Hof',
    text: 'Frankfurter Hof wants catering for 3 company events in February. They would pay about 4,500 EUR, but only 30 days after the events. We would need about 1,200 EUR of extra ingredients in the first week of February.',
    durationSec: 34,
    at: '2025-12-30T08:12:00',
    useInChat: true,
  },
  {
    id: 'seed-meeting',
    kind: MATERIAL_KIND.meeting,
    title: 'Meeting with the Commerzbank advisor',
    text: 'Bank offers an overdraft line of 15,000 EUR. Also a 3-month deposit at 2.5% for free cash. Decision needed by mid January.',
    durationSec: 1860,
    fileName: 'bank-meeting-17-12.m4a',
    at: '2025-12-17T15:00:00',
    useInChat: true,
  },
];

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(ADVISOR_STORAGE_KEY) || 'null');
    return Array.isArray(saved) ? saved : SEED;
  } catch {
    return SEED;
  }
}

function persist(materials) {
  try {
    // Audio stays in memory for this session only; text and metadata survive a refresh.
    localStorage.setItem(ADVISOR_STORAGE_KEY, JSON.stringify(materials.map(({ audioUrl, ...rest }) => rest)));
  } catch {
    /* storage blocked: materials live for this session only */
  }
}

/** Mock facts (Bakery demo, PLN) used only when the backend cannot be reached. */
function mockFacts() {
  const { q4 } = analysis;
  const upcoming = q4.events
    .filter((e) => e.day >= q4.today)
    .map((e) => {
      const d = new Date(q4.start);
      d.setDate(d.getDate() + e.day);
      return { date: d.toISOString().slice(0, 10), what: `${e.label} · ${e.who}`, amount: e.kind === 'in' ? e.amount : -e.amount };
    });
  return {
    company: company.name,
    currency: company.currency,
    today: '2026-11-20',
    bank_balance: company.bankBalance,
    safety_buffer: company.safetyBuffer,
    runway_months: company.runwayMonths,
    lowest_balance_next_days: { amount: forecastSummary.lowest.amount, date: forecastSummary.lowest.date },
    lowest_balance_after_approved_decisions: { amount: forecastSummary.lowestWithActions },
    upcoming_payments: upcoming,
  };
}

/** Engine numbers the advisor may quote (never the model's own): from the database, the mock when offline. */
export async function advisorFacts() {
  try {
    return await getAdvisorFacts();
  } catch {
    return mockFacts();
  }
}

/** Owner's notes, voice messages and meeting summaries chosen for the chat. */
export function advisorNotes(materials) {
  return materials
    .filter((m) => m.useInChat && m.text?.trim())
    .map((m) => ({ type: m.kind, title: m.title, date: m.at.slice(0, 10), text: m.text.trim() }));
}

/** Materials on the Advisor page, saved in the browser. */
export function useAdvisorMaterials() {
  const [materials, setMaterials] = useState(load);

  useEffect(() => persist(materials), [materials]);

  const add = useCallback((material) => {
    setMaterials((list) => [{ id: `m-${Date.now()}`, at: new Date().toISOString(), useInChat: true, ...material }, ...list]);
  }, []);

  const update = useCallback((id, patch) => {
    setMaterials((list) => list.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  }, []);

  const remove = useCallback((id) => {
    setMaterials((list) => {
      const gone = list.find((m) => m.id === id);
      if (gone?.audioUrl) URL.revokeObjectURL(gone.audioUrl);
      return list.filter((m) => m.id !== id);
    });
  }, []);

  return { materials, add, update, remove };
}
