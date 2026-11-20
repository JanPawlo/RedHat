# Ideas

Source: brainstorming notes in Figma (see `spec/projekt.md`).

## 1. KSeF: invoice verification, catching fraud

KSeF = Poland's national e-invoicing system.

Open questions:
- What are example frauds we are trying to stop?
- How do we stop them?
- How does the user use this service?
- How do we integrate this solution with KSeF?

## 2. Invoice consistency detection

- No details, to be worked out. Probably closely related to idea 1.

## 3. Chatbot as part of the interface

- Visualizations (line charts, bar charts, etc.)
- General advice, e.g. "Does it make sense to hire 2 additional employees?"

## 4. Financial forecasts

Based on:
- invoices from KSeF,
- company structure: number of employees, positions, listed / private company,
- account balance (monthly?).

The list of inputs in Figma ends with an empty bullet, so it may be incomplete.

## 5. CFO decision inbox with swiping

Description from the review (`decisions/recenzja-pomyslu.md`) and from our brainstorming notes (2026-11-20). In the notes the working name is "Reigns: CFO support" or "Tinder for entrepreneurs".
- Problems are shown as cards. The user decides by dragging a card right or left.
- Company data is shown as vertical bars (like in the game Reigns).
- Forecasts update after each decision.
- Autonomous, proactive agent actions: it creates problem cards itself; it generates and sends emails semi-autonomously, based on swipes.
- The agent turns finances into decision cards. Swipe right or left is yes/no; up asks "why" or makes a counter-offer; down postpones.
- Card-game-style meters show how a decision will change the cash forecast before we confirm it.
- The agent prepares emails itself (e.g. to suppliers) and sends them after approval.
