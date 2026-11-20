# Recenzja pomysłu (zewnętrzna, 2026-11-20)

Recenzja naszej koncepcji „skrzynki decyzji” ze swipe'owaniem (zob. `decisions/pomysly.md`, pomysł 5). Zapisana prawie dosłownie, po angielsku. To opinia, a nie decyzja: co z niej bierzemy, wpisujemy do `decisions/decyzje.md`.

## Uwagi do recenzji (od nas)

- Recenzja ostrzega, że nie wiadomo, czy klaster ma GPU. Według challenge card (`spec/wyzwanie.md`) każdy zespół dostaje „GPU-backed instance” OpenShift AI. Mimo to warto sprawdzić to w dashboardzie albo zapytać na Discordzie.
- Recenzja zakłada dane z Polski (KSeF, PSD2, ZUS, biuro rachunkowe, kwoty w PLN), a dane przykładowe od organizatorów są niemieckie (`examples/dane-przykladowe.md`).
- Statystyki rynkowe (Mastercard, Every, cfo.ai, termin KSeF) pochodzą z recenzji; nie były przez nas weryfikowane.

---

## Review of the idea

**Verdict:** this is a real business need with a strong, memorable interface. The weak spot is the pitch. "An AI that replaces your CFO" overclaims, and you'll get pushed on it. **"Your CFO's decision inbox"** is more believable and easier to defend.

## What's strong

- **Demand is proven.** Big players moved into this space this year. Mastercard is debuting a "virtual CFO" built with AI because most small businesses can't afford a full-time finance chief. Every launched an AI CFO, AI Bookkeeper and AI CHRO for small firms, and cfo.ai launched an agent designed to act as a chief financial officer for startup founders and independent business owners.
  - That proves the problem is real, but it also means "an AI CFO" alone won't stand out. Your edge has to be the swipe interface plus the agent actually carrying out decisions.
- **The swipe interface fits how owners actually work.** Small-business owners don't want dashboards; they want to be told what needs a decision. Cutting finance down to a yes/no queue is new, easy to demo, and great for the Design and Innovation criteria.
- **The Reigns-style meters are more than decoration.** Each swipe can re-run the cash forecast and show its effect before you commit. That forecast logic is the real tech behind the gimmick, and it's what the jury should see.
- **Drafting emails turns advice into action.** Most competitors stop at insight. Yours closes the loop.

## Where you'll get challenged (and how to answer)

- **"Real finance decisions aren't binary."** Only make cards for decisions that genuinely are: early-payment discounts, approving a spend, chasing an overdue invoice, accepting a supplier price rise, a seasonal hire.
  - Use the other two swipe directions: **up = "ask why / make a counter-offer"**, **down = "postpone"**. The draft already shows this.
- **"Swiping makes big decisions feel trivial."** Add friction that grows with the amount: a quick swipe for small sums, press-and-hold for large ones, and a 10-minute undo window before any email goes out.
- **"Who's liable when the agent emails a partner?"** Limit who it can write to, make anything external a draft until approved, and keep a log of every action and the reason behind it. This is also where Red Hat's bonus points come in (see below).
- **"Where does the data come from?"** The hard part isn't the model, it's connecting the data. Poland gives you a strong story here:
  - KSeF, the national e-invoicing system, became mandatory for most other VAT-registered businesses by 1 April 2026. So every Polish SME's incoming and outgoing invoices now sit in one structured system the agent can read.
  - Bank data can come through open-banking access (PSD2).
  - For the hackathon, mock both but design them as real data feeds.
- **"Why not just use the accounting office (biuro rachunkowe)?"** They handle past compliance. You handle forward-looking cash decisions. Present yourselves as a complement to them, not a replacement.

## Ways to expand it (strongest first)

1. **Swipes become rules.** After five "take the discount" swipes, the agent asks: "Always take early-payment discounts above 2% if the safety buffer holds?" That's how the autopilot under 2,000 PLN earns trust. It's also the most original part of the idea, so put it in the pitch.
2. **Swipe up to negotiate.** The agent drafts a counter-offer, e.g. "can we do 30 days instead?"
3. **Chasing unpaid invoices.** Overdue-invoice cards trigger a sequence of reminders that gets firmer over time. This is cash recovered directly, so it's easy to show value.
4. **Tax and social-security (ZUS) deadline cards**, using data from KSeF.
5. **The bank as sales channel.** Commerzbank is judging this. An AI CFO inside the business banking app gives the bank daily engagement from small-business clients.
   - It also creates natural moments to offer an overdraft or credit line.
   - Flag the conflict of interest yourselves (the agent recommending the bank's own products); juries respect that.
6. **Several people:** the co-owner and the accountant each get the cards meant for them, plus an audit log.

## Red Hat challenge and judging strategy

**Required (no points without it):** run the app on your cluster, and serve a model there that the app actually calls.

**Pick 3 bonuses that fit the story:**
- **vLLM:** serve the model this way.
- **MCP tools via ogx:** expose the agent's tools as MCP: `read_invoices`, `get_balance`, `draft_email`, `send_email`.
- **NeMo Guardrails:** "the agent may never email unapproved recipients or commit to amounts over X." This is your answer to the liability question, so it scores twice.
- (Optional) **MLflow tracing:** use it as the "why did the agent do this?" audit trail.

**Demo idea:** run a test mail server (e.g. Mailpit) on the cluster and show it on screen. Swipe three cards and the emails land live in front of the jury. Then try a swipe that breaks a rule and show the guardrail blocking it. That 90 seconds covers business value, technical depth and the demo criterion together.

**Watch out:** 32 CPUs and 128 GB of RAM doesn't say whether there's a GPU. Ask on Discord early. If it's CPU-only, use a small model, such as one of IBM's small Granite models, and pre-generate the cards in the background rather than live during the demo.
