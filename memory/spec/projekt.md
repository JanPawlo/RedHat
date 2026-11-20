# Project

## Challenge

Collabothon 2026 (Commerzbank), Red Hat challenge "Autonomous CFO": an AI-based CFO assistant for small and medium-sized companies. Details, requirements and scoring: `spec/wyzwanie.md`.

## Topic

A tool for companies based on invoices from KSeF (the Polish National e-Invoicing System): invoice verification, financial analysis and forecasts, with a chatbot in the interface.

## Sources

- Repo: https://github.com/JanPawlo/RedHat
- Brainstorming notes in Figma (Figma Spec): https://www.figma.com/spec/XcQ8glduBgAVS43S1A06o7/Notatki-z-brainstormingu
  - last sync to `decisions/pomysly.md`: 2026-11-20

## Tech stack

- Not settled yet (see `zadania.md`).
- Constraints from the challenge: the app must run on Red Hat OpenShift, and an open source / open weights model (e.g. Granite, Mistral, Qwen) on OpenShift AI. The organizers suggest a web app in TypeScript; Quarkus + LangChain4J gives a bonus point.
