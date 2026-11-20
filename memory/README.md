# Pamięć projektu

Ten folder to wspólna pamięć projektu dla ludzi i dla każdego asystenta AI (Claude, Gemini, ChatGPT, Copilot, Codex).
Asystent czyta te pliki przed pracą i dopisuje do nich to, czego się dowiedział.

## Struktura

| **Folder** | **Co tu trafia** |
| --- | --- |
| `spec/` | Najważniejsze: czym jest projekt, wymagania organizatorów, opis funkcji, nasze środowisko. Tu szukaj odpowiedzi „co budujemy i na czym”. |
| `decisions/` | Decyzje, pomysły z brainstormingu, recenzje i podpowiedzi. Tu szukaj odpowiedzi „co ustaliliśmy i dlaczego”. |
| `examples/` | Przykładowe firmy i dane testowe. Kontekst do demo i danych, nie wymagania. |
| `zadania.md` | Bieżąca lista zadań (zostaje w głównym folderze, bo zagląda się do niej najczęściej). |

## Pliki

| **Plik** | **Co zawiera** |
| --- | --- |
| [spec/projekt.md](spec/projekt.md) | Opis projektu, wyzwanie, źródła i linki |
| [spec/wyzwanie.md](spec/wyzwanie.md) | Streszczenie materiałów organizatorów: cel, 4 przypadki użycia, wymagania twarde, punktacja, środowisko, formularz zgłoszenia |
| [spec/funkcjonalnosci.md](spec/funkcjonalnosci.md) | Opis funkcji pod szkic interfejsu: ekran z prognozą, karty ze swipe, „Ask why” z czatem, outbox, autonomia i audit log; łatwe dodatki, MVP, otwarte pytania |
| [spec/openshift-ai.md](spec/openshift-ai.md) | Nasz klaster (adresy, bez haseł, GPU L4), jak wdrożyć model z vLLM, modele z katalogu, co docs mówią o bonusach, checklista na start |
| [decisions/decyzje.md](decisions/decyzje.md) | Podjęte decyzje (w tym wybór modelu LLM) oraz odrzucone pomysły wraz z powodami |
| [decisions/pomysly.md](decisions/pomysly.md) | Pomysły z brainstormingu i otwarte pytania do nich |
| [decisions/recenzja-pomyslu.md](decisions/recenzja-pomyslu.md) | Zewnętrzna recenzja koncepcji „skrzynki decyzji” (swipe): mocne strony, zarzuty jury i odpowiedzi, rozszerzenia, strategia bonusów i demo |
| [examples/dane-przykladowe.md](examples/dane-przykladowe.md) | Analiza danych przykładowych (wyciąg bankowy Pizzerii Amalfi 2025) i pułapki w nich |
| [examples/firmy/](examples/firmy/README.md) | Opisy przykładowych firm, dla których projekt ma działać (szablon w `examples/firmy/_szablon.md`) |
| [zadania.md](zadania.md) | Lista zadań do zrobienia |

Oryginalne pliki od organizatorów (PDF-y, dane CSV) leżą w `../materials/`, a ich spis jest w `../materials/README.md`. Tam ich nie edytujemy; wnioski zapisujemy tutaj.

## Zasady

- Pisz po polsku, krótko, w punktach.
- Jeden temat to jeden plik. Nowy plik wrzucaj do pasującego folderu (`spec/`, `decisions/`, `examples/`) i dopisz go do tabeli powyżej. W głównym folderze nie dodawaj nowych plików.
- Odwołania do innych plików pisz jako ścieżkę względem folderu `memory/`, np. `spec/wyzwanie.md`.
- Przy decyzjach i zmianach stanu podawaj datę w formacie RRRR-MM-DD.
- Nie usuwaj cudzych wpisów. Pomysł, z którego rezygnujemy, przenieś do sekcji „Odrzucone” w `decisions/decyzje.md` i podaj powód.
- Gdy na otwarte pytanie z `decisions/pomysly.md` padnie odpowiedź, wpisz ją do `decisions/decyzje.md`, a samo pytanie skreśl (`~~pytanie~~`) i dodaj odnośnik do decyzji.
- Nie wpisuj haseł, tokenów ani danych osobowych.
