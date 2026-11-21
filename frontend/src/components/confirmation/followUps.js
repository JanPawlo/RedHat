import { CalendarPlus, Mail } from 'lucide-react';

/**
 * Follow-up actions offered on the Confirmation screen after a card is approved.
 * A card lists the ones it supports in `followUps: ['scheduleMail', 'calendar']`.
 * To add a new scenario, add an entry here: { label, icon, doneLabel, available(card), run(ctx) }.
 * `run` gets { card, entry, app } where `app` is the AppState (addMail, showToast, …).
 */

const nowTime = () => new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

function icsDate(d) {
  return d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
}

export const FOLLOW_UPS = {
  scheduleMail: {
    label: 'Schedule your mail',
    hint: 'Goes out today at 16:00, you can still edit it in Mail',
    icon: Mail,
    doneLabel: 'Mail scheduled for 16:00 · see Mail → Scheduled',
    available: (card) => Boolean(card.mail),
    run: ({ card, app }) => {
      const { to, initials, subject, body } = card.mail;
      app.addMail({
        to,
        initials,
        subject,
        body,
        time: '16:00',
        status: 'Scheduled',
        snippet: body[1] || body[0],
        card: card.title,
        agent: `${card.agent} agent`,
        timeline: [['Drafted by AI', nowTime()], ['Approved by you', nowTime()], ['Scheduled', 'today 16:00']],
      });
    },
  },
  calendar: {
    label: 'Add a reminder to my calendar',
    hint: 'Downloads an .ics file for tomorrow 9:00',
    icon: CalendarPlus,
    doneLabel: 'Calendar reminder downloaded',
    available: () => true,
    run: ({ card }) => {
      const start = new Date();
      start.setDate(start.getDate() + 1);
      start.setHours(9, 0, 0, 0);
      const end = new Date(start.getTime() + 15 * 60 * 1000);
      const ics = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//RedCaps CFO//EN',
        'BEGIN:VEVENT',
        `UID:${card.id}-${Date.now()}@redcaps`,
        `DTSTAMP:${icsDate(new Date())}`,
        `DTSTART:${icsDate(start)}`,
        `DTEND:${icsDate(end)}`,
        `SUMMARY:Check: ${card.title.replace(/[,;]/g, ' ')}`,
        `DESCRIPTION:${(card.resultLabel || '').replace(/[,;]/g, ' ')}`,
        'END:VEVENT',
        'END:VCALENDAR',
      ].join('\r\n');
      const url = URL.createObjectURL(new Blob([ics], { type: 'text/calendar' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `reminder-${card.id}.ics`;
      a.click();
      URL.revokeObjectURL(url);
    },
  },
};

export function followUpsFor(card) {
  return (card?.followUps || []).map((key) => ({ key, ...FOLLOW_UPS[key] })).filter((f) => f.label && f.available(card));
}
