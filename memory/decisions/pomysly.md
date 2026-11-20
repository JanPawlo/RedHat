# Pomysły

Źródło: notatki z brainstormingu w Figmie (zob. `spec/projekt.md`).

## 1. KSeF: weryfikacja faktur, wyłapywanie przekrętów

Otwarte pytania:
- Jakie są przykładowe przekręty, które próbujemy powstrzymać?
- W jaki sposób je powstrzymujemy?
- W jaki sposób użytkownik korzysta z tej usługi?
- Jak zintegrować to rozwiązanie z KSeF?

## 2. Wykrywanie spójności faktur

- Brak szczegółów, do rozpisania. Prawdopodobnie jest blisko powiązany z pomysłem 1.

## 3. Chatbot jako część interfejsu

- Wizualizacje (wykresy liniowe, słupkowe itd.)
- Ogólne porady, np. „Czy sensownym jest zatrudnienie dodatkowych 2 pracowników?”

## 4. Prognozy finansowe

Na podstawie:
- faktur z KSeF,
- struktury firmy: liczba pracowników, stanowiska, spółka giełdowa / prywatna,
- stanu konta (co miesiąc?).

Lista danych wejściowych w Figmie kończy się pustym punktem, więc może być niepełna.

## 5. Skrzynka decyzji CFO ze swipe'owaniem

Opis z recenzji (`decisions/recenzja-pomyslu.md`) i z naszych notatek z brainstormingu (2026-11-20). W notatkach nazwa robocza to „Reigns: CFO support” albo „Tinder dla przedsiębiorców”.
- Problemy pokazujemy jako karty. Użytkownik decyduje, przeciągając kartę w prawo albo w lewo.
- Dane o firmie widać jako pionowe słupki (jak w grze Reigns).
- Po każdej decyzji prognozy się aktualizują.
- Autonomiczne, proaktywne działania agenta: sam tworzy karty problemów; generuje i wysyła maile pół-autonomicznie, na podstawie swipe'ów.
- Agent zamienia finanse na karty decyzji. Swipe w prawo albo w lewo to tak/nie; w górę zapytaj „dlaczego” albo złóż kontrofertę; w dół odłóż na później.
- Wskaźniki w stylu gry karcianej pokazują, jak decyzja zmieni prognozę gotówki, zanim ją zatwierdzimy.
- Agent sam przygotowuje maile (np. do dostawców) i wysyła je po akceptacji.
