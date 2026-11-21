# Project memory

This folder is the shared project memory for people and for every AI assistant (Claude, Gemini, ChatGPT, Copilot, Codex).
The assistant reads these files before working and adds what it has learned to them.

## Structure

| **Folder** | **What goes here** |
| --- | --- |
| `spec/` | The essentials: what the project is, organizer requirements, feature description, our environment. Look here for "what we are building and on what". |
| `decisions/` | Decisions, brainstorming ideas, reviews and tips. Look here for "what we agreed on and why". |
| `examples/` | Example companies and test data. Context for the demo and data, not requirements. |
| `reference/` | Original files from the organizers (PDFs, sample CSV data). Read-only: never edit them, write conclusions into the other folders. |
| `zadania.md` | Current task list (stays in the main folder because it is opened most often). |

## Files

| **File** | **What it contains** |
| --- | --- |
| [spec/projekt.md](spec/projekt.md) | Project description, challenge, sources and links |
| [spec/wyzwanie.md](spec/wyzwanie.md) | Summary of the organizers' materials: goal, 4 use cases, hard requirements, scoring, environment, submission form |
| [spec/funkcjonalnosci.md](spec/funkcjonalnosci.md) | Feature description for the UI sketch: forecast screen, swipe cards, "Ask why" with chat, outbox, autonomy and audit log; easy add-ons, MVP, open questions |
| [spec/openshift-ai.md](spec/openshift-ai.md) | Our cluster (addresses, no passwords, L4 GPU), how to deploy a model with vLLM, models from the catalog, what the docs say about bonuses, getting-started checklist |
| [decisions/decyzje.md](decisions/decyzje.md) | Decisions made (including the LLM choice) and rejected ideas with reasons |
| [decisions/pomysly.md](decisions/pomysly.md) | Brainstorming ideas and open questions about them |
| [decisions/recenzja-pomyslu.md](decisions/recenzja-pomyslu.md) | External review of the "decision inbox" (swipe) concept: strengths, jury objections and answers, extensions, bonus and demo strategy |
| [examples/dane-przykladowe.md](examples/dane-przykladowe.md) | Analysis of the sample data (Pizzeria Amalfi 2025 bank statement) and its pitfalls |
| [examples/firmy/](examples/firmy/README.md) | Descriptions of example companies the project should work for (template in `examples/firmy/_szablon.md`) |
| [reference/](reference/README.md) | Organizers' original files (challenge card, slides, survival guide, project card, sample data) with an index of what each one is |
| [zadania.md](zadania.md) | To-do list |

The original files from the organizers (PDFs, CSV data) are in `reference/`, and their index is in `reference/README.md`. We do not edit them there; we write our conclusions in the other folders.

## Rules

- Write in English, short, in bullet points.
- One topic per file. Put a new file into the matching folder (`spec/`, `decisions/`, `examples/`) and add it to the table above. Do not add new files to the main folder.
- Write references to other files as a path relative to the `memory/` folder, e.g. `spec/wyzwanie.md`.
- For decisions and status changes, give the date in YYYY-MM-DD format.
- Do not delete other people's entries. Move an idea we drop to the "Rejected" section in `decisions/decyzje.md` and give the reason.
- When an open question from `decisions/pomysly.md` gets answered, write the answer into `decisions/decyzje.md`, strike out the question itself (`~~question~~`) and add a link to the decision.
- Do not write passwords, tokens or personal data.
