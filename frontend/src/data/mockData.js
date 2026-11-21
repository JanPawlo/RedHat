// Demo data for Piekarnia Kowalski (numbers match the Figma screens).
// Replace pieces of this file with API calls as the backend grows.

export const TODAY = new Date(2026, 10, 20); // 20 Nov 2026

export const company = {
  name: 'Piekarnia Kowalski',
  legalName: 'Piekarnia Kowalski Sp. z o.o.',
  owner: { firstName: 'Jan', lastName: 'Kowalski', initials: 'JK' },
  currency: 'PLN',
  safetyBuffer: 150000,
  bankBalance: 412300,
  runwayMonths: 7.4,
  autopilotLimit: 2000,
};

// ---------- Forecast ----------
// Key points in thousands of PLN by day offset from TODAY; the chart interpolates daily values.
export const forecastKeyPoints = {
  baseline: [
    [0, 412], [3, 398], [6, 384], [10, 334], [13, 300], [16, 214], [19, 118.4], [21, 124], [24, 196],
    [28, 232], [32, 252], [36, 238], [40, 262], [45, 282], [50, 250], [55, 272], [60, 294],
    [65, 280], [70, 300], [75, 288], [80, 310], [85, 296], [90, 318],
  ],
  afterActions: [
    [0, 412], [3, 398], [6, 384], [10, 334], [13, 306], [16, 238], [19, 168], [21, 176], [24, 240],
    [28, 272], [32, 292], [36, 282], [40, 306], [45, 322], [50, 298], [55, 318], [60, 340],
    [65, 328], [70, 346], [75, 336], [80, 356], [85, 344], [90, 362],
  ],
};

export const forecastSummary = {
  lowest: { amount: 118400, date: '9 Dec', underBuffer: 31600 },
  lowestWithActions: 168000,
  cashProtectedThisMonth: 14800,
};

// ---------- Alerts ----------
export const alerts = [
  {
    id: 'a1', type: 'warning', unread: true,
    title: 'You drop below your safety buffer in 18 days',
    message: 'Rent, payroll and ZUS land in the week of 7 Dec. Lowest point 118,400 PLN on 9 Dec (buffer 150,000 PLN).',
    action: 'Open card', to: '/#deck',
  },
  {
    id: 'a2', type: 'error', unread: true,
    title: 'Mleczarnia Łąka invoice is 3 days overdue',
    message: '6,420 PLN, FV/2026/11/118. Their bank account also changed 3 days ago.',
    action: 'Pay safely', to: '/invoices',
  },
  {
    id: 'a3', type: 'error', unread: true,
    title: 'Hotel Pod Różą was added to the debtor registry',
    message: 'They owe you 9,600 PLN and pay 14 days late on average.',
    action: 'See invoices', to: '/invoices',
  },
  {
    id: 'a4', type: 'info', unread: false,
    title: 'Młyn Nowak: 4% early-pay discount ends today',
    message: 'Pay 14,208 PLN instead of 14,800 PLN by midnight.',
    action: 'Open card', to: '/#deck',
  },
  {
    id: 'a5', type: 'success', unread: false,
    title: 'Landlord agreed to move December rent',
    message: '18,000 PLN now leaves on 15 Dec. Forecast updated.',
    action: 'View', to: '/mail',
  },
];

// ---------- Decision cards ----------
export const decisionCards = [
  {
    id: 'c-overdraft',
    agent: 'Liquidity',
    category: 'LIQUIDITY',
    icon: 'landmark',
    bankProduct: true,
    autonomy: 'Requires approval',
    title: 'Raise the overdraft for December?',
    proposal: 'Raise the limit to 80,000 PLN for 30 days. Cost ≈ 420 PLN, cash stays above your buffer.',
    confidence: 86,
    recommendation: 'right',
    left: 'Keep current limit',
    right: 'Raise to 80k',
    // What each decision leads to (shown while the card is dragged toward it). Numbers from the engine.
    outcomes: {
      left: ['No extra cost', '5 days under the safety buffer from 9 Dec', 'Lowest balance 118,400 PLN'],
      right: ['Cost ≈ 420 PLN for 30 days', 'Cash stays above the buffer', 'Request goes to Commerzbank · SIMULATED'],
    },
    protects: 31600,
    amount: 80000,
    resultLabel: 'Overdraft request sent to the bank · SIMULATED',
    followUps: ['calendar'],
    next: { sub: 'Liquidity · covers the 9 Dec gap', chip: '+31,600 PLN', tone: 'green' },
    back: {
      description:
        'Rent, payroll and ZUS all leave in the week of 7 Dec. Card payouts only arrive on the 14th, so for 5 days you would sit 31,600 PLN under your safety buffer.',
      facts: [
        ['Lowest balance · 9 Dec', '118,400 PLN'],
        ['Safety buffer', '150,000 PLN'],
        ['Payroll + ZUS · 10 Dec', '96,200 PLN'],
        ['Card payouts · 14 Dec', '+61,000 PLN'],
      ],
      weeks: [62, 54, 40, 28, 46, 58, 64, 66],
      weeksIfApproved: [62, 56, 48, 42, 50, 60, 66, 68],
      bufferLevel: 36,
      sources: 'Bank feed · KSeF e-invoices · payroll export',
      questions: ['What if I pay the supplier a week later?', 'How much does it cost?', 'What are the other options?', 'Explain it more simply'],
    },
  },
  {
    id: 'c-mlyn',
    agent: 'Payables',
    category: 'PAYABLES',
    icon: 'package',
    autonomy: 'Requires approval',
    title: 'Pay Młyn Nowak 21 days early, take 4%?',
    proposal: 'Invoice FV/11/0412 · 14,800 PLN. Paying today saves 592 PLN. The discount ends at midnight.',
    confidence: 78,
    recommendation: 'right',
    left: 'Pay on due date',
    right: 'Pay early, save 592',
    outcomes: {
      left: ['Pay 14,800 PLN on 11 Dec', 'No discount', 'More cash on hand until December'],
      right: ['Pay 14,208 PLN today', 'You save 592 PLN', 'Balance stays above the buffer'],
    },
    protects: 592,
    amount: 14208,
    resultLabel: 'Early payment scheduled · SIMULATED',
    followUps: ['scheduleMail', 'calendar'],
    mail: { to: 'Młyn Nowak', initials: 'MN', subject: 'Early payment of FV/11/0412 with 4% discount', body: ['Dear Mr Nowak,', 'We will pay invoice FV/11/0412 today and use the 4% early-payment discount. The transfer will be 14,208 PLN.', 'Kind regards,\nJan Kowalski, Piekarnia Kowalski'] },
    holdToConfirm: true,
    next: { sub: 'Payables · 4% off, discount ends today', chip: '+592 PLN', tone: 'green' },
    back: {
      description:
        'A 4% discount for 21 days is worth about 70% a year, far more than your overdraft costs. With the higher overdraft the buffer still holds.',
      facts: [
        ['Invoice FV/11/0412', '14,800 PLN'],
        ['Due date', '11 Dec 2026'],
        ['Early-pay discount', '−592 PLN'],
        ['Lowest balance after paying', '153,800 PLN'],
      ],
      weeks: [60, 52, 38, 30, 46, 58, 64, 66],
      weeksIfApproved: [57, 49, 36, 28, 44, 56, 62, 64],
      bufferLevel: 36,
      sources: 'KSeF e-invoice FV/11/0412 · bank feed',
      questions: ['What if I pay half now?', 'Is the supplier reliable?', 'Explain it more simply'],
    },
  },
  {
    id: 'c-hotel',
    agent: 'Collections',
    category: 'COLLECTIONS',
    icon: 'building',
    autonomy: 'Email needs your OK',
    title: 'Remind Hotel Pod Różą about FV/10/0388?',
    proposal: 'The invoice is 14 days late · 9,600 PLN. I will send a polite reminder and ask for payment by 27 Nov.',
    confidence: 91,
    recommendation: 'right',
    left: 'Wait a week',
    right: 'Send reminder',
    outcomes: {
      left: ['No email for 7 more days', '9,600 PLN stays unpaid', 'Hotel is on the debtor registry'],
      right: ['Polite reminder drafted in Mail', 'Asks for 9,600 PLN by 27 Nov', 'Nothing leaves without your OK'],
    },
    protects: 9600,
    amount: 9600,
    resultLabel: 'Reminder drafted · waiting in Mail',
    followUps: ['scheduleMail', 'calendar'],
    mail: { to: 'Hotel Pod Różą', initials: 'HR', subject: 'Reminder: invoice FV/10/0388 (9,600 PLN)', body: ['Dear Sir or Madam,', 'Invoice FV/10/0388 for 9,600 PLN is 14 days past due. Could you please pay it by 27 November?', 'Kind regards,\nJan Kowalski, Piekarnia Kowalski'] },
    next: { sub: 'Collections · 14 days late', chip: '+9,600 PLN', tone: 'amber' },
    back: {
      description:
        'Hotel Pod Różą pays 14 days late on average and was added to the debtor registry (KRZ) in October. The longer we wait, the lower the chance of getting paid.',
      facts: [
        ['Invoice FV/10/0388', '9,600 PLN'],
        ['Days overdue', '14'],
        ['Average delay (12 mo)', '14 days'],
        ['Debtor registry (KRZ)', 'Listed since Oct'],
      ],
      weeks: [62, 54, 40, 28, 46, 58, 64, 66],
      weeksIfApproved: [62, 54, 44, 32, 48, 58, 64, 66],
      bufferLevel: 36,
      sources: 'KSeF sales invoices · bank feed · KRZ',
      questions: ['Write it more firmly', 'Should I ask for prepayment next time?', 'Explain it more simply'],
    },
  },
  {
    id: 'c-dairy',
    agent: 'Margin guard',
    category: 'MARGIN GUARD',
    icon: 'trendingUp',
    autonomy: 'Email needs your OK',
    title: 'Dairy prices up 11%. Push back?',
    proposal: 'Mleczarnia Łąka raised milk and butter prices by 11% in October (≈ 1,240 PLN a month). I will ask to return to Q2 prices.',
    confidence: 72,
    recommendation: 'right',
    left: 'Accept new prices',
    right: 'Ask for Q2 prices',
    outcomes: {
      left: ['About 1,240 PLN more a month', 'No email to the supplier'],
      right: ['Email drafted to Mleczarnia Łąka', 'Could save about 1,240 PLN a month', 'Nothing leaves without your OK'],
    },
    protects: 1240,
    amount: 1240,
    resultLabel: 'Email drafted · waiting in Mail',
    followUps: ['scheduleMail'],
    mail: { to: 'Mleczarnia Łąka', initials: 'ML', subject: 'Dairy prices since October', body: ['Dear Sir or Madam,', 'Prices on your last 6 invoices went up by 11% without notice. Could we return to the Q2 price list from December?', 'Kind regards,\nJan Kowalski, Piekarnia Kowalski'] },
    next: { sub: 'Margin guard · Mleczarnia Łąka', chip: '−1,240 PLN/mo', tone: 'red' },
    back: {
      description:
        'Prices on the last 6 dairy invoices went up by 11% without notice. Two other dairies nearby sell at Q2 prices, so you have a good argument.',
      facts: [
        ['Price change since Q2', '+11%'],
        ['Extra cost a month', '1,240 PLN'],
        ['Invoices checked', '6'],
        ['Share of supplier costs', '19%'],
      ],
      weeks: [62, 54, 40, 28, 46, 58, 64, 66],
      weeksIfApproved: [62, 55, 41, 29, 47, 59, 65, 67],
      bufferLevel: 36,
      sources: 'KSeF purchase invoices (6) · price history',
      questions: ['Who else could supply dairy?', 'Write it more politely', 'Explain it more simply'],
    },
  },
];

// ---------- Analysis ----------
export const analysis = {
  kpis: [
    { icon: 'calendar', label: 'Next payroll', value: 'in 20 days', sub: '10 Dec · 96,200 PLN incl. Christmas overtime', highlight: true },
    { icon: 'wallet', label: 'Payroll this month', value: '78,400 PLN', sub: 'incl. ZUS 16,600 PLN' },
    { icon: 'users', label: 'Team', value: '14 people', sub: '2 on sick leave (L4) · 1 on holiday' },
    { icon: 'fileText', label: 'Invoices to pay', value: '9 · 58,540 PLN', sub: '2 overdue · 8,570 PLN' },
  ],
  // Q4 2026 (1 Oct – 31 Dec). Day = days since 1 Oct; today (20 Nov) is day 50, later weeks are the engine's forecast.
  q4: {
    label: 'Q4 2026 · Oct–Dec',
    start: new Date(2026, 9, 1),
    days: 91,
    today: 50,
    months: [
      { day: 0, label: 'Oct' },
      { day: 31, label: 'Nov' },
      { day: 61, label: 'Dec' },
    ],
    // Money in / out per week, PLN (the weeks include the payments listed in `events`).
    weeks: [
      { day: 0, revenue: 40200, expenses: 30400 },
      { day: 7, revenue: 41100, expenses: 89700 },
      { day: 14, revenue: 66600, expenses: 28500 },
      { day: 21, revenue: 43300, expenses: 13000 },
      { day: 28, revenue: 41800, expenses: 30600 },
      { day: 35, revenue: 40600, expenses: 91300 },
      { day: 42, revenue: 69000, expenses: 29300 },
      { day: 49, revenue: 43500, expenses: 34400 },
      { day: 56, revenue: 45200, expenses: 31400 },
      { day: 63, revenue: 88800, expenses: 14800 },
      { day: 70, revenue: 54600, expenses: 128400 },
      { day: 77, revenue: 87400, expenses: 16200 },
      { day: 84, revenue: 37500, expenses: 13500 },
    ],
    // Moments when larger amounts come in or go out (vertical markers on the chart).
    events: [
      { day: 0, kind: 'out', label: 'Rent', who: 'Zarządca Nieruchomości ABC', amount: 18000 },
      { day: 9, kind: 'out', label: 'Payroll', who: '14 people', amount: 76900 },
      { day: 14, kind: 'out', label: 'ZUS', who: 'Social insurance', amount: 16400 },
      { day: 19, kind: 'in', label: 'Catering invoice', who: 'Hotel Wawel', amount: 24600 },
      { day: 31, kind: 'out', label: 'Rent', who: 'Zarządca Nieruchomości ABC', amount: 18000 },
      { day: 40, kind: 'out', label: 'Payroll', who: '14 people', amount: 78400 },
      { day: 44, kind: 'in', label: 'Catering invoice', who: 'Hotel Wawel', amount: 26100 },
      { day: 45, kind: 'out', label: 'ZUS', who: 'Social insurance', amount: 16600 },
      { day: 55, kind: 'out', label: 'VAT', who: 'Tax office', amount: 21300 },
      { day: 61, kind: 'out', label: 'Rent', who: 'Zarządca Nieruchomości ABC', amount: 18000 },
      { day: 65, kind: 'in', label: 'Christmas pre-orders', who: 'Shop deposits', amount: 38000 },
      { day: 70, kind: 'out', label: 'Payroll + overtime', who: '14 people', amount: 96200 },
      { day: 75, kind: 'out', label: 'ZUS', who: 'Social insurance', amount: 16600 },
      { day: 80, kind: 'in', label: 'Catering invoice', who: 'Hotel Wawel', amount: 29000 },
    ],
  },
  breakdown: {
    period: 'Q4 so far · 1 Oct – 20 Nov',
    // `hex` for charts, `color` for bars; same order as the Figma palette.
    items: [
      { label: 'Payroll & ZUS', amount: 155300, color: 'bg-green-900', hex: '#23382B' },
      { label: 'Ingredients & suppliers', amount: 86900, color: 'bg-green-700', hex: '#3F5E4A' },
      { label: 'Rent', amount: 36000, color: 'bg-green-500', hex: '#6F8F78' },
      { label: 'Energy & gas', amount: 21800, color: 'bg-heat-4', hex: '#B8D3BE' },
      { label: 'Other', amount: 12000, color: 'bg-heat-3', hex: '#E2B45C' },
    ],
    insight: 'Flour and dairy are 61% of supplier costs. Dairy went up 11% in October.',
  },
  team: [
    { name: 'Anna Wiśniewska', role: 'Head baker', status: 'Working', tone: 'green', pay: '7,900 PLN' },
    { name: 'Piotr Zając', role: 'Baker', status: 'L4 since 12 Nov · paid 80%', tone: 'red', pay: '5,040 PLN' },
    { name: 'Marta Lis', role: 'Pastry chef', status: 'Working', tone: 'green', pay: '6,300 PLN' },
    { name: 'Kamil Nowicki', role: 'Driver', status: 'Holiday 24–28 Nov', tone: 'blue', pay: '4,900 PLN' },
    { name: 'Ewa Kowalczyk', role: 'Shop assistant', status: 'L4 since 18 Nov · paid 80%', tone: 'red', pay: '3,520 PLN' },
    { name: 'Tomasz Wójcik', role: 'Night baker', status: 'Working · +12 h overtime', tone: 'amber', pay: '6,860 PLN' },
    { name: 'Ola Mazur', role: 'Shop assistant', status: 'Working', tone: 'green', pay: '4,400 PLN' },
  ],
  teamMore: 7,
  teamTotal: '78,400 PLN',
  teamInsight: 'Sick leave lowers pay by 2,180 PLN this month, but the night shift needs 12 h of overtime to cover it.',
  meters: [
    { icon: 'wallet', label: 'Cash', value: '412,300 PLN', pct: 72, sub: 'in the bank today' },
    { icon: 'hourglass', label: 'Runway', value: '7.4 months', pct: 62, sub: 'at current costs' },
    { icon: 'users', label: 'Team', value: '82% morale', pct: 82, sub: 'overtime is rising', warn: true },
    { icon: 'shield', label: 'Trust', value: '74% partners', pct: 74, sub: 'you pay on time 91%' },
  ],
};

// ---------- Invoices ----------
export const invoices = [
  { id: 'i1', supplier: 'Mleczarnia Łąka', category: 'Dairy · Payables', amount: 6420, number: 'FV/2026/11/118', due: 'Due 17 Nov', group: 'overdue', urgency: 'Overdue 3 days', progress: 1, icon: 'milk', selected: true },
  { id: 'i2', supplier: 'Transport Wiśniewski', category: 'Delivery · Payables', amount: 2150, number: 'FV/77/11/2026', due: 'Due 18 Nov', group: 'overdue', urgency: 'Overdue 2 days', progress: 1, icon: 'truck', selected: true },
  { id: 'i3', supplier: 'Młyn Nowak', category: 'Flour · Payables', amount: 14800, number: 'FV/11/0412', due: 'Due 11 Dec · 14,208 PLN today', group: 'today', urgency: '4% off if paid today', progress: 0.95, icon: 'package', discount: true },
  { id: 'i4', supplier: 'Gaz-Serwis Kraków', category: 'Gas · Utilities', amount: 3870, number: 'FV/GS/4471', due: 'Due 23 Nov', group: 'week', urgency: 'Due in 3 days', progress: 0.8, icon: 'flame' },
  { id: 'i5', supplier: 'Opakowania Eko', category: 'Packaging · Payables', amount: 4260, number: '112/11/2026', due: 'Due 25 Nov', group: 'week', urgency: 'Due in 5 days', progress: 0.7, icon: 'package' },
  { id: 'i6', supplier: 'Serwis Pieców Kamiński', category: 'Oven service', amount: 1980, number: 'FV/11/2026/09', due: 'Due 27 Nov', group: 'week', urgency: 'Due in 7 days', progress: 0.6, icon: 'wrench' },
  { id: 'i7', supplier: 'Zarządca Nieruchomości ABC', category: 'Rent · Fixed cost', amount: 18000, number: 'FV/R/12/2026', due: 'Due 1 Dec', group: 'later', urgency: 'Due in 11 days', progress: 0.45, icon: 'building' },
  { id: 'i8', supplier: 'Biuro Rachunkowe Kos', category: 'Accounting', amount: 1230, number: 'FV/245/2026', due: 'Due 5 Dec', group: 'later', urgency: 'Due in 15 days', progress: 0.3, icon: 'calculator' },
  { id: 'i9', supplier: 'Słodka Hurtownia', category: 'Sugar & fillings · Payables', amount: 5830, number: 'FV/SH/0921', due: 'Due 9 Dec', group: 'later', urgency: 'Due in 19 days', progress: 0.15, icon: 'package' },
];

export const invoiceGroups = [
  { id: 'overdue', label: 'Overdue', tone: 'red', note: 'pay today' },
  { id: 'today', label: 'Today', tone: 'blue', note: 'discount ends at midnight' },
  { id: 'week', label: 'This week', tone: 'amber' },
  { id: 'later', label: 'Later', tone: 'green', note: 'after 1 Dec' },
];

export const paidThisMonth = { count: 31, amount: '112,400 PLN', note: 'all on time except 1' };

// ---------- Mail ----------
export const mails = [
  {
    id: 'm1', to: 'Zarządca Nieruchomości ABC', initials: 'ZN', time: '10:24', status: 'Replied',
    subject: 'Request to defer December rent by 14 days',
    snippet: 'Dear Sir or Madam, because of a seasonal gap…',
    card: 'Defer rent to 15 Dec', agent: 'Liquidity agent',
    body: [
      'Dear Sir or Madam,',
      'December is our busiest month, but card payouts for the Christmas season arrive only after the 14th. Could we pay the December rent of 18,000 PLN on 15 December instead of 1 December?',
      'We have paid every rent on time for the past 3 years and will confirm the transfer the same day.',
      'Kind regards,\nJan Kowalski, Piekarnia Kowalski',
    ],
    timeline: [['Drafted by AI', '10:12'], ['Approved by you', '10:14'], ['Sent', '10:24'], ['Opened', '11:02'], ['Replied', '13:40']],
    reply: { from: 'Zarządca Nieruchomości ABC', time: '13:40', text: 'We agree to move the December rent to 15 December. Please confirm the transfer on that day.' },
    effect: 'This moves 18,000 PLN past the 9 Dec low. Forecast updated: lowest balance is now 136,400 PLN, still under the buffer, so the overdraft card stays open.',
  },
  {
    id: 'm2', to: 'Młyn Nowak', initials: 'MN', time: '09:58', status: 'Needs OK',
    subject: 'Early payment of FV/11/0412 with 4% discount',
    snippet: 'We will pay today and deduct 592 PLN…',
    card: 'Pay Młyn Nowak early', agent: 'Payables agent',
    body: [
      'Dear Mr Nowak,',
      'We will pay invoice FV/11/0412 today, 21 days before the due date, and use the 4% early-payment discount from your terms. The transfer will be 14,208 PLN.',
      'Kind regards,\nJan Kowalski, Piekarnia Kowalski',
    ],
    timeline: [['Drafted by AI', '09:58']],
  },
  {
    id: 'm3', to: 'Hotel Pod Różą', initials: 'HR', time: '09:40', status: 'Needs OK',
    subject: 'Friendly reminder: FV/10/0388 is 14 days overdue',
    snippet: 'We kindly remind you about the open invoice…',
    card: 'Remind Hotel Pod Różą', agent: 'Collections agent',
    body: [
      'Dear Sir or Madam,',
      'We kindly remind you that invoice FV/10/0388 for 9,600 PLN was due on 6 November. Could you please pay it by 27 November?',
      'Thank you and kind regards,\nJan Kowalski, Piekarnia Kowalski',
    ],
    timeline: [['Drafted by AI', '09:40']],
  },
  {
    id: 'm4', to: 'Bank relationship manager', initials: 'BR', time: '16:00', status: 'Scheduled',
    subject: 'Request to raise the overdraft to 80,000 PLN',
    snippet: 'Could we discuss raising the limit for December…',
    card: 'Raise the overdraft for December', agent: 'Liquidity agent',
    body: [
      'Hello,',
      'Could we raise our overdraft limit to 80,000 PLN for 30 days from 1 December? Christmas card payouts arrive only after the 14th, while rent and payroll are due earlier.',
      'Kind regards,\nJan Kowalski, Piekarnia Kowalski',
    ],
    timeline: [['Drafted by AI', '09:20'], ['Approved by you', '09:31'], ['Scheduled', 'today 16:00']],
  },
  {
    id: 'm5', to: 'Anna Wiśniewska', initials: 'AW', time: 'Yesterday', status: 'Opened',
    subject: 'Approved: 2 overtime shifts for the Christmas rush',
    snippet: 'Thanks for planning ahead, the shifts are approved…',
    card: 'Approve Christmas overtime', agent: 'Payroll',
    body: [
      'Hi Anna,',
      'Thanks for planning ahead. The two extra night shifts on 18 and 19 December are approved and will be paid with the December payroll.',
      'Jan',
    ],
    timeline: [['Drafted by AI', 'Yesterday 15:02'], ['Approved by you', '15:05'], ['Sent', '15:05'], ['Opened', '17:44']],
  },
  {
    id: 'm6', to: 'Biuro Rachunkowe Kos', initials: 'BK', time: 'Yesterday', status: 'Sent',
    subject: 'November VAT: figures attached',
    snippet: 'Please file by the 25th, all invoices are in KSeF…',
    card: 'Send VAT figures', agent: 'Tax agent',
    body: [
      'Good afternoon,',
      'Please find the November VAT summary attached. All invoices are in KSeF. Could you file it by the 25th?',
      'Kind regards,\nJan Kowalski',
    ],
    timeline: [['Drafted by AI', 'Yesterday 11:10'], ['Approved by you', '11:12'], ['Sent', '11:12']],
  },
  {
    id: 'm7', to: 'Mleczarnia Łąka', initials: 'ML', time: 'Mon', status: 'Replied',
    subject: 'Question about the 11% price increase',
    snippet: 'Could we return to the Q2 prices for milk and butter…',
    card: 'Dairy prices up 11%', agent: 'Margin guard',
    body: [
      'Dear Sir or Madam,',
      'Prices for milk and butter on your last six invoices went up by 11%. Could we return to the Q2 prices? We have been ordering every week for four years.',
      'Kind regards,\nJan Kowalski, Piekarnia Kowalski',
    ],
    timeline: [['Drafted by AI', 'Mon 08:40'], ['Approved by you', '08:45'], ['Sent', '08:45'], ['Opened', '10:02'], ['Replied', '14:15']],
    reply: { from: 'Mleczarnia Łąka', time: 'Mon 14:15', text: 'We can offer Q2 prices for butter and 5% higher for milk from December.' },
    effect: 'This saves about 820 PLN a month compared with the new prices.',
  },
];


// ---------- Cash calendar (component kept, not shown anywhere yet) ----------
export const cashCalendar = {
  range: '16 Nov – 20 Dec',
  days: [
    ...Array.from({ length: 15 }, (_, i) => {
      const d = 16 + i;
      const level = d < 20 ? 0 : d <= 22 ? 5 : 4;
      return { day: d, month: 'Nov', level, today: d === 20 };
    }),
    ...[3, 3, 3, 3, 3, 3, 2, 2, 1, 1, 1, 1, 2, 4, 4, 4, 4, 5, 5, 5].map((level, i) => ({ day: i + 1, month: 'Dec', level })),
  ],
  hardestWeek: 'Hardest week: 7–13 Dec. Rent, payroll and ZUS before card payouts.',
};

// ---------- Rules (defaults; the Rules page edits them) ----------
export const defaultRules = {
  autopilot: true, // agent acts alone on small, safe actions
  autopilotLimit: 2000, // PLN: actions below this may run without a swipe
  extraConfirmAbove: 10000, // PLN: decisions above this need a longer hold to confirm
  keepBuffer: true, // block any action that takes cash under the safety buffer
  safetyBuffer: 150000,
  knownRecipientsOnly: true, // agent emails only counterparties known from invoices and transfers
  learnFromSwipes: true, // propose a rule after repeated identical swipes
};

// ---------- History seed (decisions made before this session) ----------
const daysAgo = (n, h = 10) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  d.setHours(h, 15, 0, 0);
  return d.toISOString();
};

export const pastDecisions = [
  {
    id: 'p-rent', cardId: 'p-rent', choice: 'approve', at: daysAgo(1, 10), past: true,
    card: { category: 'LIQUIDITY', icon: 'building', title: 'Ask to move December rent to the 15th?', proposal: 'Rent of 18,000 PLN leaves on 1 Dec, card payouts arrive after the 14th. Asking costs nothing.', left: 'Pay on the 1st', right: 'Ask to defer', confidence: 88, recommendation: 'right', resultLabel: 'Email sent · landlord agreed', agent: 'Liquidity' },
    ai: { model: 'qwen3-8b', answer: 'Your rent of 18,000 PLN falls in the same week as payroll, right before your lowest balance. Moving it to 15 December, after the card payouts, keeps you closer to your safety buffer at no cost.' },
    actions: ['Email sent to Zarządca Nieruchomości ABC'],
  },
  {
    id: 'p-oven', cardId: 'p-oven', choice: 'decline', at: daysAgo(4, 15), past: true,
    card: { category: 'CAPEX', icon: 'wrench', title: 'Lease a second oven for 1,450 PLN a month?', proposal: 'More Christmas capacity, but the lease starts before the 9 Dec low.', left: 'Not now', right: 'Lease the oven', confidence: 54, recommendation: 'left', resultLabel: 'Declined', agent: 'Investment' },
    ai: { model: 'qwen3-8b', answer: 'The lease would add 1,450 PLN a month just before your lowest balance in December. Waiting until January keeps the buffer safer; the extra capacity mostly matters for two weeks.' },
    actions: [],
  },
  {
    id: 'p-gas', cardId: 'p-gas', choice: 'approve', at: daysAgo(9, 9), past: true,
    card: { category: 'PAYABLES', icon: 'flame', title: 'Pay Gaz-Serwis on the due date?', proposal: 'Invoice FV/GS/4402 · 3,640 PLN. No discount for paying early.', left: 'Pay now', right: 'Pay on due date', confidence: 93, recommendation: 'right', resultLabel: 'Payment scheduled · SIMULATED', agent: 'Payables' },
    ai: { model: 'qwen3-8b', answer: 'There is no early-payment discount, so paying on the due date keeps 3,640 PLN in your account a little longer with no extra cost.' },
    actions: ['Bank transfer scheduled · SIMULATED'],
  },
];
