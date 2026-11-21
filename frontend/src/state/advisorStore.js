import { useCallback, useEffect, useState } from 'react';
import { ADVISOR_STORAGE_KEY, MATERIAL_KIND } from '../const/advisor.js';
import { analysis, company, forecastSummary } from '../data/mockData.js';

/** Example materials so the page is not empty in the demo. */
const SEED = [
  {
    id: 'seed-oven',
    kind: MATERIAL_KIND.note,
    title: 'Second deck oven',
    text: 'Thinking about buying a second deck oven for about 45,000 PLN before Christmas. The supplier says the price goes up 8% in January.',
    at: '2026-11-19T18:40:00',
    useInChat: true,
  },
  {
    id: 'seed-voice',
    kind: MATERIAL_KIND.voice,
    title: 'Voice message · Hotel Wawel',
    text: 'Hotel Wawel wants 30 extra Christmas trays. They pay on delivery, on 20 December. We would need about 6,000 PLN of extra flour and butter in the first week of December.',
    durationSec: 34,
    at: '2026-11-20T08:12:00',
    useInChat: true,
  },
  {
    id: 'seed-meeting',
    kind: MATERIAL_KIND.meeting,
    title: 'Meeting with the Commerzbank advisor',
    text: 'Bank offers an overdraft line of 60,000 PLN. Also a 3-month deposit at 4.2% for free cash. Decision needed by the end of November.',
    durationSec: 1860,
    fileName: 'bank-meeting-14-11.m4a',
    at: '2026-11-14T15:00:00',
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

/** Engine numbers the advisor may quote (never the model's own). */
export function advisorFacts() {
  const { q4 } = analysis;
  const upcoming = q4.events
    .filter((e) => e.day >= q4.today)
    .map((e) => {
      const d = new Date(q4.start);
      d.setDate(d.getDate() + e.day);
      return { date: d.toISOString().slice(0, 10), what: `${e.label} · ${e.who}`, direction: e.kind, amount_pln: e.amount };
    });
  return {
    company: company.name,
    today: '2026-11-20',
    bank_balance_pln: company.bankBalance,
    safety_buffer_pln: company.safetyBuffer,
    runway_months: company.runwayMonths,
    lowest_balance_next_60_days: { amount_pln: forecastSummary.lowest.amount, date: forecastSummary.lowest.date, under_buffer_pln: forecastSummary.lowest.underBuffer },
    lowest_balance_after_approved_actions_pln: forecastSummary.lowestWithActions,
    upcoming_payments: upcoming,
  };
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
