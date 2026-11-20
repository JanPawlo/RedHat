# Pizzeria Amalfi

A company from the organizers' official sample data. Full data analysis: `examples/dane-przykladowe.md`.

## Basic information

- Industry: food service (pizzeria), Germany (Frankfurt am Main)
- Legal form: not given; probably a sole proprietorship (owner's draws, Einkommensteuer and Gewerbesteuer)
- Listed / private company: private
- Number of employees: 4 people including the owner
- Positions: owner (Vincenzo Amalfi), pizzaiolo, cook, waitress (temporary)
- Annual revenue (approximate): about 544k EUR of card inflows in 2025

## How it operates

- Restaurant; customers pay almost exclusively by card
- Main suppliers and costs: Asimex Wholesale (food, ingredients from Italy), Fattoria La Vino (wine, weekly), Central Wholesale Market (vegetables, every morning), rent 3800 EUR, payroll 8600 EUR net per month
- Seasonality: 3-week closure in June (zero revenue); strong Q3 and Q4

## Invoices

- There are no invoices in the data, only transfers with invoice numbers in the reference (`Invoice AS-…`, `Invoice FLV-…`)
- Typical amounts: Asimex and Fattoria about 600–900 EUR per payment, wholesale market about 250–310 EUR per day

## Finances

- One account at Commerzbank; balance between about −22k EUR (early July) and about +40k EUR (December)
- Loans, leases: none in the data
- Biggest financial problems: overdraft after the June closure; constant outflow of about 4.3k EUR per month to Switzerland (50k CHF per year, exchange rate risk)

## Scenarios for the project

- What frauds or invoice inconsistencies it may be exposed to: (to be filled in)
- What the owner would ask the chatbot: "Will I get through June without an overdraft?", "How much can I safely transfer to Luigi?", "What should I do with the year-end surplus?"
- What forecasts would be useful for it: balance x days ahead, taking into account the June closure, the CHF exchange rate and tax deadlines
