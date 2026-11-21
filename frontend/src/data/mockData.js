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
    action: 'See risk', to: '/risk',
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
    protects: 31600,
    amount: 80000,
    resultLabel: 'Overdraft request sent to the bank · SIMULATED',
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
    protects: 592,
    amount: 14208,
    resultLabel: 'Early payment scheduled · SIMULATED',
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
    protects: 9600,
    amount: 9600,
    resultLabel: 'Reminder drafted · waiting in Mail',
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
    protects: 1240,
    amount: 1240,
    resultLabel: 'Email drafted · waiting in Mail',
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
  months: [
    { month: 'Jun', revenue: 168000, expenses: 142000 },
    { month: 'Jul', revenue: 174000, expenses: 150000 },
    { month: 'Aug', revenue: 161000, expenses: 149000 },
    { month: 'Sep', revenue: 182000, expenses: 151000 },
    { month: 'Oct', revenue: 190000, expenses: 158000 },
    { month: 'Nov', revenue: 176000, expenses: 154000, partial: true },
  ],
  totals: [
    { label: 'Revenue · 6 mo', value: '1,051,000 PLN', chip: '+6% vs last half', tone: 'green' },
    { label: 'Expenses · 6 mo', value: '904,000 PLN', chip: '+4%', tone: 'amber' },
    { label: 'Profit · 6 mo', value: '147,000 PLN', chip: '14% margin', tone: 'green', positive: true },
  ],
  breakdown: {
    total: '154,000 PLN',
    items: [
      { label: 'Payroll & ZUS', amount: '78,400', pct: 51, color: 'bg-green-900' },
      { label: 'Ingredients & suppliers', amount: '42,600', pct: 28, color: 'bg-green-700' },
      { label: 'Rent', amount: '18,000', pct: 12, color: 'bg-green-500' },
      { label: 'Energy & gas', amount: '9,800', pct: 6, color: 'bg-heat-4' },
      { label: 'Other', amount: '5,200', pct: 3, color: 'bg-heat-3' },
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
  invoiceGauge: {
    paidPct: 78,
    paidCount: 31,
    totalCount: 40,
    rows: [
      { label: 'Paid · 31', amount: '112,400 PLN', color: 'bg-green-700' },
      { label: 'To pay · 9', amount: '58,540 PLN', color: 'bg-heat-3' },
      { label: 'Overdue · 2', amount: '8,570 PLN', color: 'bg-status-red' },
    ],
  },
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

// ---------- Risk ----------
export const risk = {
  score: 34,
  label: 'Low · watch December',
  factors: [
    { label: 'Liquidity', note: 'December dips under the buffer', level: 'Medium' },
    { label: 'Supplier dependency', note: 'Młyn Nowak = 41% of purchases', level: 'Medium' },
    { label: 'Customer concentration', note: 'Top client = 18% of revenue', level: 'Low' },
    { label: 'Taxes & ZUS', note: 'All paid on time this year', level: 'Low' },
    { label: 'Currency (FX)', note: 'No foreign invoices', level: 'Low' },
  ],
  lender: {
    rating: 'Good',
    metrics: [
      { label: 'Revenue stability', value: '±6%', note: 'month to month, card payouts', tone: 'green' },
      { label: 'Debt service', value: '0.4×', note: 'no loans, one leasing', tone: 'green' },
      { label: 'Payment discipline', value: '91% on time', note: '2 invoices overdue now', tone: 'amber' },
      { label: 'Runway', value: '7.4 months', note: 'at current costs', tone: 'green' },
    ],
    insight: 'These numbers support the 80,000 PLN overdraft on your decision card. It is a Commerzbank product, so compare it with simply delaying the rent.',
  },
  counterparties: [
    { name: 'Hotel Pod Różą', role: 'Client', score: 'High', google: ['★ 3.1 · 212', 'amber'], krz: ['Listed since Oct', 'red'], payments: ['Pays 14 days late', 'red'], statements: ['2025 not filed', 'amber'], account: ['Unchanged', 'green'], watch: true },
    { name: 'Mleczarnia Łąka', role: 'Supplier', score: 'Medium', google: ['★ 4.2 · 88', 'green'], krz: ['Not listed', 'green'], payments: ['We are 3 days late', 'amber'], statements: ['2025 filed', 'green'], account: ['Changed 3 days ago', 'red'], watch: true },
    { name: 'Kawiarnia Złoty Róg', role: 'Client', score: 'Medium', google: ['★ 4.4 · 530', 'green'], krz: ['Not listed', 'green'], payments: ['Pays 6 days late', 'amber'], statements: ['2025 filed', 'green'], account: ['On VAT whitelist', 'green'] },
    { name: 'Młyn Nowak', role: 'Supplier', score: 'Low', google: ['★ 4.7 · 41', 'green'], krz: ['Not listed', 'green'], payments: ['Always on time', 'green'], statements: ['2025 filed', 'green'], account: ['On VAT whitelist', 'green'] },
    { name: 'Transport Wiśniewski', role: 'Supplier', score: 'Low', google: ['★ 4.5 · 63', 'green'], krz: ['Not listed', 'green'], payments: ['On time', 'green'], statements: ['2025 filed', 'green'], account: ['On VAT whitelist', 'green'] },
    { name: 'Delikatesy Pod Lipami', role: 'Client', score: 'Low', google: ['★ 4.6 · 190', 'green'], krz: ['Not listed', 'green'], payments: ['Pays 1 day late', 'green'], statements: ['2025 filed', 'green'], account: ['On VAT whitelist', 'green'] },
  ],
  counts: { all: 24, clients: 9, suppliers: 15, watchlist: 2 },
  watchlist: [
    { icon: 'building', title: 'Hotel Pod Różą is in the debtor registry and pays 14 days late', note: 'Ask for 50% prepayment on the next catering order (9,600 PLN open now).', tone: 'red' },
    { icon: 'landmark', title: 'Mleczarnia Łąka changed its bank account 3 days ago', note: 'Classic invoice fraud pattern. Confirm the new account by phone before paying 6,420 PLN.', tone: 'amber' },
  ],
  sources: [
    { icon: 'star', label: 'Google reviews', note: 'Rating and trend of the last 90 days' },
    { icon: 'ban', label: 'KRZ', note: 'Krajowy Rejestr Zadłużonych (debtor registry)' },
    { icon: 'fileText', label: 'Your history', note: 'Bank feed + KSeF invoices: who pays late' },
    { icon: 'file', label: 'eKRS statements', note: 'Was the last annual report filed?' },
    { icon: 'landmark', label: 'VAT whitelist', note: 'Is the bank account on the official list?' },
  ],
};

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
