# Wyzwanie: Autonomous CFO (Red Hat / Commerzbank)

Źródła: `materials/challenge-card-autonomous-cfo.pdf`, `materials/red-hat-challenge-slides.pdf`, `materials/openshift-ai-survival-guide.pdf`, `materials/project-card-fillable.pdf` (otrzymane 2026-11-20).

## Problem i cel

- Małymi i średnimi firmami (MŚP) często kierują właściciele, którzy sami zajmują się finansami. Zabiera im to czas i grozi tym, że przeoczą coś ważnego.
- Cel: asystent CFO oparty na AI, który monitoruje finanse, wykrywa potencjalne problemy i proponuje **wytłumaczalne** kolejne kroki.
- Akcje wymagające zgody pokazujemy w **symulowanym** środowisku. Jeśli się da, rozróżniamy:
  - co agenci analizują samodzielnie,
  - co rekomendują,
  - co wymaga zgody użytkownika,
  - czy wykonanie jest symulowane, czy dozwolone naprawdę.
- Motyw Collabothonu: „Innovations for all generations”. Aplikacja ma być zrozumiała dla właścicieli o różnej biegłości technicznej, a użytkownik ma zachować kontrolę. Ma być „fun and easy to use”.

## Przypadki użycia (wybrać CO NAJMNIEJ jeden)

Trzeba pokazać pełny przepływ: dane wejściowe → wytłumaczalna rekomendacja → interakcja z użytkownikiem. Kolejne agenty są opcjonalne.

- **Liquidity agent**: monitoruje konta, prognozuje cash flow x dni do przodu i automatycznie proponuje linie kredytowe.
- **FX hedging agent**: wykrywa ryzyko walutowe z faktur zagranicznych i układa zabezpieczenia z użyciem produktów Commerzbanku.
- **Tax agent**: koordynuje zaliczki na podatki i szuka możliwości optymalizacji.
- **Investment agent**: analizuje wolną gotówkę i rekomenduje inwestycje (lokaty terminowe, fundusze rynku pieniężnego, finansowanie capex).

Oczekiwany wynik: działający use case end-to-end, wyjaśniona logika biznesowa stojąca za odpowiedzią agenta oraz pokazanie, jak właściciel rozumie proponowaną akcję i na nią reaguje.

## Wymagania twarde (bez nich 0 punktów)

1. Aplikacja działa na **Red Hat OpenShift** w środowisku od organizatorów. Backend musi działać na klastrze; frontend mobilny może działać poza nim.
2. Aplikacja używa modelu **open source / open weights** (np. Granite, Mistral, Qwen) wdrożonego na **Red Hat OpenShift AI (RHOAI)**.

Bez działającej aplikacji albo bez spełnienia wymagań podstawowych nie ma żadnych punktów.

## Punktacja (tabela z survival guide)

| **Kryterium** | **Waga** | **Uwagi** |
| --- | --- | --- |
| Aplikacja na OpenShift | 60 | dyskwalifikacja, jeśli brak |
| Model na RHOAI używany przez aplikację | 60 | dyskwalifikacja, jeśli brak |
| Use case | 12 | 0 = oczywisty fake, 10 = use case zaimplementowany |
| UI/UX | 12 | 0 = ledwo używalne, 10 = „Jony Ive byłby dumny” |
| Bonus: vLLM | 1 | |
| Bonus: llm-d | 1 | |
| Bonus: model gateway (MaaS) | 1 | |
| Bonus: ogx + MCP do orkiestracji agentów | 1 | |
| Bonus: OpenShell albo NeMo Guardrails (min. 1 zabezpieczony agent) | 2 | |
| Bonus: osobisty asystent agentowy (OpenClaw, Pi) na OpenShift | 1 | trzeba pokazać logi użycia |
| Bonus: MLflow do tracingu i ewaluacji agentów | 1 | |
| Bonus: Jupyter Notebooks na OpenShift AI | 1 | dowolne zadanie, np. analiza, fine-tuning |
| Bonus: Red Hat Dev Spaces („VS Code w przeglądarce”) | 2 | |
| Bonus: OSS AI code assistant w Dev Spaces / JupyterLab na RHOAI | 2 | |
| Bonus: Quarkus + LangChain4J | 1 | wystarczy jeden serwis |

Rada organizatorów: skupić się na wymaganiach twardych i logice domenowej, a bonusów robić najwyżej 2–4. Wagi bonusów są mniejsze niż w zeszłym roku. Włączenie wszystkiego naraz prawdopodobnie położy klaster single-node. Po zrobieniu bonusów trzeba się zgłosić do Georga i Karstena, żeby je ocenili.

Komercyjnych asystentów (Claude Code, Codex, Cursor) wolno używać lokalnie albo w Dev Spaces / JupyterLab, ale preferowane są asystenci OSS na OpenShift AI.

## Środowisko

- Każdy zespół (do 13 zespołów) dostaje własny klaster RHOAI single-node z GPU: 32 CPU, 128 GB RAM. Stack trzeba dobrać rozsądnie.
- **Dostęp do środowiska dostajemy dopiero po podaniu organizatorom URL-i repozytoriów Git** (preferowany dostęp na poziomie organizacji i publiczny link). Rejestracja jest samodzielna, prawdziwy e-mail nie jest potrzebny.
- Wsparcie: techniczne zdalnie przez Discorda; na miejscu Georg i Karsten (Red Hat).
- Środowisko jest usuwane po wydarzeniu bez backupu. Używamy go tylko do hackathonu.
- Dokumentacja: Red Hat OpenShift AI Self-Managed 3.5. Dobry ogólny wstęp to tutorial „fraud detection example” (link w survival guide).
- Deployment: przez `oc new-app <obraz>~<repo-git>` (przykłady dla Quarkus, Spring, Node.js i Pythona w aneksie survival guide), potem `oc expose svc/<nazwa>`.
- Sugestia organizatorów: aplikacja webowa w TypeScripcie (łatwa do rozpowszechnienia), ale desktop i mobile też są dozwolone.

## Kontakty

- Challenge: Sandra Fensterseifer, Thomas Muth, Anel Memic.
- Discord: #Commerzbank (pytania biznesowe), #Red-Hat (pytania techniczne).

## Konsultacja z pracownikiem(Commerzbank), 2026-11-20

- Czy prognoza na 60 dni to mało, czy dużo? CFO dzielą prognozy na strategiczne (lata) i taktyczne (kwartały). Dla MŚP najpraktyczniejsze są prognozy **3-miesięczne**.
- O naszym interfejsie (karty, swipe): fajny pomysł, ale pod spodem musi być **„silnik”, który uzasadnia decyzje**. Ważne jest też dobre przedstawienie tego na prezentacji.
- Standardowe zadania CFO: prognozowanie cash flow, zapewnienie dostępu do finansowania i terminowe opłacanie zobowiązań. Po więcej szczegółów odesłał nas do LLM-ów.
- Możemy przyjmować dużo założeń co do dostępu do danych.

## Zgłoszenie (Project Card)

Formularz `materials/project-card-fillable.pdf`, pola wymagane:
- Project Name,
- One-Line Summary (maks. 200 znaków: co robi projekt i komu pomaga),
- Technology Stack,
- Project Overview z sekcjami: The Problem, Your Solution, The Working Prototype (co działa naprawdę), Behind the Build (architektura, z czego korzystaliśmy, co zrobiliśmy sami), Challenges and Discoveries, Results and Next Steps,
- Source Code Repository (link).

## Jak to się ma do naszych pomysłów

Obserwacje, nie decyzje (decyzje zapadają w `decisions/decyzje.md`):
- Pomysł 4 (prognozy finansowe) pokrywa się z **Liquidity agentem**.
- Pomysł 3 (chatbot z wykresami i poradami) pasuje do wymogu wytłumaczalnych rekomendacji i UI/UX.
- Pomysły 1 i 2 (KSeF, przekręty, spójność faktur) nie są żadnym z 4 przypadków użycia. Mogą być najwyżej dodatkiem.
- KSeF jest polski, a wyzwanie i dane przykładowe są niemieckie (Commerzbank, bank we Frankfurcie, podatki DE).
