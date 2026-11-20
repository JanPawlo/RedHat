# RedHat
Collabothon Red Hat's challenge about creating an autonomus CFO agent for small-medium companies.

## Where is what

| **Path** | **What is there** |
| --- | --- |
| [`memory/`](memory/) | Shared project memory: everything we know and decide (plain Markdown, in Polish) |
| [`materials/`](materials/) | Original files from the challenge organizers (challenge card, slides, survival guide, project card, sample data); index in [`materials/README.md`](materials/README.md) |
| [`AGENTS.md`](AGENTS.md) | Instructions for AI assistants: read `memory/` first, write new findings back there |
| `CLAUDE.md`, `GEMINI.md` | Only import `AGENTS.md`, so Claude Code and Gemini CLI load it automatically |

## Project memory

Everything we know and decide about the project lives in [`memory/`](memory/) as plain Markdown (written in Polish), so it works with any AI assistant, not only Claude Code.

| **File** | **Purpose** |
| --- | --- |
| [`memory/README.md`](memory/README.md) | Index of memory files and the rules for editing them |
| [`memory/spec/`](memory/spec/) | The essentials: project description, challenge summary (requirements, scoring), features, our OpenShift AI cluster and model deployment |
| [`memory/decisions/`](memory/decisions/) | Decisions (incl. LLM choice) and rejected ideas, brainstorm ideas, external review of the concept |
| [`memory/examples/`](memory/examples/) | Sample data analysis (Pizzeria Amalfi 2025) and example companies; copy `firmy/_szablon.md` to add one |
| [`memory/zadania.md`](memory/zadania.md) | To-do list |

### Using it with your assistant

- **Claude Code, Gemini CLI, Codex, Copilot:** open the repo; they pick up `AGENTS.md` (or `CLAUDE.md` / `GEMINI.md`) on their own.
- **ChatGPT, Gemini or Claude in the browser:** paste or upload `AGENTS.md` and the files from `memory/` at the start of the chat, then ask it to return the updated files and commit them.
