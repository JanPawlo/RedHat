// Rules page: what the agent may do, the limits it works with and when it warns the owner.
// Every rule has an ID that History and the audit log can quote (e.g. "Blocked by RULE-LIQ-01").

// ---------- What the agent may do on its own ----------
// The agent never sends money. It can send messages, and it can prepare a transfer that you
// approve in your bank (strong customer authentication); at the hackathon the bank is simulated.

// Automation / Autonomy levels
export const AUTO_MANUAL = 'approval';
export const AUTO_AUTOMATED = 'automated';
export const AUTOMATION_LEVELS = [
  { value: AUTO_MANUAL, label: 'Manual approval' },
  { value: AUTO_AUTOMATED, label: 'Automated' },
];

// Messages (the agent really can do these alone).
export const MSG_ASK = 'ask';
export const MSG_SEND = 'send';
export const MSG_NEVER = 'never';
export const MESSAGE_MODES = [
  { value: MSG_ASK, label: 'Ask me' },
  { value: MSG_SEND, label: 'Send it, tell me' },
  { value: MSG_NEVER, label: 'Never' },
];
export const MESSAGE_ACTIONS = [
  { id: 'reminder', ruleId: 'RULE-MSG-01', title: 'Remind a customer about a late invoice', text: 'A polite email to a customer who has not paid on time.' },
  { id: 'supplierMail', ruleId: 'RULE-MSG-02', title: 'Write to a supplier', text: 'Ask for a later due date or the old prices.' },
];

// Payments (the agent only prepares them; you send them from your bank).
export const PAY_PREPARE = 'prepare';
export const PAY_TELL = 'tell';
export const PAY_NEVER = 'never';
export const PAYMENT_MODES = [
  { value: PAY_PREPARE, label: 'Prepare transfer' },
  { value: PAY_TELL, label: 'Only tell me' },
  { value: PAY_NEVER, label: 'Never' },
];
// `locked`: fixed at the hackathon, shown as a chip instead of the choice.
export const PAYMENT_ACTIONS = [
  { id: 'invoicePay', ruleId: 'RULE-PAY-10', title: 'Pay invoices on time', text: 'A few days before the due date the transfer is ready in Invoices; you approve it in your bank.' },
  { id: 'earlyPay', ruleId: 'RULE-PAY-11', title: 'Pay early to take a discount', text: 'Only when the supplier gives a discount and the balance stays above your buffer.' },
  { id: 'bankProduct', ruleId: 'RULE-PAY-12', title: 'Bank products', text: 'Credit line, deposit, currency hedge. A card explains the offer; you decide.', locked: 'Card only · simulated bank' },
];

// ---------- Always on (checked in code, cannot be switched off) ----------
export const SAFETY_RULES = [
  { ruleId: 'RULE-PAY-00', title: 'The agent never sends money', text: 'It can only prepare a transfer. You approve every payment in your bank.' },
  { ruleId: 'RULE-LIQ-01', title: 'Never under the safety buffer', text: 'A payment that would take the balance under your buffer is not prepared.' },
  { ruleId: 'RULE-PAY-01', title: 'New bank account = stop', text: 'If a supplier’s account number changed, no transfer is prepared until you check it.' },
  { ruleId: 'RULE-PAY-02', title: 'No double payments', text: 'No transfer for an invoice that looks like one already paid.' },
  { ruleId: 'RULE-MAIL-01', title: 'Email only known companies', text: 'The agent writes only to companies from your invoices and bank transfers.' },
  { ruleId: 'RULE-BANK-01', title: 'Bank actions are simulated', text: 'Nothing reaches a real bank; every bank action is marked SIMULATED.' },
  { ruleId: 'RULE-AI-01', title: 'Numbers come from the engine', text: 'If the AI writes an amount the engine did not calculate, the answer is thrown away.' },
];

// ---------- When to warn the owner (bell) ----------
export const ALERT_RULES = [
  { key: 'alertBufferDays', ruleId: 'RULE-ALERT-01', title: 'Balance will drop under the buffer', unit: 'days ahead', min: 7, max: 60, step: 7 },
  { key: 'alertPriceRisePct', ruleId: 'RULE-ALERT-02', title: 'A supplier raised prices by more than', unit: '%', min: 2, max: 30, step: 1 },
  { key: 'alertLateDays', ruleId: 'RULE-ALERT-03', title: 'A customer is late by more than', unit: 'days', min: 3, max: 60, step: 1 },
];

// ---------- Limits (PLN) ----------
export const LIMITS = {
  buffer: { min: 20000, max: 300000, step: 10000 },
  bigAmount: { min: 1000, max: 100000, step: 1000 },
};

// Upcoming payments kept aside as the tax reserve (labels of payments in the forecast), and how far ahead.
export const TAX_LABELS = ['VAT', 'ZUS', 'PIT', 'CIT'];
export const TAX_RESERVE_DAYS = 30;
// Payments that make up one month of fixed costs (for the "buffer ≈ x months" hint).
export const FIXED_COST_LABELS = ['Rent', 'Payroll', 'ZUS'];
