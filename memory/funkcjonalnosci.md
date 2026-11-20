# Funkcjonalności

Pełna lista funkcji, których potrzebujemy albo które mogą się przydać. 

To **propozycja, a nie decyzja**. Co bierzemy do MVP, wpisujemy do `decyzje.md`.

## Legenda

Priorytet:
- **P0**: wymaganie twarde. Bez tego mamy 0 punktów.
- **P1**: MVP na demo. Pełny przepływ: dane → wytłumaczalna rekomendacja → interakcja z użytkownikiem.
- **P2**: mocno podnosi ocenę (UI/UX, use case, bonus), robimy, jeśli starczy czasu.
- **P3**: pomysł na później albo na slajd „Next steps”.

Poziom autonomii (challenge card prosi o rozróżnienie):
- **A** (analizuje sam): agent liczy i monitoruje bez pytania.
- **R** (rekomenduje): agent proponuje i uzasadnia, a decyduje użytkownik.
- **Z** (wymaga zgody): akcja wykona się dopiero po zatwierdzeniu.
- **S / P** (symulowane / dozwolone): wykonanie idzie tylko do symulatora (S) albo naprawdę (P). Na hackathonie prawie wszystko jest S.

## Zasada nadrzędna: silnik liczy, LLM tłumaczy

- Interfejs jest fajny, ale **pod spodem musi być „silnik”**, który uzasadnia decyzje.
- Liczby (saldo, prognoza, kwoty, terminy) liczy deterministyczny kod. LLM ich nie wymyśla.
- LLM: tłumaczy wyniki prostym językiem, prowadzi rozmowę, układa treść kart i maili, wybiera narzędzia (tool calling).
- Każda liczba pokazana użytkownikowi ma źródło: konkretne transakcje, reguła albo założenie.

---

## 0. Platforma i wymagania twarde (P0)

| **#** | **Funkcja** | **Szczegóły** |
| --- | --- | --- |
| 0.1 | Backend działa na OpenShift | Deploy przez `oc new-app <obraz>~<repo>` + `oc expose svc/<nazwa>`; Route z HTTPS |
| 0.2 | Model open weights na RHOAI | Granite / Qwen / Mistral, serwowany przez vLLM (to od razu bonus) |
| 0.3 | Aplikacja **faktycznie woła** model | Endpoint modelu w konfiguracji (zmienna środowiskowa), bez kluczy w repo |
| 0.4 | Frontend dostępny przez URL | Najprościej: też na klastrze (jeden Route), da się otworzyć z telefonu jury |
| 0.5 | Health check i logi | `/health` dla OpenShift (readiness/liveness), logi wywołań modelu do pokazania jury |
| 0.6 | Działa bez internetu poza klastrem | Kursy walut i dane: lokalne pliki / mock, bez zewnętrznych API |
| 0.7 | Lekki stack | Klaster single-node (32 CPU, 128 GB, GPU): jeden model, 2–4 bonusy, nie wszystko naraz |

## 1. Dane wejściowe

| **#** | **Funkcja** | **Prio** | **Szczegóły** |
| --- | --- | --- | --- |
| 1.1 | Import wyciągu bankowego CSV | P1 | Format Pizzerii: separator `;`, cudzysłowy, przecinek dziesiętny, data `DD.MM.YY`, sortowanie od najnowszej |
| 1.2 | Obsługa walut | P1 | Przelewy do Zurychu są w **CHF**: przeliczenie na EUR po kursie z dnia (lokalna tabela kursów EBC) |
| 1.3 | Odtworzenie salda dziennego | P1 | Brak kolumny salda: liczymy wstecz od salda końcowego 33 266,35 EUR (31.12.2025) i weryfikujemy z wykresem (min. −22 097,60 EUR 03.07) |
| 1.4 | Kategoryzacja transakcji | P1 | Regułami po `Transaction Type` i kontrahencie: przychody kartowe, dostawcy, płace, czynsz, podatki, ZUS/składki, media, przelewy prywatne/inwestycje |
| 1.5 | Wykrywanie płatności cyklicznych | P1 | Czynsz 1., płace 28., składki 27., podatek od płac 10., zaliczki kwartalne, CHF 15.; z tego powstaje kalendarz zobowiązań |
| 1.6 | Profil firmy (onboarding) | P2 | Branża, liczba pracowników, stanowiska, forma prawna, sezonowość, minimalny bufor gotówki, znane przyszłe zdarzenia (np. „zamykamy w czerwcu na 3 tygodnie”) |
| 1.7 | Faktury (mock KSeF / e-faktury) | P2 | Faktury przychodzące i wychodzące z terminem płatności; na demo plik JSON/XML zaprojektowany jak prawdziwy feed (KSeF w PL, XRechnung/ZUGFeRD w DE) |
| 1.8 | Dopasowanie faktur do przelewów | P2 | W tytułach są numery (`Invoice AS-…`, `Invoice FLV-…`); daje to listę zapłaconych i niezapłaconych faktur |
| 1.9 | Konektory „jak prawdziwe” | P3 | PSD2 / open banking dla konta, KSeF API dla faktur; na hackathonie mocki z tym samym interfejsem |
| 1.10 | Wiele firm / profili | P2 | Przełącznik firm: Pizzeria Amalfi + profile z `firmy/target-group-profiles.md` (dane wygenerowane) |
| 1.11 | Symulowana data „dziś” | P1 | Dane są z 2025, więc na demo ustawiamy „dziś” (np. 2025-05-01) i agent widzi tylko przeszłość; suwak czasu pokazuje, co agent przewidział |

Możemy przyjmować dużo założeń o dostępie do danych. Zapisujemy je jawnie w aplikacji (ekran „Założenia”).

## 2. Silnik finansowy (deterministyczny)

| **#** | **Funkcja** | **Prio** | **Szczegóły** |
| --- | --- | --- | --- |
| 2.1 | Prognoza cash flow na 90 dni | P1 | Dla MŚP najpraktyczniejsza jest prognoza **3-miesięczna** (taktyczna). Dzienna rozdzielczość, widok tygodniowy |
| 2.2 | Model przychodów | P1 | Średnia wg dnia tygodnia i miesiąca (sezonowość), rytm wypłat kart (debetowe codziennie, kredytowe 2× w tygodniu) |
| 2.3 | Model kosztów | P1 | Koszty stałe z kalendarza (1.5) + zmienne jako % przychodu (dostawcy, rynek hurtowy) |
| 2.4 | Znane zdarzenia | P1 | Zamknięcie lokalu, zatrudnienie, jednorazowe wydatki: wpisywane przez użytkownika albo czatem |
| 2.5 | Pasmo niepewności | P2 | Scenariusz pesymistyczny / bazowy / optymistyczny (np. percentyle historycznych odchyleń) |
| 2.6 | Wskaźniki | P1 | Saldo min. w horyzoncie i jego data, dni do debetu, „runway”, wolna gotówka ponad bufor, udział kosztów stałych |
| 2.7 | Symulacja „co jeśli” | P1 | Zmiana parametru (linia kredytowa, przesunięcie płatności, nowy pracownik) → nowa prognoza; tej samej funkcji używają karty i czat |
| 2.8 | Wykrywanie problemów → kandydaci na karty | P1 | Reguły: saldo poniżej bufora, debet w horyzoncie, termin podatku przy niskim saldzie, nadwyżka ponad bufor, ekspozycja walutowa, nietypowa transakcja |
| 2.9 | Wykrywanie anomalii | P2 | Podwyżka cen dostawcy (średnia kwota faktury rośnie), duplikat płatności, nowy kontrahent, nietypowo duża kwota |
| 2.10 | Kalkulatory produktów (mock Commerzbank) | P1 | Koszt linii kredytowej (odsetki od wykorzystania), forward FX, lokata terminowa, fundusz rynku pieniężnego: stałe stawki z pliku konfiguracyjnego |

## 3. Agenci (przypadki użycia z wyzwania)

Wymagany jest co najmniej jeden pełny przypadek. Propozycja: **Liquidity jako główny** (pasuje do debetu Pizzerii w czerwcu i do tego, że prognozowanie cash flow to podstawowe zadanie CFO), a FX albo Investment jako drugi, jeśli starczy czasu.

### 3.1 Liquidity agent (P1)

- Monitoruje saldo i prognozę 90 dni (A).
- Wykrywa lukę, np. „po zamknięciu w czerwcu saldo spadnie do ok. −22 tys. EUR na początku lipca” (A).
- Proponuje rozwiązania z wyliczonym kosztem (R):
  - linia kredytowa / limit w rachunku w Commerzbanku na kwotę luki + bufor, z kosztem odsetek,
  - przesunięcie płatności do dostawcy (o ile dni i co to zmienia),
  - przesunięcie przelewu prywatnego (CHF do Zurychu) na później,
  - wcześniejsze odłożenie gotówki w maju.
- Wniosek o linię kredytową wymaga zgody (Z) i trafia do symulatora banku (S).
- Po decyzji przelicza prognozę i pokazuje różnicę.

### 3.2 FX hedging agent (P2)

- Wykrywa ekspozycję walutową: płatności w CHF (ok. 50 tys. CHF rocznie), faktury w obcej walucie (A).
- Liczy wrażliwość: „jeśli CHF podrożeje o 5%, zapłacisz ok. X EUR więcej rocznie” (A).
- Proponuje forward / zlecenie z limitem kursu na kolejne 3–6 miesięcy płatności (R).
- Zawarcie zabezpieczenia: zgoda (Z) i symulator (S).

### 3.3 Tax agent (P2)

- Kalendarz podatków i składek z historii (A).
- Ostrzega, gdy termin wypada przy niskim saldzie (A).
- Proponuje korektę zaliczek, gdy zysk odbiega od podstawy (zaliczka liczona od ok. 30 tys. EUR zysku, a rok kończy się wyżej). Tylko jako rekomendacja z prośbą o konsultację z doradcą podatkowym (R).
- Rezerwa na podatek: odkładanie części przychodów na subkonto (Z/S).

### 3.4 Investment agent (P2)

- Liczy wolną gotówkę: saldo − bufor − zobowiązania w horyzoncie − sezonowe dołki (A).
- Proponuje lokatę terminową / fundusz rynku pieniężnego tak, żeby pieniądze wróciły przed znanym dołkiem, np. przed czerwcem (R).
- Wyliczony zysk i data dostępności środków; ulokowanie: zgoda (Z) i symulator (S).
- Opcjonalnie finansowanie capex (np. nowy piec): kredyt czy gotówka.

### 3.5 Agent faktur / KSeF (P3, rozszerzenie pomysłów 1 i 2)

- Nie jest żadnym z 4 przypadków użycia, więc to tylko dodatek, który zasila karty.
- Spójność faktur: suma netto + VAT = brutto, NIP/VAT ID kontrahenta, duplikaty numerów, termin płatności.
- Sygnały przekrętu: zmiana numeru konta dostawcy, nowy kontrahent z dużą kwotą, faktura bez zamówienia, kwota tuż pod progiem akceptacji.
- Wyjście: karta „Sprawdź tę fakturę zanim zapłacisz” (R).

### 3.6 Orkiestrator / koordynator (P2)

- Zbiera kandydatów od agentów, usuwa konflikty (np. Investment chce ulokować pieniądze, których Liquidity potrzebuje w czerwcu) i ustala kolejność kart wg pilności i kwoty.
- Pasuje do bonusu ogx + MCP.

## 4. Skrzynka decyzji: karty ze swipe'em (pomysł 5)

| **#** | **Funkcja** | **Prio** | **Szczegóły** |
| --- | --- | --- | --- |
| 4.1 | Kolejka kart | P1 | Jedna karta = jedna decyzja; sortowanie wg pilności (termin) i wpływu (kwota) |
| 4.2 | Treść karty | P1 | Tytuł prostym językiem, kwota, termin, 1–2 zdania „dlaczego”, przewidywany efekt, ikona agenta, poziom autonomii (A/R/Z, S/P) |
| 4.3 | Swipe | P1 | Prawo = tak, lewo = nie; **góra = „dlaczego?” / kontroferta**, **dół = odłóż**. Zawsze też zwykłe przyciski (dostępność, desktop) |
| 4.4 | Wskaźniki w stylu Reigns | P1 | Pionowe słupki u góry: np. Gotówka, Bezpieczeństwo (dni bez debetu), Zobowiązania, Ryzyko walutowe. Najechanie albo przytrzymanie karty pokazuje, który słupek się zmieni |
| 4.5 | Podgląd skutku przed decyzją | P1 | Mini-wykres prognozy „przed / po” na karcie |
| 4.6 | Prognoza po decyzji | P1 | Po swipe silnik przelicza prognozę, a słupki się animują |
| 4.7 | Tarcie zależne od kwoty | P2 | Mała kwota: szybki swipe; duża: przytrzymanie / potwierdzenie; próg ustawia użytkownik |
| 4.8 | Cofnięcie (undo) | P2 | Okno np. 10 minut, zanim akcja (mail, wniosek) wyjdzie do symulatora |
| 4.9 | Historia decyzji | P1 | Lista: co zaproponowano, co wybrał użytkownik, kiedy i z jakim skutkiem |
| 4.10 | Swipe'y zamieniają się w reguły | P2 | Po kilku takich samych decyzjach agent pyta „Zawsze tak robić, jeśli bufor się utrzyma?”; reguła ma limit kwoty i można ją wyłączyć (najbardziej oryginalne według recenzji) |
| 4.11 | Karty dla różnych osób | P3 | Współwłaściciel, księgowa / biuro rachunkowe dostają swoje karty |

Typy kart (przykłady pod Pizzerię):
- „W lipcu zabraknie ok. 22 tys. EUR. Otworzyć linię kredytową 25 tys. EUR (koszt ok. X EUR)?” (Liquidity)
- „Przesunąć przelew do Luigiego z 15.06 na 15.08?” (Liquidity)
- „CHF zdrożał o 3% od stycznia. Zabezpieczyć kurs na 6 kolejnych przelewów?” (FX)
- „10.06 zaliczka 1150 EUR przy niskim saldzie: odłożyć teraz?” (Tax)
- „Masz ok. 20 tys. EUR ponad bufor. Lokata 3-mies. do marca?” (Investment)
- „Asimex podniósł ceny o 8% w ciągu kwartału. Napisać do dostawcy?” (anomalia + mail)

## 5. Wyjaśnialność

| **#** | **Funkcja** | **Prio** | **Szczegóły** |
| --- | --- | --- | --- |
| 5.1 | Panel „Dlaczego?” | P1 | Łańcuch: dane → reguła → liczba → rekomendacja, prostym językiem |
| 5.2 | Źródła | P1 | Lista transakcji / faktur, z których wynika liczba (klikalna) |
| 5.3 | Założenia | P1 | Np. „przyjęliśmy kurs 0,94 CHF/EUR”, „przychód w lipcu jak średnia z lipca–sierpnia” |
| 5.4 | Alternatywy | P2 | Co jeszcze rozważył agent i dlaczego odrzucił (np. kredyt vs przesunięcie płatności) |
| 5.5 | Pewność | P2 | Niska / średnia / wysoka, zależnie od ilości danych i zmienności |
| 5.6 | Konflikt interesów | P2 | Gdy agent poleca produkt Commerzbanku, mówimy to wprost i pokazujemy alternatywę (radzi recenzja; jury to doceni) |

## 6. Akcje, zgody i symulator

| **#** | **Funkcja** | **Prio** | **Szczegóły** |
| --- | --- | --- | --- |
| 6.1 | Macierz autonomii | P1 | Ekran / tabela: która akcja jest A, R, Z, S, P; użytkownik może zaostrzyć |
| 6.2 | Symulator banku (mock Commerzbank) | P1 | Endpointy: wniosek o linię kredytową, forward FX, lokata, przelew, subkonto podatkowe; odpowiedź „zaakceptowano (symulacja)” z numerem referencyjnym |
| 6.3 | Wyraźne oznaczenie symulacji | P1 | Na każdej wykonanej akcji etykieta „SYMULACJA” |
| 6.4 | Szkice maili | P2 | Agent pisze maila (do dostawcy, klienta, banku); wysyła dopiero po akceptacji |
| 6.5 | Testowy serwer poczty | P2 | Mailpit na klastrze: na demo maile lądują na żywo na ekranie |
| 6.6 | Dziennik audytowy | P1 | Każda akcja: kto, kiedy, co, dlaczego, wynik; nie da się go edytować |
| 6.7 | Limity i lista odbiorców | P2 | Agent pisze tylko do znanych kontrahentów i nie zobowiązuje się powyżej kwoty X |
| 6.8 | Przypomnienia o zaległych fakturach | P3 | Sekwencja coraz stanowczych przypomnień (szybko odzyskana gotówka) |
| 6.9 | Kontroferta / negocjacje | P3 | Swipe w górę: agent pisze kontrpropozycję, np. „30 dni zamiast 14?” |

## 7. Chatbot (pomysł 3)

| **#** | **Funkcja** | **Prio** | **Szczegóły** |
| --- | --- | --- | --- |
| 7.1 | Pytania o finanse firmy | P1 | Odpowiedź z danych przez narzędzia, a nie z „pamięci” modelu: `get_balance`, `get_forecast`, `list_transactions`, `get_obligations`, `simulate` |
| 7.2 | Wykresy w odpowiedzi | P2 | Liniowy (saldo + prognoza), słupkowy (koszty wg kategorii), kalendarz płatności |
| 7.3 | Pytania „co jeśli” | P1 | „Czy stać mnie na 2 dodatkowych pracowników?”: czat ustala pensje, woła `simulate` i odpowiada z wykresem i ryzykiem |
| 7.4 | Czat przy karcie | P1 | Swipe w górę otwiera czat z kontekstem karty („dlaczego tyle?”, „a jak przesunę o tydzień?”) |
| 7.5 | Tworzenie kart z czatu | P2 | „Przypomnij mi o…” albo „zaplanuj zakup pieca” zamienia się w kartę lub znane zdarzenie |
| 7.6 | Prosty język, bez żargonu | P1 | Instrukcja systemowa + słowniczek; przycisk „wyjaśnij prościej” |
| 7.7 | Języki | P2 | EN na demo (jury), opcjonalnie DE / PL |
| 7.8 | Odmowa poza zakresem | P2 | Bez porad inwestycyjnych „na pewniaka”; przy podatkach odsyła do doradcy (guardrails) |

Przykładowe pytania (Pizzeria): „Czy przetrwam czerwiec bez debetu?”, „Ile mogę bezpiecznie przelać Luigiemu?”, „Co zrobić z nadwyżką na koniec roku?”.

## 8. Ekrany i wizualizacje

| **#** | **Ekran** | **Prio** | **Szczegóły** |
| --- | --- | --- | --- |
| 8.1 | Start / „Dziś” | P1 | Słupki stanu firmy, 1 zdanie podsumowania („Najbliższe 90 dni: OK do 10.06, potem luka”), liczba kart do decyzji |
| 8.2 | Skrzynka decyzji | P1 | Karty ze swipe (sekcja 4) |
| 8.3 | Prognoza | P1 | Wykres salda: historia + prognoza 90 dni + pasmo + linia bufora + zaznaczone zdarzenia |
| 8.4 | Kalendarz zobowiązań | P2 | Podatki, płace, czynsz, raty na osi czasu |
| 8.5 | Czat | P1 | Pełnoekranowy albo panel boczny |
| 8.6 | Historia i dziennik | P1 | Decyzje + audyt |
| 8.7 | Ustawienia | P2 | Bufor, progi zgody, reguły, tryb prosty / zaawansowany, język |
| 8.8 | Dane i założenia | P2 | Skąd dane, kiedy aktualizowane, przyjęte założenia |

## 9. UX „dla wszystkich pokoleń”

- **Mobile-first**, ale też działa na desktopie (jury może oglądać na rzutniku).
- Tryb prosty: duże litery, mało liczb, zdania zamiast tabel; tryb zaawansowany: pełne wykresy i tabele.
- Dostępność: kontrast, alternatywa przycisków dla swipe, obsługa klawiaturą, czytnik ekranu.
- Ton przyjazny, „jak rozmowa ze znajomym” (profil salonu kosmetycznego w `firmy/target-group-profiles.md`).
- Onboarding w 3 krokach: wgraj wyciąg → odpowiedz na 3 pytania o firmę → pierwsze karty.
- Element „fun”: animacje słupków, krótkie podsumowanie tygodnia.

## 10. Bezpieczeństwo i guardrails

| **#** | **Funkcja** | **Prio** | **Szczegóły** |
| --- | --- | --- | --- |
| 10.1 | NeMo Guardrails albo OpenShell | P2 | Zasady: brak maili do niezatwierdzonych odbiorców, brak zobowiązań powyżej X, brak akcji bez zgody (bonus 2 pkt) |
| 10.2 | Demo zablokowanej akcji | P2 | Na demo próbujemy złamać regułę i guardrail ją blokuje |
| 10.3 | Walidacja wyjścia LLM | P1 | Kwoty w tekście muszą się zgadzać z silnikiem; inaczej odrzucamy i generujemy ponownie |
| 10.4 | Bez sekretów w repo | P0 | Konfiguracja przez Secret / ConfigMap w OpenShift |
| 10.5 | Dane | P1 | Tylko dane przykładowe / wygenerowane, bez prawdziwych danych osobowych |

## 11. Obserwowalność i ewaluacja

- MLflow tracing (bonus): każde wywołanie agenta i narzędzia widoczne jako „ślad decyzji”; to też odpowiedź na pytanie „dlaczego agent tak zrobił” (P2).
- Ewaluacja: zestaw pytań testowych do czatu z oczekiwanymi liczbami; sprawdzamy, czy model nie zmyśla (P2).
- Jupyter Notebook na RHOAI (bonus): analiza CSV Pizzerii, odtworzenie salda, strojenie prognozy (P2, tani bonus, bo tę analizę i tak robimy).

## 12. Bonusy: co pasuje do funkcji

Rada organizatorów: 2–4 bonusy. Propozycja (decyzja w `decyzje.md`):

| **Bonus** | **Pkt** | **Funkcja, która go daje** | **Koszt** |
| --- | --- | --- | --- |
| vLLM | 1 | 0.2: serwowanie modelu | niski (i tak potrzebne) |
| Jupyter na RHOAI | 1 | 11: analiza danych, prognoza | niski |
| ogx + MCP | 1 | narzędzia agentów jako MCP (`get_balance`, `get_forecast`, `simulate`, `draft_email`, `submit_to_bank`) + orkiestrator 3.6 | średni |
| NeMo Guardrails | 2 | 10.1–10.2 | średni |
| MLflow | 1 | 11: ślad decyzji | średni |
| Quarkus + LangChain4J | 1 | gdyby backend był w Javie | zależy od zespołu |
| Dev Spaces | 2 | praca w przeglądarce na klastrze | niski, ale obciąża klaster |

## 13. Scenariusz demo (Pizzeria Amalfi)

1. „Dziś” = 2025-05-01. Start: słupki, zdanie „Do 10.06 OK, potem luka do ok. −22 tys. EUR”.
2. Karta Liquidity: linia kredytowa 25 tys. EUR. „Dlaczego?” → wykres + zamknięcie w czerwcu + koszty stałe. Swipe w prawo → symulator banku → prognoza bez debetu.
3. Karta: przesunięcie przelewu do Luigiego; swipe w górę → czat „a jeśli przesunę tylko połowę?”.
4. Karta FX: CHF; podgląd wpływu.
5. Przeskok czasu na grudzień: karta Investment, nadwyżka ok. 33 tys. EUR → lokata do maja (przed kolejnym czerwcem).
6. Próba akcji poza regułami → blokada guardrails.
7. Dziennik audytowy + ślad w MLflow: „tak agent doszedł do tej rekomendacji”.

Ważne jest też dobre przedstawienie tego na prezentacji, więc demo trzeba przećwiczyć.

## 14. Proponowana kolejność prac

1. P0: hello-world na OpenShift + model przez vLLM + aplikacja woła model.
2. Import CSV + saldo dzienne + kategoryzacja (1.1–1.5) i weryfikacja z wykresem.
3. Prognoza 90 dni + „co jeśli” (2.1–2.7).
4. Liquidity agent + karty + panel „Dlaczego?” + symulator banku.
5. Czat z narzędziami.
6. Bonusy (Jupyter, guardrails, MCP, MLflow) i drugi agent.
7. Szlify UI, demo, Project Card.

## Otwarte pytania

- Jakie stawki / produkty Commerzbanku przyjąć do symulatora (linia kredytowa, forward, lokata)? Można zapytać na #Commerzbank.
- Rynek: niemieckie dane przykładowe czy polski KSeF? Albo uniwersalny moduł faktur z adapterami.
- Który model zmieści się obok reszty i dobrze robi tool calling (Granite 3.x, Qwen 2.5/3 7–14B)?
- Język interfejsu na demo (EN?) i jak pokazać PL/DE.
- Backend: TypeScript (sugestia organizatorów) czy Python (łatwiej o prognozy) czy Quarkus (bonus)?
