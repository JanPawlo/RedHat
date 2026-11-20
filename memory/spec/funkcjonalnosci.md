# Features

Description of the app's features. Version from 2026-11-20, rewritten for the first UI sketch (swipe cards, forecast screen, outbox, audit log). The visuals will still change; this file describes **what** the app does, not exactly how it looks.

This is a **proposal, not a decision**. What goes into the MVP is recorded in `decisions/decyzje.md`.

## In short

The app is a financial assistant for the owner of a small or medium-sized company. It watches the company's money on its own, and when something needs a decision, it shows it as a **card**. The owner goes through the cards like in Tinder: **right = yes, left = no**. If they want to know more, they click **"Ask why"**: the card flips and shows where the proposal came from, and an AI chat opens next to it. The main screen shows the **cash forecast** for the coming weeks and how decisions change it.

The app should work **generically for different companies** (food service, services, transport…), not for one specific company.

## Glossary

| **Term** | **Meaning** |
| --- | --- |
| Card | One matter to decide, e.g. "Pay the invoice early and get a 4% discount?" |
| Deck | The queue of cards for today |
| Swipe | Dragging a card sideways with a finger or mouse; the buttons do the same |
| Engine | Plain code (no AI) that calculates the balance, the forecast and the effects of decisions |
| Agent | Part of the app that watches one area (liquidity, currencies, taxes…) and creates cards |
| Safety buffer | Minimum amount the balance should not drop below; set by the owner |
| Runway | How many months the cash will last at current costs |
| Outbox | Emails the AI wrote based on decisions |
| Autopilot | Amount threshold below which the agent may act on its own, without asking |
| Simulation | A "bank" action goes to a fake bank, not the real one |

## Overriding principle: the engine calculates, the AI explains

- Under the nice interface there must be an **"engine" that justifies decisions**.
- **Numbers** (balance, forecast, amounts, dates, effects of decisions) are calculated by deterministic code. The language model does not make them up.
- The **language model (LLM)** writes card content in plain language, answers in the chat, writes emails and picks tools (e.g. "recalculate the forecast if I pay in a week").
- Every number in the app has a **source**: specific transactions, an invoice, a rule or an explicit assumption.
- Check: if the LLM states an amount in the text that differs from the engine's, the response is rejected and generated again.

---

## Main features

### F1. Main screen: company status and cash forecast

The first thing the owner sees. Within 10 seconds they should know whether things are good or bad and how many decisions they have to make.

**Top bar**
- Logo and company name; company switcher (the app supports several profiles).
- Tabs: **Deck** (cards, with the number waiting), **Outbox**, **Ledger** (history and audit log), **Rules**.
- **Autopilot** toggle with an amount threshold (e.g. "Autopilot under 2,000").
- Badge **"OpenShift AI · vLLM · <model> active"**. It shows the jury that the model from the cluster is running (hard requirement), and turns red when the model does not respond.

**Indicators (bars in the style of the game Reigns)**
- 4 horizontal bars with an icon, name and value. In the sketch: Cash, Runway, Team, Trust (set to be decided, see "Open questions").
- When the user hovers over a choice on a card or starts dragging it, **a dot appears above the bars that this decision will change**, and the bar shows the new value. This way the effect is visible before the decision.

**Cash forecast chart**
- X axis: days from today (60 by default, toggle 30 / 60 / 90). Y axis: balance.
- **Baseline**: what happens if we do nothing.
- **Liquidity gap**: the point where the balance drops below zero or the buffer, marked in red with a label, e.g. "Liquidity gap −32,000 in 18 days".
- **Dashed line "after approved actions"**: forecast after decisions from cards, with a difference label (e.g. "After approved actions: +8,400").
- **Horizontal safety buffer line.**
- On hovering over a point: the balance on that day and the largest inflows and outflows on that day.
- **"Cash protected"** counter: the total that decisions from cards saved or protected.

**One-sentence summary**
- E.g. "All fine until December 10. After that, rent and salaries fall in the same week. 3 cards waiting, about 2 minutes." The LLM writes the sentence, and the engine provides the numbers.

### F2. Deck of decision cards (swipe like in Tinder)

The heart of the app. Instead of tables and reports, the owner gets a few concrete "yes / no" questions.

**Card structure**
- **Header:** avatar with the counterparty's initials (or the agent's icon), counterparty name, category (e.g. "Flour supplier · Payables").
- **Question in the title**, in plain language: "Pay invoice 21 days early to get a 4% discount?"
- **Description with numbers**, 1–2 sentences: which invoice, amount, due date, how much we gain and whether the balance stays above the buffer.
- **Agent hint:** "I'd swipe right · 86% confident". The agent says what it would do and how confident it is.
- **Two buttons with named effects**, not just "yes/no": "Pay on due date" (left), "Pay early, take 4%" (right).
- Badges: autonomy level ("Requires approval") and product source (e.g. "Commerzbank", if it is a bank product).

**Gestures and controls**

| **Move** | **Button** | **Effect** |
| --- | --- | --- |
| Right | Approve | Accepts the agent's proposal |
| Left | Decline | Rejects it, the card disappears |
| Up | Ask why | Flips the card and opens the chat (F3) |
| Down | Later | Postpones the card (tonight / tomorrow / in a week) |

- Every gesture has a **regular button** under the card (for people who don't like dragging, and on desktop) and a **keyboard shortcut** (arrow keys).
- Progress bar: "Card 3 of 7 · about 2 min left".
- **Undo last swipe:** undoes the last decision before the action goes out (e.g. 10 minutes for emails).
- **Friction for large amounts:** above the autopilot threshold a plain swipe is not enough; you have to hold the button or confirm.

**What happens after a swipe**
1. The decision is saved in the history (Ledger).
2. If needed, an action is created: an email draft in the Outbox or an order in the bank simulator.
3. The engine recalculates the forecast; the bars and chart animate.
4. The agent shows the next card.

**Where the "confidence" (86%) comes from**
- Not from the model's feelings, but from the engine: we calculate the forecast in several scenarios (pessimistic, base, optimistic, possibly more random draws).
- Confidence = in how many scenarios the recommendation is still good (e.g. the balance stays above the buffer). Easy to calculate and to explain.

**Card order:** urgent first (near due date), then largest impact on cash.

### F3. "Ask why": flipped card and chat

The answer to the challenge requirement: the owner must **understand** where the recommendation comes from and stay in control.

**Flipping the card**
- After "Ask why" (or a swipe up) the card rotates with an animation to its **back side**.
- On the back there is a **"What I looked at"** section, i.e. the data the agent based its decision on, with values:
  - bank balance, invoice amount and number, due date, early-payment discount,
  - lowest balance in the next 60 days, safety buffer.
- **Mini chart** of the weekly forecast (e.g. 8 bars = 8 weeks) with the buffer line and the week the decision concerns highlighted; toggle "now / if swiped right".
- **Sources** at the bottom: "Bank feed · e-invoices · payroll export"; clicking shows the specific transactions or invoice.
- The decision buttons are also available on the back, so you can decide without going back.
- A "Back" button flips the card back.

**Card chat**
- Opens together with the flip (on a phone below the card, on a computer next to it).
- Knows the card's context, so nothing has to be typed from scratch.
- **Question suggestions** (clickable "chips"): "What if I pay in a week?", "How much does it cost?", "What are the other options?", "Explain it more simply".
- "What if" questions run the engine; the mini chart on the card updates live.
- The agent can propose a **modified decision** (e.g. "pay half now"); the card then gets a new variant to swipe.
- For bank products, the agent says plainly that it is recommending a Commerzbank product and shows an alternative (honesty towards the user).

**General chat** (outside the cards)
- Available from the main screen. Questions like: "Can I afford 2 new employees?", "When will the hardest week be?", "How much can I safely spend on new equipment?".
- Answers are based on data from tools (`get_balance`, `get_forecast`, `list_invoices`, `simulate`…), not on the model's "knowledge".
- A chart may appear in the answer (forecast before / after, costs by category).
- A conversation can produce a new card or a known event (e.g. "we close for 2 weeks in July"), which the engine takes into account in the forecast.

### F4. Financial forecasts

The engine everything else rests on.

**Based on what**
- Account history (bank statement).
- Invoices: unpaid cost invoices (what we have to pay) and sales invoices (what should come in, adjusted for how late a given customer usually pays).
- Recurring payments detected in the history: rent, salaries, taxes, social contributions, loan installments, subscriptions.
- Known future events entered by the owner or via the chat (closing the premises, hiring, buying equipment).
- Company profile: industry, number of employees, seasonality, buffer.

**How we calculate (simple but honest)**
- Revenue: average by day of week and month (seasonality) over recent months.
- Fixed costs: from the recurring-payments calendar. Variable costs: as a % of revenue.
- Invoices: on the due date (or with the delay typical for a given customer).
- 3 scenarios (pessimistic / base / optimistic) from historical deviations; they give a band on the chart and the "confidence" on cards.
- Horizon: 60 days by default in the view, we calculate up to 90 days. For SMEs, forecasts of about 3 months are the most practical.

**Indicators from the engine**
- Lowest balance in the horizon and its date; days until the liquidity gap.
- Runway in months.
- Free cash = balance − buffer − liabilities in the horizon.

**"What if" simulation**
- A single function `simulate(zmiany)`, used by the cards (effect preview), the chat and the post-decision chart.

### F5. Outbox: emails from decisions

- A decision may require an email: to a supplier (early payment, request to move a due date), a customer (invoice reminder), the accountant, the bank advisor.
- **The AI writes the email** based on the card and the decision; the user can read and edit it.
- Each email has a status: **NEEDS OK** (waiting for approval), **SCHEDULED** (will go out at a given time), **SENT**.
- A **"Review all"** button to approve several emails at once.
- At the hackathon, emails go to a **test mailbox on the cluster** (e.g. Mailpit), so they can be seen live in the demo.
- The agent only writes to counterparties we already know from invoices and transfers (recipient list).

### F6. Control: autonomy levels, rules and audit log

The challenge requires distinguishing **what the agent does on its own, what it recommends, what requires approval and what is only simulated**. This feature shows that.

**Autonomy levels** (toggle in settings or in the header)

| **Mode** | **What the agent does** |
| --- | --- |
| Copilot | Only analyzes and recommends; every action requires approval |
| 1-Click Approve | Prepares the action in full; one swipe or click is enough |
| Auto (max X) | Executes actions below the amount threshold on its own; above it, asks |

**Classification of each action**
- **Analysis** (always on its own): reading data, forecasting, detecting problems.
- **Recommendation**: a card with a proposal.
- **Requires approval**: anything that goes outside (email, bank order) or exceeds the threshold.
- **Execution: simulated / allowed**: at the hackathon, bank actions are always simulated and marked with a **SIMULATED** badge.

**Rules (Rules tab)**
- Hard rules checked in code (policy-as-code), e.g.:
  - human approval above X,
  - emails only to known recipients,
  - the balance after an action must not drop below the buffer,
  - numbers only from the engine.
- **Swipes turn into rules:** when the owner makes the same decision several times, the agent proposes a rule ("Always take early-payment discounts above 2% if the buffer holds?"). A rule can be turned off.

**Audit log (Ledger tab)**
- A list of all actions: time, rule ID (e.g. `RULE-LIQ-01`), description, status:
  - **SIMULATED**: action executed in the simulator,
  - **PENDING**: waiting for approval,
  - **BLOCKED BY POLICY**: the agent wanted to do something, but a rule blocked it (e.g. "Auto-execution 35k exceeds 2,000 limit").
- Entries cannot be edited. Clicking an entry shows the full "why".

**Bank simulator**
- Fake Commerzbank API: credit line, limit change, deposit, currency hedge, transfer.
- Responds "accepted (simulation)" with a reference number; preview of what would go to the real bank.

### F7. Free cash and investments (Investment agent)

One of the 4 use cases from the challenge. Liquidity makes sure the money **doesn't run out**, and Investment makes sure the surplus **doesn't sit idle**. The agent looks for cash the company will certainly not need for some time and proposes a safe place where it can earn during that time.

**How the agent calculates free cash**

The key question is not "how much do I have in the account", but **"how much can I lock up and for how long"**:
1. The engine takes the forecast in the **pessimistic scenario** (F4).
2. For each possible period (1, 3, 6, 12 months) it finds the **lowest balance** in that period.
3. Free amount for a given period = that lowest balance − safety buffer − tax reserve from the Tax agent.
4. It rounds the result down and skips amounts too small to be worth it (threshold e.g. 5,000).

Example: balance today 60,000, buffer 30,000. In the next 3 months the lowest balance in the worse scenario is 52,000, but in June (seasonal dip) it drops to 35,000. The agent proposes **20,000 for 3 months** (52,000 − 30,000, rounded down), so the money comes back before June, rather than e.g. 30,000 for a year.

**Products it compares** (simulated Commerzbank products, example rates from a configuration file)

| **Product** | **Access to money** | **Return** | **When it fits** |
| --- | --- | --- | --- |
| Savings account | Immediate | Lowest, variable | Surplus that may be needed at any moment |
| Term deposit 1 / 3 / 6 / 12 months | Locked until the end of the term (breaking it = losing the interest) | Fixed, known in advance | We know for sure the money will not be needed for the whole period |
| Money market fund | About 1–2 business days | Variable, not guaranteed, usually between account and deposit | Larger amount, uncertain timing |
| Purchase financing (capex) | Not applicable | Interest cost instead of return | Planned equipment purchase: pay cash or take a loan / lease |

The agent recommends **only safe cash products**: no stocks, corporate bonds or cryptocurrencies. It does not replace an investment advisor.

**How it picks the proposal**
- **Term matched to the forecast:** the money comes back before a known dip or a large payment (tax, bonuses, season).
- **Deposit ladder** (optional): for a larger amount it splits it into parts with different terms, e.g. 10,000 for 1 month and 10,000 for 3 months, so part of the money comes back sooner.
- **Part always liquid:** it does not propose placing 100% of the free amount.
- **Comparison with "doing nothing":** return stated in money, not just in percent (e.g. "about 150 over 3 months").

**Card**
- Title: "You have 20,000 of free cash until March. Put it in a 3-month deposit?"
- Description: return of about X, the money comes back on March 15, i.e. 2 weeks before the seasonal drop; the balance stays above the buffer even in the worse scenario.
- Buttons: "Leave in the account" (left), "Open a 20,000 deposit" (right).
- Bars: Cash drops by 20,000 (less money on hand), but the app shows the deposited amount separately so it does not look like a loss.
- "Commerzbank" badge and a note that it is a bank product.

**Back of the card ("Ask why")**
- "What I looked at": balance, buffer, liabilities until the end of the period, lowest balance in the worse scenario, calculated free amount.
- **Product comparison** in a small table: account / deposit / fund, i.e. return, availability, risk.
- **Forecast chart with the lock-up period shaded** and the day the money comes back marked.
- Chat question suggestions: "What if I put away 30,000?", "What if I need the money earlier?", "How is a fund different from a deposit?", "How much will I earn over 6 months?".
- Changing the amount or term in the chat recalculates the chart and creates a new card variant.

**Equipment purchases (capex)**
- When the owner enters a planned purchase (e.g. in the chat: "in April I want to buy an oven for 10,000"), the agent creates a card with a comparison:
  - paying cash: how much the balance drops and whether the buffer holds,
  - loan / lease: monthly installment and total interest cost.
- The recommendation depends on the forecast, e.g. "cash, but only after the 15th, when receivables come in".

**After the decision**
- The bank simulator "opens" the deposit (SIMULATED in the Ledger).
- Forecast: outflow of the amount today, inflow of the amount + interest on the end date.
- 7 days before the deposit ends, the agent creates a card: "The deposit ends on March 15. Renew it or leave the money in the account?", with a new forecast.

**Safeguards**
- Never deposits money below the buffer or the tax reserve.
- The coordinator gives priority to Liquidity and Tax: safety first, then return.
- Depositing always **requires approval** (also in Auto mode) and at the hackathon is **simulated**.
- On the card and in the chat: "This is not investment advice", and for Commerzbank products an honest note that it is a bank product, with the alternative "leave in the account".

**Scope**
- Minimum (if this were the second full use case): free cash + 1 / 3 / 6-month deposits + card + back with chart.
- Later: money market fund, deposit ladder, renewal card, capex.

---

## Agents: where cards come from

The challenge requires at least one full use case (data → explainable recommendation → user decision). We propose **Liquidity** as the main one, and the rest as additional sources of cards.

| **Agent** | **What it watches** | **Example card** | **Prio** |
| --- | --- | --- | --- |
| Liquidity (from the challenge) | Gaps in the forecast, buffer, due dates of large payments | "In 18 days you will be 32,000 short for salaries. Open a short credit line of 35,000 (cost about 420)?" | P1 |
| Payables: discounts and due dates | Cost invoices, early-payment discounts | "Pay 21 days early and get a 4% discount?" | P1 |
| Collections | Overdue sales invoices | "Customer X is 14 days late. Send a polite reminder?" | P2 |
| Margin guard | Silent price increases from suppliers | "The supplier raised prices by 11%. Write to ask for a return to Q2 rates?" | P2 |
| FX hedging (from the challenge) | Payments and invoices in a foreign currency | "Hedge the exchange rate for the next 6 payments in CHF?" | P2 |
| Tax (from the challenge) | Tax and advance payment deadlines | "Tax advance payment due in 10 days. Set the amount aside now?" | P2 |
| Investment (from the challenge, described in F7) | Free cash above the buffer, deposits, equipment purchases | "You have 20,000 of free cash until March. 3-month deposit?" | P2 (P1 if it is the second full use case) |
| Invoices / KSeF | Consistency and suspicious invoices | "The supplier changed its account number. Check before paying?" | P3 |

When agents contradict each other (e.g. Investment wants to deposit money that Liquidity needs in a month), the **coordinator** decides and shows only one consistent card.

## Input data

- **Bank statement:** CSV import (various bank formats), eventually open banking (PSD2).
- **E-invoices:** eventually KSeF (PL) / XRechnung (DE); at the hackathon, sample files in the same shape.
- **Payroll:** export from the HR system (amounts and dates).
- **Company profile:** short onboarding (industry, headcount, seasonality, buffer).
- **Multiple companies:** data from the organizers (Pizzeria Amalfi, `examples/dane-przykladowe.md`) + generated data for the profiles in `firmy/`.
- At the hackathon we may make assumptions about data access, but in the app we show them explicitly.

## Platform (hard requirements, P0)

| **Requirement** | **How** |
| --- | --- |
| Backend on OpenShift | `oc new-app` + Route with HTTPS; frontend on the cluster too |
| Open-weights model on RHOAI | vLLM (free bonus); favorite `qwen3-8b` (details in `spec/openshift-ai.md`) |
| The app really calls the model | OpenAI-compatible endpoint, address and token from a Secret, not from the repo |
| Visible proof | Model status badge in the header + call logs |

---

## Easy extras (proposals)

Things that add a lot to the impression and are not hard. Difficulty: **E** = a few hours or less, **M** = about a day.

| **Idea** | **Why** | **Difficulty** |
| --- | --- | --- |
| "All done" screen after the last card | Summary: how many decisions, how much cash protected, what went out in the Outbox. Gives a sense of "fun" and closure | E |
| "Cash protected" counter | One number showing the app's value; the jury gets it right away | E |
| Model status badge | Shows the hard requirement is met without explaining | E |
| Keyboard shortcuts (arrow keys) | Quick demo on a laptop | E |
| "Later" with a choice of time | Tonight / tomorrow / in a week instead of just "later" | E |
| Reason for "Decline" (3 chips) | "Too expensive / bad timing / I'll handle it myself"; the agent learns what to propose | E |
| Question suggestions in the chat | The user doesn't need to know what to ask | E |
| Bank order preview | For a SIMULATED action, a "see what would go to the bank" button | E |
| Simple mode / large font | "Innovations for all generations" | E |
| Light and dark theme | We already have both directions in the sketches | E |
| Mini calendar of the next 7 days | List: what comes in and what goes out this week | E |
| "Today's date" slider (demo mode) | Moving through time in the presentation: the agent sees only the past, and we show that the forecast came true | M |
| PL / EN language switch | Demo in English, user in Polish | M |
| Summary export for the accountant | PDF or email with the week's decisions | M |
| Rule proposal after repeated swipes | The most original element of the idea | M |

## Priorities (MVP proposal)

| **Prio** | **What** |
| --- | --- |
| P0 | App on OpenShift + model on RHOAI via vLLM, which the app really calls |
| P1 | Forecast engine (F4), main screen with chart (F1), card deck with swipe (F2), "Ask why" with flip and chat (F3), Liquidity + Payables agents, bank simulator, simple audit log |
| P2 | Outbox with test mailbox (F5), autonomy levels and rules (F6), Investment agent (F7), further agents, easy extras, selected bonuses |
| P3 | Invoices / KSeF agent, real connectors (PSD2, KSeF API), multiple people in one company (co-owner, accountant) |

## Bonuses that fit the features

The organizers recommend 2–4. Technical details in `spec/openshift-ai.md`.

| **Bonus** | **Pts** | **Where in our app** |
| --- | --- | --- |
| vLLM | 1 | Model serving (needed anyway) |
| Jupyter on RHOAI | 1 | Analysis of sample data and forecast tuning |
| NeMo Guardrails | 2 | Second layer of the rules from F6 (the first is code) + "BLOCKED BY POLICY" demo |
| ogx + MCP | 1 | Agent tools as MCP: `get_balance`, `get_forecast`, `simulate`, `draft_email`, `submit_to_bank` |
| MLflow | 1 | Trace of every agent decision as an extended audit log |

## Demo scenario (draft)

1. Main screen: the chart shows a liquidity gap in a couple of weeks; "3 cards, about 2 minutes".
2. Liquidity card: short credit line. "Ask why" → the card flips → data, mini chart, chat: "what if I postpone the payment to the supplier?".
3. Swipe right → SIMULATED in the Ledger → chart: dashed line above zero, the "Cash protected" counter goes up.
4. Early-payment discount card → swipe → email in the Outbox → appears in the test mailbox.
5. Attempt at an action above the autopilot limit → "BLOCKED BY POLICY".
6. "All done" screen.

The demo needs to be rehearsed, because a good presentation is as important as a working app.

## Open questions

- **Bars at the top:** keep Cash, Runway, Team (morale), Trust (partners) or replace them with purely financial ones?
  - Option A, keep them: Team and Trust calculated with a simple heuristic, e.g. Team from overtime and on-time salaries, Trust from on-time payments to suppliers. More "game-like" and fun, but harder to defend.
  - Option B, financial: e.g. Cash, Runway, Liabilities, Risk. All from data, easier to explain.
  - To be decided in the team.
- Chart horizon: 60 days (as in the sketch) or 90 days (closer to the advice about 3-month forecasts)? Proposal: a toggle.
- Currency and market in the demo: the app is generic, but the sample data has to be shown in some currency (EUR in the organizers' data, PLN in the sketch).
- What rates for Commerzbank products should we assume in the simulator (credit line, deposit, forward)? Ask on #Commerzbank.
- Should Investment (F7) be the second full use case next to Liquidity?
- Backend: TypeScript (organizers' suggestion), Python (easier for forecasts) or Quarkus (bonus)?
