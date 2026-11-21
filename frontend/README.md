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
| `src/state/AppState.jsx` | Front-end state: card decisions, undo, alerts, invoices, mails, autopilot, toast. |
| `src/pages/` | Dashboard, Analysis, Invoices, Risk, Mail, ComingSoon (Ledger, Rules). |
| `src/components/dashboard/` | Alert stack + panel, forecast chart, decision deck and card (swipe, flip, hold-to-approve), cash calendar (kept, not shown). |
| `src/components/ui/` | Chip, Button, IconCircle, Segmented, Pill, Bar, Insight, PageHeader, Gauge, Icon. |
| `tailwind.config.js` | Colors, fonts and radii from the Figma tokens "RedCaps v2 · Green". |
| `src/index.css` | Text styles `.t-display-xl` … `.t-mono` matching Figma. |

The font is not final: change `fontFamily` in `tailwind.config.js` (and the Google Fonts link in `index.html`).

## Deck controls

Drag the card or use the keys: ← decline · → approve · ↑ ask why (flip) · ↓ later. Payments above the autopilot limit need press-and-hold on the approve button.
