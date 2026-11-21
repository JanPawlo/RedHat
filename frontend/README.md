# RedCaps CFO · frontend

React 18 + Vite + Tailwind, built from the Figma file "RedCaps – AI CFO (Swipe Decisions) – Draft".

## Run

With Node 20 installed:

```bash
npm install
npm run dev
```

Without Node (Docker only), from this folder:

```bash
docker run --rm -it -p 3000:3000 -v "${PWD}:/app" -w /app node:20-alpine sh -c "npm install && npm run dev -- --host 0.0.0.0"
```

Open http://localhost:3000. API calls go to `/api/...` and are proxied to the backend on port 8000 (`vite.config.js`). Without the backend the app still works on demo data; the sidebar then shows "Model offline · demo data".

## Where things are

| Path | What |
| --- | --- |
| `src/data/mockData.js` | All demo numbers (Piekarnia Kowalski). Replace pieces with API calls later. |
| `src/state/AppState.jsx` | Front-end state: card decisions and History, Rules, undo, alerts, invoices, mails, toast. History, deck order and rules are kept in localStorage. |
| `src/state/agentStore.js` | AI answers for the cards: prefetched in the background at start (2 at a time) and cached in localStorage per card, so a refresh does not ask again. |
| `src/api/agentApi.js` | Calls the qwen3-8b model (`/vllm` proxy, then the backend `/api/v1/ai/explain`). |
| `src/components/confirmation/` | Confirmation screen after a decision; follow-up actions (schedule mail, calendar reminder) are registered in `followUps.js`. |
| `src/pages/` | Dashboard (one card), Analysis (with the forecast chart), Invoices, Risk, Mail, History, Rules, LiveData, Login. |
| `src/components/dashboard/` | Alert stack + panel, forecast chart, decision deck and card (swipe, flip, hold-to-approve), cash calendar (kept, not shown). |
| `src/components/ui/` | Chip, Button, IconCircle, Segmented, Pill, Bar, Insight, PageHeader, Gauge, Icon. |
| `tailwind.config.js` | Colors, fonts and radii from the Figma tokens "RedCaps v2 · Green". |
| `src/index.css` | Text styles `.t-display-xl` … `.t-mono` matching Figma. |

The font is not final: change `fontFamily` in `tailwind.config.js` (and the Google Fonts link in `index.html`).

## Card controls

- Tap the card (or the "I'd swipe right · 86% confident" chip) to flip it and see why.
- Press, drag left/right past the edge and keep holding: 0.6 s (1.2 s above the amount set in Rules), then release to decide. Released too early, the card goes back.
- The side buttons (round buttons under the card on phones) work the same way: press and hold.
- "Skip for now" moves the card to the end of the deck.
