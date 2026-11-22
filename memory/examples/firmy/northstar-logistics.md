# Northstar Logistics GmbH

Fictional transport company used to test the app with data outside the Pizzeria Amalfi scenario.

## Company profile

- Country and currency: Germany, EUR.
- Size: four people (three drivers and an owner-manager), operating three delivery vans.
- Business: regional courier and light freight services.
- Financial period: 2025.
- Statement: `backend/sample_data/northstar-logistics-bank-statement-2025.csv`.

## Dataset

- 1,125 synthetic transactions from 2025-01-01 through 2025-12-31, in the same semicolon-separated German bank CSV layout as the Pizzeria sample.
- Includes recurring payroll, payroll tax, social contributions, depot rent, vehicle leases, utilities and software, plus customer transfers, fuel, tolls, repairs, vehicle parts and administration costs.
- The parser categorizes business customer transfers as `revenue_b2b` and separates vehicle fuel, tolls, maintenance and parts from general suppliers.
- Four monthly payroll payments total EUR 8,600, matching the Pizzeria example's team size and payroll scale.
- Every company, counterparty and account identifier is fictional. The account number is a placeholder, not a usable IBAN.
- The file has no opening-balance column. Net transaction movement is EUR 25,000, so importing it into a new zero-balance account gives an inferred closing balance of EUR 25,000.
- `CUSTOMER REVENUE TRANSFER` is categorized as `revenue_pos` by the current parser because its generic revenue detector uses that category for revenue. That label is not semantically precise for B2B transfers.

## Demo seed

- Northstar is the default demo profile (`SEED_PROFILE=northstar`). Its CSV is packaged under `backend/sample_data/` and is included in Docker builds.
- A fresh database is seeded at API startup. Existing company data is preserved; use the authenticated demo reset endpoint or `/demo-reset` in the app to replace it with the selected demo profile. User accounts remain.
- The account snapshot is EUR 25,000 as of 2025-12-31, matching the net movement in the statement (there is no opening balance in the CSV).
- The seed adds synthetic open vehicle-maintenance and parts invoices, plus a late-paying business customer, so the invoice and receivables cards have transport-relevant examples.
- The paid-invoice history links to the customer's existing statement transactions; it does not add extra cash movements or change the EUR 25,000 statement balance.
- Set `SEED_PROFILE=pizzeria` to use the organizers' example. A custom `SEED_CSV_PATH` must match the selected profile's company and account data.
