# Dane przykładowe: Pizzeria Amalfi 2025

Źródła: `materials/sample-data/` (CSV, opis DOCX, wykres PNG). Opis firmy jako klienta: `firmy/pizzeria-amalfi.md`.

Organizatorzy piszą, że dane są **nieobowiązkowe** (można użyć własnych) i zostały wygenerowane przez AI, więc nie zawsze są w pełni realistyczne.

## Plik CSV

- `pizzeria-amalfi-bank-statement-2025-v6.csv`: wyciąg w formacie typowym dla niemieckiej bankowości online (podobnym do MT940).
- Separator `;`, wszystkie pola w cudzysłowach, przecinek dziesiętny (`-3200,00`), data w formacie `DD.MM.YY`.
- 1125 transakcji z okresu 01.01.2025–31.12.2025, posortowanych od najnowszej.
- Jedno konto: `DE89370400440532013000`.
- Kolumny: `Account Number`, `Booking Date`, `Value Date`, `Transaction Type`, `Payment Reference`, `Beneficiary/Payer`, `Counterparty Account`, `Bank Code`, `Amount`, `Currency`, `Info`.
- **Brak kolumny z saldem** i salda otwarcia. Saldo dzienne trzeba wyliczyć samemu.

### Typy transakcji (suma za rok)

| **Typ** | **Liczba** | **Suma** |
| --- | --- | --- |
| CREDIT CARD PAYOUT (Commerzbank Global Pay, 2× w tygodniu) | 143 | +435 319,19 EUR |
| CARD SETTLEMENT (DEBIT) (karty debetowe, codziennie) | 335 | +109 105,08 EUR |
| SUPPLIER PAYMENT (Asimex: jedzenie, Fattoria La Vino: wino) | 239 | −180 193,06 EUR |
| SALARY PAYMENT (4 osoby, 28. dnia miesiąca) | 48 | −103 200,00 EUR |
| GIRO CARD PAYMENT (Central Wholesale Market, codzienne zakupy) | 292 | −76 825,66 EUR |
| INTERNATIONAL WIRE TRANSFER (do Luigiego w Zurychu) | 12 | −50 000,04 **CHF** |
| RENT PAYMENT (1. dnia miesiąca) | 12 | −45 600,00 EUR |
| DIRECT DEBIT (składki społeczne, media, kwartalne podatki) | 32 | −45 100,00 EUR |
| TAX OFFICE TRANSFER (podatek od wynagrodzeń, 10. dnia) | 12 | −10 560,00 EUR |

## Scenariusz (z DOCX)

- Właściciel: Vincenzo Amalfi. Okres: cały 2025 rok.
- Wynagrodzenia netto (28. dnia): Vincenzo 3200 (wypłata właściciela), Yusuf Akcit (pizzaiolo) 2350, Rosa Pavese (kucharka) 2100, Vanessa Paradi (kelnerka, tymczasowo) 950. Razem 8600 EUR/mies.
- Podatki i składki:
  - podatek od wynagrodzeń + solidarnościowy: 880 EUR/mies., 10. dnia (Urząd Skarbowy Frankfurt),
  - ubezpieczenia społeczne: 2650 EUR/mies., 27. dnia (Techniker Krankenkasse),
  - zaliczka na podatek dochodowy (Einkommensteuer): 1150 EUR/kwartał (10.03, 10.06, 10.09, 10.12), liczona od ok. 30 000 EUR zysku z poprzedniego roku,
  - zaliczka na podatek od działalności (Gewerbesteuer): 225 EUR/kwartał (15.02, 15.05, 15.08, 15.11).
- Koszty stałe: czynsz 3800 EUR (1. dnia), media 650 EUR (10. dnia).
- Odpływ kapitału: cicha spółka w nowej restauracji brata, Luigiego, w Zurychu. Łącznie 50 000 CHF, czyli 4166,67 CHF/mies. 15. dnia, co daje ok. 4325–4375 EUR.
- Przychody: prawie wyłącznie karty. Debetowe rozliczane codziennie, kredytowe wypłacane 2× w tygodniu przez Commerzbank Global Pay. Gotówki prawie nie ma.
- Czerwiec: lokal zamknięty na 3 tygodnie, zero przychodów, a koszty idą dalej. Konto wpada w debet.
- Koniec roku: saldo +33 266,35 EUR.

## Wykres (PNG)

- Saldo dzienne w 2025 roku. Do maja waha się wokół 0–10 tys. EUR.
- Od czerwca (zamknięcie) spada w debet. Najniższy punkt to −22 097,60 EUR (03.07).
- Wraca na plus we wrześniu i rośnie do ok. 33,3 tys. EUR na koniec roku.

## Na co uważać

- Kwoty przelewów do Szwajcarii są w CSV zapisane w **CHF** (`Currency = CHF`), a nie w przeliczeniu na EUR, choć DOCX mówi o obciążeniu w EUR. Do salda trzeba je przeliczyć po kursie.
- DOCX i wykres podają różne wartości debetu: −20 098,69 EUR na koniec czerwca według DOCX i minimum −22 097,60 EUR 03.07 według wykresu. To nie musi być sprzeczność (inne daty), ale warto sprawdzić przy liczeniu salda.
- DOCX podaje nazwę pliku `pizzeria-amalfi-bank-statement-2025.csv`, a dostaliśmy wersję `-v6`.

## Do czego się nadaje (pod 4 przypadki użycia)

- **Liquidity agent**: debet w czerwcu da się przewidzieć z wyprzedzeniem (znane zamknięcie lokalu, stałe koszty) i zaproponować linię kredytową przed wakacjami.
- **FX hedging agent**: comiesięczne płatności w CHF to ryzyko walutowe (ok. 50 tys. CHF rocznie).
- **Tax agent**: znany harmonogram zaliczek kwartalnych i podatków miesięcznych. Zaliczka dochodowa liczona od ok. 30 tys. EUR zysku, a rok kończy się wyższym saldem, więc można pytać o korektę zaliczek.
- **Investment agent**: nadwyżka ok. 33 tys. EUR pod koniec roku, którą można ulokować, zostawiając bufor na sezon i czerwiec.
