import React from 'react';
import { ChevronLeft, ChevronRight, TriangleAlert } from 'lucide-react';
import { cashCalendar } from '../../data/mockData.js';
import { getCashCalendar } from '../../api/pagesApi.js';
import { usePageData } from '../../state/pageDataStore.js';
import { cx, formatPLN } from '../../utils/format.js';

// NOTE: kept ready but not shown anywhere yet (decision 2026-11-20: calendar removed from the dashboard). Data comes from GET /analysis/calendar.
const HEAT = ['bg-subtle text-text-muted', 'bg-heat-1 text-white', 'bg-heat-2', 'bg-heat-3', 'bg-heat-4', 'bg-heat-5 text-white'];

export default function CashCalendar({ data: given }) {
  const live = usePageData('calendar', getCashCalendar, cashCalendar);
  const data = given || live;
  const weeks = [];
  for (let i = 0; i < data.days.length; i += 7) weeks.push(data.days.slice(i, i + 7));
  return (
    <section className="card flex w-[368px] flex-col gap-3.5" aria-label="Cash calendar">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="t-title">Cash calendar</h2>
          <p className="t-small text-text-muted">{data.range} · daily balance</p>
        </div>
        <div className="flex gap-1.5">
          <button type="button" aria-label="Previous" className="flex h-8 w-8 items-center justify-center rounded-full bg-subtle hover:bg-line"><ChevronLeft className="h-4 w-4" /></button>
          <button type="button" aria-label="Next" className="flex h-8 w-8 items-center justify-center rounded-full bg-subtle hover:bg-line"><ChevronRight className="h-4 w-4" /></button>
        </div>
      </div>
      <div className="grid grid-cols-7 gap-1.5 text-center">
        {(data.dayNames || ['M', 'T', 'W', 'T', 'F', 'S', 'S']).map((d, i) => <span key={i} className="t-overline text-text-muted">{d}</span>)}
        {weeks.flat().map((d) => (
          <span key={d.date || `${d.month}-${d.day}`} title={d.balance != null ? `${d.day} ${d.month} · ${formatPLN(d.balance)}` : `${d.day} ${d.month}`} className={cx('flex h-10 items-center justify-center rounded-xl t-small', HEAT[d.level], d.today && 'ring-[2.5px] ring-inset ring-green-900')}>
            {d.day}
          </span>
        ))}
      </div>
      <div className="flex items-center gap-1.5">
        <span className="t-small text-text-muted">Tight</span>
        {[1, 2, 3, 4, 5].map((l) => <span key={l} className={cx('h-2.5 w-7 rounded-full', HEAT[l].split(' ')[0])} />)}
        <span className="t-small text-text-muted">Comfortable</span>
      </div>
      <div className="flex items-center gap-2.5 rounded-2xl bg-status-red-soft px-3 py-2.5">
        <TriangleAlert className="h-[18px] w-[18px] shrink-0 text-status-red" />
        <p className="t-small">{data.hardestWeek}</p>
      </div>
    </section>
  );
}
