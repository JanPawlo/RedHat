# Funkcjonalności

Opis funkcji aplikacji. Wersja z 2026-11-20, przepisana pod pierwszy szkic interfejsu (karty ze swipe, ekran z prognozą, outbox, audit log). Grafika będzie się jeszcze zmieniać; ten plik opisuje, **co** aplikacja robi, a nie jak dokładnie wygląda.

To **propozycja, a nie decyzja**. Co bierzemy do MVP, wpisujemy do `decyzje.md`.

## W skrócie

Aplikacja to asystent finansowy dla właściciela małej lub średniej firmy. Sama pilnuje pieniędzy firmy, a gdy coś wymaga decyzji, pokazuje to jako **kartę**. Właściciel przegląda karty jak w Tinderze: **w prawo = tak, w lewo = nie**. Jeśli chce wiedzieć więcej, klika **„Ask why”**: karta się odwraca i pokazuje, skąd wzięła się propozycja, a obok otwiera się czat z AI. Na ekranie głównym widać **prognozę gotówki** na najbliższe tygodnie i to, jak decyzje ją zmieniają.

Aplikacja ma działać **ogólnie dla różnych firm** (gastronomia, usługi, transport…), a nie pod jedną konkretną.

## Słowniczek

| **Pojęcie** | **Znaczenie** |
| --- | --- |
| Karta | Jedna sprawa do decyzji, np. „Zapłacić fakturę wcześniej i dostać 4% rabatu?” |
| Talia (deck) | Kolejka kart na dziś |
| Swipe | Przeciągnięcie karty palcem albo myszą w bok; to samo robią przyciski |
| Silnik | Zwykły kod (bez AI), który liczy saldo, prognozę i skutki decyzji |
| Agent | Część aplikacji, która pilnuje jednego obszaru (płynność, waluty, podatki…) i tworzy karty |
| Bufor bezpieczeństwa | Minimalna kwota, poniżej której saldo nie powinno spaść; ustawia ją właściciel |
| Runway | Na ile miesięcy wystarczy gotówki przy obecnych kosztach |
| Outbox | Maile, które AI napisało na podstawie decyzji |
| Autopilot | Próg kwoty, poniżej którego agent może działać sam, bez pytania |
| Symulacja | Akcja „bankowa” idzie do udawanego banku, a nie do prawdziwego |

## Zasada nadrzędna: silnik liczy, AI tłumaczy

- Pod ładnym interfejsem musi być **„silnik”, który uzasadnia decyzje**.
- **Liczby** (saldo, prognoza, kwoty, terminy, skutki decyzji) liczy deterministyczny kod. Model językowy ich nie wymyśla.
- **Model językowy (LLM)** pisze treść kart prostym językiem, odpowiada w czacie, pisze maile i wybiera narzędzia (np. „przelicz prognozę, jeśli zapłacę za tydzień”).
- Każda liczba w aplikacji ma **źródło**: konkretne transakcje, faktura, reguła albo jawne założenie.
- Kontrola: jeśli LLM poda w tekście kwotę inną niż silnik, odpowiedź jest odrzucana i generowana ponownie.

---

## Główne funkcjonalności

### F1. Ekran główny: stan firmy i prognoza gotówki

Pierwsza rzecz, którą widzi właściciel. W 10 sekund ma wiedzieć, czy jest dobrze, czy źle i ile ma decyzji do podjęcia.

**Pasek górny**
- Logo i nazwa firmy; przełącznik firm (aplikacja obsługuje kilka profili).
- Zakładki: **Deck** (karty, z liczbą czekających), **Outbox**, **Ledger** (historia i audit log), **Rules** (reguły).
- Przełącznik **autopilota** z progiem kwoty (np. „Autopilot under 2,000”).
- Plakietka **„OpenShift AI · vLLM · <model> active”**. Pokazuje jury, że działa model z klastra (wymaganie twarde), i zmienia się na czerwoną, gdy model nie odpowiada.

**Wskaźniki (słupki w stylu gry Reigns)**
- 4 poziome paski z ikoną, nazwą i wartością. W szkicu: Cash, Runway, Team, Trust (zestaw do ustalenia, patrz „Otwarte pytania”).
- Gdy użytkownik najedzie na wybór na karcie albo zacznie ją przeciągać, **nad słupkami, które ta decyzja zmieni, pojawia się kropka**, a pasek pokazuje nową wartość. Dzięki temu skutek widać przed decyzją.

**Wykres prognozy gotówki**
- Oś X: dni od dziś (domyślnie 60, przełącznik 30 / 60 / 90). Oś Y: saldo.
- **Linia bazowa**: co się stanie, jeśli nic nie zrobimy.
- **Luka płynności**: miejsce, gdzie saldo spada poniżej zera albo bufora, zaznaczone na czerwono z etykietą, np. „Liquidity gap −32,000 in 18 days”.
- **Linia przerywana „po zatwierdzonych akcjach”**: prognoza po decyzjach z kart, z etykietą różnicy (np. „After approved actions: +8,400”).
- **Pozioma linia bufora bezpieczeństwa.**
- Po najechaniu na punkt: saldo tego dnia i największe wpływy i wydatki w tym dniu.
- Licznik **„Cash protected”**: suma, którą decyzje z kart uratowały albo zaoszczędziły.

**Podsumowanie jednym zdaniem**
- Np. „Do 10 grudnia wszystko OK. Potem czynsz i pensje zbiegają się w jednym tygodniu. 3 karty czekają, ok. 2 minuty.” Zdanie pisze LLM, a liczby podaje silnik.

### F2. Talia kart decyzji (swipe jak w Tinderze)

Serce aplikacji. Zamiast tabel i raportów właściciel dostaje kilka konkretnych pytań „tak / nie”.

**Budowa karty**
- **Nagłówek:** awatar z inicjałami kontrahenta (albo ikona agenta), nazwa kontrahenta, kategoria (np. „Flour supplier · Payables”).
- **Pytanie w tytule**, prostym językiem: „Pay invoice 21 days early to get a 4% discount?”
- **Opis z liczbami**, 1–2 zdania: która faktura, kwota, termin, ile zyskujemy i czy saldo zostanie nad buforem.
- **Podpowiedź agenta:** „I'd swipe right · 86% confident”. Agent mówi, co by zrobił i jak bardzo jest pewny.
- **Dwa przyciski z nazwanymi skutkami**, a nie samym „tak/nie”: „Pay on due date” (lewo), „Pay early, take 4%” (prawo).
- Plakietki: poziom autonomii („Requires approval”) i źródło produktu (np. „Commerzbank”, jeśli to produkt banku).

**Gesty i sterowanie**

| **Ruch** | **Przycisk** | **Skutek** |
| --- | --- | --- |
| W prawo | Approve | Zgoda na propozycję agenta |
| W lewo | Decline | Odrzucenie, karta znika |
| W górę | Ask why | Odwraca kartę i otwiera czat (F3) |
| W dół | Later | Odkłada kartę (dziś wieczorem / jutro / za tydzień) |

- Każdy gest ma **zwykły przycisk** pod kartą (dla osób, które nie lubią przeciągać, i na desktopie) i **skrót klawiszowy** (strzałki).
- Pasek postępu: „Card 3 of 7 · about 2 min left”.
- **Undo last swipe:** cofnięcie ostatniej decyzji, zanim akcja wyjdzie (np. 10 minut na maile).
- **Tarcie przy dużych kwotach:** powyżej progu autopilota zwykły swipe nie wystarczy; trzeba przytrzymać przycisk albo potwierdzić.

**Co się dzieje po swipe**
1. Decyzja zapisuje się w historii (Ledger).
2. Jeśli trzeba, powstaje akcja: szkic maila w Outboxie albo zlecenie w symulatorze banku.
3. Silnik przelicza prognozę; słupki i wykres się animują.
4. Agent pokazuje następną kartę.

**Skąd bierze się „pewność” (86%)**
- Nie z odczuć modelu, tylko z silnika: prognozę liczymy w kilku scenariuszach (pesymistyczny, bazowy, optymistyczny, ewentualnie więcej losowań).
- Pewność = w ilu scenariuszach rekomendacja nadal jest dobra (np. saldo zostaje nad buforem). Proste do policzenia i do wytłumaczenia.

**Kolejność kart:** najpierw pilne (bliski termin), potem największy wpływ na gotówkę.

### F3. „Ask why”: odwrócona karta i czat

Odpowiedź na wymaganie wyzwania: właściciel ma **rozumieć**, skąd jest rekomendacja, i zachować kontrolę.

**Odwrócenie karty**
- Po „Ask why” (albo swipe w górę) karta obraca się animacją na **drugą stronę**.
- Na odwrocie jest sekcja **„What I looked at”**, czyli dane, na których oparł się agent, z wartościami:
  - saldo w banku, kwota i numer faktury, termin, rabat za wcześniejszą płatność,
  - najniższe saldo w najbliższych 60 dniach, bufor bezpieczeństwa.
- **Mini-wykres** prognozy tygodniowej (np. 8 słupków = 8 tygodni) z linią bufora i podświetlonym tygodniem, którego dotyczy decyzja; przełącznik „teraz / jeśli swipe w prawo”.
- **Źródła** na dole: „Bank feed · e-invoices · payroll export”; kliknięcie pokazuje konkretne transakcje albo fakturę.
- Przyciski decyzji są dostępne także na odwrocie, więc można zdecydować bez wracania.
- Przycisk „Wróć” obraca kartę z powrotem.

**Czat do karty**
- Otwiera się razem z odwróceniem (na telefonie pod kartą, na komputerze obok niej).
- Zna kontekst karty, więc nie trzeba niczego wpisywać od zera.
- **Podpowiedzi pytań** (klikane „chipsy”): „Co jeśli zapłacę za tydzień?”, „Ile to kosztuje?”, „Jakie są inne opcje?”, „Wyjaśnij prościej”.
- Pytania „co jeśli” uruchamiają silnik; mini-wykres na karcie aktualizuje się na żywo.
- Agent może zaproponować **zmienioną decyzję** (np. „zapłać połowę teraz”); wtedy karta dostaje nowy wariant do swipe'a.
- Przy produktach banku agent mówi wprost, że poleca produkt Commerzbanku, i pokazuje alternatywę (uczciwość wobec użytkownika).

**Czat ogólny** (poza kartami)
- Dostępny z ekranu głównego. Pytania typu: „Czy stać mnie na 2 nowych pracowników?”, „Kiedy będzie najtrudniejszy tydzień?”, „Ile mogę bezpiecznie wydać na nowy sprzęt?”.
- Odpowiedzi opierają się na danych z narzędzi (`get_balance`, `get_forecast`, `list_invoices`, `simulate`…), a nie na „wiedzy” modelu.
- W odpowiedzi może pojawić się wykres (prognoza przed / po, koszty wg kategorii).
- Z rozmowy może powstać nowa karta albo znane zdarzenie (np. „w lipcu zamykamy na 2 tygodnie”), które silnik uwzględni w prognozie.

### F4. Prognozy finansowe

Silnik, na którym stoi cała reszta.

**Na podstawie czego**
- Historia konta (wyciąg bankowy).
- Faktury: nieopłacone kosztowe (co musimy zapłacić) i sprzedażowe (co powinno wpłynąć, z poprawką na to, jak spóźnia się dany klient).
- Płatności cykliczne wykryte w historii: czynsz, pensje, podatki, składki, raty, subskrypcje.
- Znane przyszłe zdarzenia wpisane przez właściciela albo przez czat (zamknięcie lokalu, zatrudnienie, zakup sprzętu).
- Profil firmy: branża, liczba pracowników, sezonowość, bufor.

**Jak liczymy (prosto, ale uczciwie)**
- Przychody: średnia wg dnia tygodnia i miesiąca (sezonowość) z ostatnich miesięcy.
- Koszty stałe: z kalendarza płatności cyklicznych. Koszty zmienne: jako % przychodu.
- Faktury: w dniu terminu (albo z opóźnieniem typowym dla danego klienta).
- 3 scenariusze (pesymistyczny / bazowy / optymistyczny) z historycznych odchyleń; dają pasmo na wykresie i „pewność” na kartach.
- Horyzont: domyślnie 60 dni w widoku, liczymy do 90 dni. Dla MŚP najbardziej praktyczne są prognozy około 3-miesięczne.

**Wskaźniki z silnika**
- Najniższe saldo w horyzoncie i jego data; dni do luki płynności.
- Runway w miesiącach.
- Wolna gotówka = saldo − bufor − zobowiązania w horyzoncie.

**Symulacja „co jeśli”**
- Jedna funkcja `simulate(zmiany)`, z której korzystają karty (podgląd skutku), czat i wykres po decyzjach.

### F5. Outbox: maile z decyzji

- Decyzja może wymagać maila: do dostawcy (wcześniejsza płatność, prośba o przesunięcie terminu), klienta (przypomnienie o fakturze), księgowej, doradcy w banku.
- **AI pisze maila** na podstawie karty i decyzji; użytkownik może go przeczytać i poprawić.
- Każdy mail ma status: **NEEDS OK** (czeka na zgodę), **SCHEDULED** (wyjdzie o danej godzinie), **SENT**.
- Przycisk **„Review all”** do zatwierdzenia kilku maili naraz.
- Na hackathonie maile trafiają do **testowej skrzynki na klastrze** (np. Mailpit), więc na demo widać je na żywo.
- Agent pisze tylko do kontrahentów, których już znamy z faktur i przelewów (lista odbiorców).

### F6. Kontrola: poziomy autonomii, reguły i audit log

Wyzwanie wymaga rozróżnienia, **co agent robi sam, co rekomenduje, co wymaga zgody i co jest tylko symulowane**. Ta funkcja to pokazuje.

**Poziomy autonomii** (przełącznik w ustawieniach albo w nagłówku)

| **Tryb** | **Co robi agent** |
| --- | --- |
| Copilot | Tylko analizuje i rekomenduje; każda akcja wymaga zgody |
| 1-Click Approve | Przygotowuje akcję w całości; wystarczy jeden swipe albo klik |
| Auto (max X) | Sam wykonuje akcje poniżej progu kwoty; powyżej pyta |

**Klasyfikacja każdej akcji**
- **Analiza** (zawsze sam): czytanie danych, prognoza, wykrywanie problemów.
- **Rekomendacja**: karta z propozycją.
- **Wymaga zgody**: wszystko, co wychodzi na zewnątrz (mail, zlecenie w banku) albo przekracza próg.
- **Wykonanie: symulowane / dozwolone**: na hackathonie akcje bankowe są zawsze symulowane i oznaczone plakietką **SIMULATED**.

**Reguły (zakładka Rules)**
- Twarde zasady sprawdzane w kodzie (policy-as-code), np.:
  - zgoda człowieka powyżej X,
  - maile tylko do znanych odbiorców,
  - saldo po akcji nie może spaść poniżej bufora,
  - liczby tylko z silnika.
- **Swipe'y zamieniają się w reguły:** gdy właściciel kilka razy podejmie tę samą decyzję, agent proponuje regułę („Zawsze bierz rabat za wcześniejszą płatność powyżej 2%, jeśli bufor się utrzyma?”). Regułę można wyłączyć.

**Audit log (zakładka Ledger)**
- Lista wszystkich działań: godzina, ID reguły (np. `RULE-LIQ-01`), opis, status:
  - **SIMULATED**: akcja wykonana w symulatorze,
  - **PENDING**: czeka na zgodę,
  - **BLOCKED BY POLICY**: agent chciał coś zrobić, ale reguła zablokowała (np. „Auto-execution 35k exceeds 2,000 limit”).
- Wpisów nie da się edytować. Kliknięcie we wpis pokazuje pełne „dlaczego”.

**Symulator banku**
- Udawane API Commerzbanku: linia kredytowa, przesunięcie limitu, lokata, zabezpieczenie walutowe, przelew.
- Odpowiada „accepted (simulation)” z numerem referencyjnym; podgląd tego, co poszłoby do prawdziwego banku.

---

## Agenci: skąd biorą się karty

Wyzwanie wymaga co najmniej jednego pełnego przypadku użycia (dane → wytłumaczalna rekomendacja → decyzja użytkownika). Proponujemy **Liquidity** jako główny, a resztę jako dodatkowe źródła kart.

| **Agent** | **Czego pilnuje** | **Przykładowa karta** | **Prio** |
| --- | --- | --- | --- |
| Liquidity (z wyzwania) | Luki w prognozie, bufor, terminy dużych płatności | „Za 18 dni zabraknie 32 000 na pensje. Otworzyć krótką linię kredytową 35 000 (koszt ok. 420)?” | P1 |
| Payables: rabaty i terminy | Faktury kosztowe, rabaty za wcześniejszą płatność | „Zapłacić 21 dni wcześniej i dostać 4% rabatu?” | P1 |
| Collections | Zaległe faktury sprzedażowe | „Klient X spóźnia się 14 dni. Wysłać uprzejme przypomnienie?” | P2 |
| Margin guard | Ciche podwyżki cen u dostawców | „Dostawca podniósł ceny o 11%. Napisać o powrót do stawek z Q2?” | P2 |
| FX hedging (z wyzwania) | Płatności i faktury w obcej walucie | „Zabezpieczyć kurs na 6 kolejnych płatności w CHF?” | P2 |
| Tax (z wyzwania) | Terminy podatków i zaliczek | „Za 10 dni zaliczka na podatek. Odłożyć kwotę już teraz?” | P2 |
| Investment (z wyzwania) | Wolna gotówka ponad bufor | „Masz 20 000 ponad bufor do marca. Lokata 3-miesięczna?” | P2 |
| Invoices / KSeF | Spójność i podejrzane faktury | „Dostawca zmienił numer konta. Sprawdzić przed zapłatą?” | P3 |

Gdy agenci sobie przeczą (np. Investment chce ulokować pieniądze, których Liquidity potrzebuje za miesiąc), **koordynator** rozstrzyga i pokazuje tylko jedną spójną kartę.

## Dane wejściowe

- **Wyciąg bankowy:** import CSV (różne formaty banków), docelowo open banking (PSD2).
- **Faktury elektroniczne:** docelowo KSeF (PL) / XRechnung (DE); na hackathonie pliki przykładowe w tym samym kształcie.
- **Lista płac:** eksport z systemu kadrowego (kwoty i daty).
- **Profil firmy:** krótki onboarding (branża, liczba osób, sezonowość, bufor).
- **Wiele firm:** dane od organizatorów (Pizzeria Amalfi, `dane-przykladowe.md`) + wygenerowane dla profili z `firmy/`.
- Na hackathonie możemy przyjmować założenia co do dostępu do danych, ale w aplikacji pokazujemy je jawnie.

## Platforma (wymagania twarde, P0)

| **Wymaganie** | **Jak** |
| --- | --- |
| Backend na OpenShift | `oc new-app` + Route z HTTPS; frontend też na klastrze |
| Model open weights na RHOAI | vLLM (darmowy bonus); faworyt `qwen3-8b` (szczegóły w `openshift-ai.md`) |
| Aplikacja naprawdę woła model | Endpoint zgodny z OpenAI, adres i token z Secret, nie z repo |
| Widoczny dowód | Plakietka statusu modelu w nagłówku + logi wywołań |

---

## Łatwe dodatki (propozycje)

Rzeczy, które dużo dają w odbiorze, a nie są trudne. Trudność: **N** = kilka godzin lub mniej, **Ś** = około dnia.

| **Pomysł** | **Po co** | **Trudność** |
| --- | --- | --- |
| Ekran „Wszystko załatwione” po ostatniej karcie | Podsumowanie: ile decyzji, ile gotówki ochronione, co wyszło w Outboxie. Daje poczucie „fun” i zamknięcia | N |
| Licznik „Cash protected” | Jedna liczba pokazująca wartość aplikacji; jury od razu łapie | N |
| Plakietka statusu modelu | Pokazuje spełnienie wymagania twardego bez tłumaczenia | N |
| Skróty klawiszowe (strzałki) | Szybkie demo na laptopie | N |
| „Later” z wyborem terminu | Wieczorem / jutro / za tydzień zamiast samego „później” | N |
| Powód przy „Decline” (3 chipsy) | „Za drogo / zły moment / sam to załatwię”; agent uczy się, co proponować | N |
| Podpowiedzi pytań w czacie | Użytkownik nie musi wiedzieć, o co zapytać | N |
| Podgląd zlecenia do banku | Przy akcji SIMULATED przycisk „zobacz, co poszłoby do banku” | N |
| Tryb prosty / duża czcionka | „Innovations for all generations” | N |
| Jasny i ciemny motyw | Mamy już oba kierunki w szkicach | N |
| Mini-kalendarz najbliższych 7 dni | Lista: co wpływa i co wychodzi w tym tygodniu | N |
| Suwak „dzisiejszej daty” (tryb demo) | Przewijanie czasu na prezentacji: agent widzi tylko przeszłość, a my pokazujemy, że prognoza się sprawdziła | Ś |
| Przełącznik języka PL / EN | Demo po angielsku, użytkownik po polsku | Ś |
| Eksport podsumowania dla księgowej | PDF albo mail z decyzjami z tygodnia | Ś |
| Propozycja reguły po powtarzalnych swipe'ach | Najbardziej oryginalny element pomysłu | Ś |

## Priorytety (propozycja MVP)

| **Prio** | **Co** |
| --- | --- |
| P0 | Aplikacja na OpenShift + model na RHOAI przez vLLM, który aplikacja naprawdę woła |
| P1 | Silnik prognozy (F4), ekran główny z wykresem (F1), talia kart ze swipe (F2), „Ask why” z odwróceniem i czatem (F3), agent Liquidity + Payables, symulator banku, prosty audit log |
| P2 | Outbox z testową skrzynką (F5), poziomy autonomii i reguły (F6), kolejni agenci, łatwe dodatki, wybrane bonusy |
| P3 | Agent faktur / KSeF, prawdziwe konektory (PSD2, KSeF API), wiele osób w jednej firmie (współwłaściciel, księgowa) |

## Bonusy, które pasują do funkcji

Organizatorzy radzą 2–4. Szczegóły techniczne w `openshift-ai.md`.

| **Bonus** | **Pkt** | **Gdzie u nas** |
| --- | --- | --- |
| vLLM | 1 | Serwowanie modelu (i tak potrzebne) |
| Jupyter na RHOAI | 1 | Analiza danych przykładowych i strojenie prognozy |
| NeMo Guardrails | 2 | Druga warstwa reguł z F6 (pierwsza to kod) + demo „BLOCKED BY POLICY” |
| ogx + MCP | 1 | Narzędzia agentów jako MCP: `get_balance`, `get_forecast`, `simulate`, `draft_email`, `submit_to_bank` |
| MLflow | 1 | Ślad każdej decyzji agenta jako rozszerzony audit log |

## Scenariusz demo (szkic)

1. Ekran główny: wykres pokazuje lukę płynności za kilkanaście dni; „3 karty, ok. 2 minuty”.
2. Karta Liquidity: krótka linia kredytowa. „Ask why” → karta się odwraca → dane, mini-wykres, czat: „a jeśli przesunę płatność do dostawcy?”.
3. Swipe w prawo → SIMULATED w Ledgerze → wykres: linia przerywana nad zerem, licznik „Cash protected” rośnie.
4. Karta z rabatem za wcześniejszą płatność → swipe → mail w Outboxie → pojawia się w testowej skrzynce.
5. Próba akcji ponad limit autopilota → „BLOCKED BY POLICY”.
6. Ekran „Wszystko załatwione”.

Demo trzeba przećwiczyć, bo dobre przedstawienie jest równie ważne jak działanie.

## Otwarte pytania

- **Słupki na górze:** zostawić Cash, Runway, Team (morale), Trust (partnerzy) czy zamienić na same finansowe?
  - Opcja A, zostawiamy: Team i Trust liczone prostą heurystyką, np. Team z nadgodzin i terminowości pensji, Trust z terminowości płatności do dostawców. Bardziej „growo” i fun, ale trudniej obronić.
  - Opcja B, finansowe: np. Cash, Runway, Zobowiązania, Ryzyko. Wszystko z danych, łatwiej wytłumaczyć.
  - Do ustalenia w zespole.
- Horyzont na wykresie: 60 dni (jak w szkicu) czy 90 dni (bliżej rady o prognozach 3-miesięcznych)? Propozycja: przełącznik.
- Waluta i rynek w demo: aplikacja jest ogólna, ale przykładowe dane trzeba w jakiejś walucie pokazać (EUR w danych organizatorów, PLN w szkicu).
- Jakie stawki produktów Commerzbanku przyjąć w symulatorze (linia kredytowa, lokata, forward)? Zapytać na #Commerzbank.
- Backend: TypeScript (sugestia organizatorów), Python (łatwiej o prognozy) czy Quarkus (bonus)?
