# Challenge: Autonomous CFO (Red Hat / Commerzbank)

Sources: `materials/challenge-card-autonomous-cfo.pdf`, `materials/red-hat-challenge-slides.pdf`, `materials/openshift-ai-survival-guide.pdf`, `materials/project-card-fillable.pdf` (received 2026-11-20).

## Problem and goal

- Small and medium-sized enterprises (SMEs) are often run by owners who handle finances themselves. This takes their time and risks them missing something important.
- Goal: an AI-based CFO assistant that monitors finances, detects potential problems and proposes **explainable** next steps.
- Actions that require approval are shown in a **simulated** environment. If possible, we distinguish:
  - what the agents analyze on their own,
  - what they recommend,
  - what requires the user's approval,
  - whether execution is simulated or actually allowed.
- Collabothon theme: "Innovations for all generations". The app should be understandable for owners with different levels of technical skill, and the user should stay in control. It should be "fun and easy to use".

## Use cases (choose AT LEAST one)

A full flow must be shown: input data → explainable recommendation → user interaction. Additional agents are optional.

- **Liquidity agent**: monitors accounts, forecasts cash flow x days ahead and automatically proposes credit lines.
- **FX hedging agent**: detects currency risk from foreign invoices and sets up hedges using Commerzbank products.
- **Tax agent**: coordinates tax prepayments and looks for optimization opportunities.
- **Investment agent**: analyzes free cash and recommends investments (term deposits, money market funds, capex financing).

Expected result: a working end-to-end use case, an explanation of the business logic behind the agent's answer, and a demonstration of how the owner understands and responds to the proposed action.

## Hard requirements (without them, 0 points)

1. The app runs on **Red Hat OpenShift** in the environment provided by the organizers. The backend must run on the cluster; a mobile frontend may run outside it.
2. The app uses an **open source / open weights** model (e.g. Granite, Mistral, Qwen) deployed on **Red Hat OpenShift AI (RHOAI)**.

Without a working app or without meeting the basic requirements, there are no points at all.

## Scoring (table from the survival guide)

| **Criterion** | **Weight** | **Notes** |
| --- | --- | --- |
| App on OpenShift | 60 | disqualification if missing |
| Model on RHOAI used by the app | 60 | disqualification if missing |
| Use case | 12 | 0 = obvious fake, 10 = use case implemented |
| UI/UX | 12 | 0 = barely usable, 10 = "Jony Ive would be proud" |
| Bonus: vLLM | 1 | |
| Bonus: llm-d | 1 | |
| Bonus: model gateway (MaaS) | 1 | |
| Bonus: ogx + MCP for agent orchestration | 1 | |
| Bonus: OpenShell or NeMo Guardrails (min. 1 secured agent) | 2 | |
| Bonus: personal agentic assistant (OpenClaw, Pi) on OpenShift | 1 | usage logs must be shown |
| Bonus: MLflow for agent tracing and evaluation | 1 | |
| Bonus: Jupyter Notebooks on OpenShift AI | 1 | any task, e.g. analysis, fine-tuning |
| Bonus: Red Hat Dev Spaces ("VS Code in the browser") | 2 | |
| Bonus: OSS AI code assistant in Dev Spaces / JupyterLab on RHOAI | 2 | |
| Bonus: Quarkus + LangChain4J | 1 | one service is enough |

Organizers' advice: focus on the hard requirements and the domain logic, and do at most 2–4 bonuses. Bonus weights are lower than last year. Enabling everything at once will probably bring down the single-node cluster. After completing bonuses, you must report to Georg and Karsten so they can assess them.

Commercial assistants (Claude Code, Codex, Cursor) may be used locally or in Dev Spaces / JupyterLab, but OSS assistants on OpenShift AI are preferred.

## Environment

- Each team (up to 13 teams) gets its own single-node RHOAI cluster with a GPU: 32 CPU, 128 GB RAM. The stack must be chosen sensibly.
- **We only get access to the environment after giving the organizers the Git repository URLs** (organization-level access and a public link preferred). Registration is self-service; a real e-mail is not needed.
- Support: technical, remotely via Discord; on site, Georg and Karsten (Red Hat).
- The environment is deleted after the event without a backup. We use it only for the hackathon.
- Documentation: Red Hat OpenShift AI Self-Managed 3.5. A good general introduction is the "fraud detection example" tutorial (link in the survival guide).
- Deployment: via `oc new-app <image>~<git-repo>` (examples for Quarkus, Spring, Node.js and Python in the survival guide appendix), then `oc expose svc/<name>`.
- Organizers' suggestion: a web app in TypeScript (easy to distribute), but desktop and mobile are also allowed.

## Contacts

- Challenge: Sandra Fensterseifer, Thomas Muth, Anel Memic.
- Discord: #Commerzbank (business questions), #Red-Hat (technical questions).

## Consultation with an employee (Commerzbank), 2026-11-20

- Is a 60-day forecast short or long? CFOs divide forecasts into strategic (years) and tactical (quarters). For SMEs, **3-month** forecasts are the most practical.
- About our interface (cards, swipe): a nice idea, but underneath there must be an **"engine" that justifies the decisions**. Presenting this well in the presentation is also important.
- Standard CFO tasks: cash flow forecasting, securing access to financing and paying liabilities on time. For more details he referred us to LLMs.
- We can make a lot of assumptions about data access.

## Submission (Project Card)

Form `materials/project-card-fillable.pdf`, required fields:
- Project Name,
- One-Line Summary (max. 200 characters: what the project does and who it helps),
- Technology Stack,
- Project Overview with sections: The Problem, Your Solution, The Working Prototype (what actually works), Behind the Build (architecture, what we used, what we built ourselves), Challenges and Discoveries, Results and Next Steps,
- Source Code Repository (link).

## How this relates to our ideas

Observations, not decisions (decisions are made in `decisions/decyzje.md`):
- Idea 4 (financial forecasts) overlaps with the **Liquidity agent**.
- Idea 3 (chatbot with charts and advice) fits the requirement for explainable recommendations and UI/UX.
- Ideas 1 and 2 (KSeF, fraud, invoice consistency) are not any of the 4 use cases. At most they can be an add-on.
- KSeF is Polish, while the challenge and the sample data are German (Commerzbank, a bank in Frankfurt, German taxes).
