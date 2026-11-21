"""
Mock open-banking (PSD2 / Berlin Group style) catalogue used by the Settings page.

Nothing here talks to a real bank: accounts, balances and transactions are generated
deterministically from these templates, relative to today's date.
"""

from decimal import Decimal

BANK_CONSENT_VALID_DAYS = 90
BANK_HISTORY_DAYS = 60
BANK_SOURCE = "mock_psd2"
BANK_TRANSACTION_INFO = "Imported from connected bank (mock PSD2)"
BANK_STATUS_CONNECTED = "connected"
BANK_STATUS_AVAILABLE = "available"

EVERY_DAY = 1
EVERY_WEEK = 7
EVERY_MONTH = 30

MOCK_BANKS = [
    {
        "id": "commerzbank-business",
        "name": "Commerzbank Business",
        "bic": "COBADEFFXXX",
        "country": "DE",
        "accounts": [
            {
                "iban": "DE27500400000123456701",
                "name": "Business Savings",
                "currency": "EUR",
                "opening_balance": Decimal("18500.00"),
                "transactions": [
                    {"every": EVERY_MONTH, "offset": 3, "amount": Decimal("1500.00"), "type": "TRANSFER", "category": "internal_transfer",
                     "counterparty": "Pizzeria Amalfi Operating Account", "reference": "Monthly reserve top-up"},
                    {"every": EVERY_MONTH, "offset": 28, "amount": Decimal("12.40"), "type": "INTEREST", "category": "interest",
                     "counterparty": "Commerzbank AG", "reference": "Savings interest"},
                ],
            },
        ],
    },
    {
        "id": "deutsche-bank",
        "name": "Deutsche Bank",
        "bic": "DEUTDEFFXXX",
        "country": "DE",
        "accounts": [
            {
                "iban": "DE45500700100987654300",
                "name": "Card Acquiring Account",
                "currency": "EUR",
                "opening_balance": Decimal("6240.00"),
                "transactions": [
                    {"every": EVERY_DAY, "offset": 0, "amount": Decimal("318.70"), "type": "CARD SETTLEMENT (CREDIT)", "category": "revenue_pos",
                     "counterparty": "Pizzeria Amalfi Customers (Credit)", "reference": "Daily credit card settlement"},
                    {"every": EVERY_WEEK, "offset": 4, "amount": Decimal("-1800.00"), "type": "TRANSFER", "category": "internal_transfer",
                     "counterparty": "Pizzeria Amalfi Operating Account", "reference": "Weekly sweep to operating account"},
                    {"every": EVERY_MONTH, "offset": 1, "amount": Decimal("-49.00"), "type": "FEE", "category": "bank_fee",
                     "counterparty": "Deutsche Bank AG", "reference": "Card terminal fee"},
                ],
            },
        ],
    },
    {
        "id": "ing-business",
        "name": "ING Business",
        "bic": "INGDDEFFXXX",
        "country": "DE",
        "accounts": [
            {
                "iban": "DE63500105170456789012",
                "name": "Supplier Payments",
                "currency": "EUR",
                "opening_balance": Decimal("3920.00"),
                "transactions": [
                    {"every": EVERY_WEEK, "offset": 1, "amount": Decimal("-642.30"), "type": "SEPA TRANSFER", "category": "supplier",
                     "counterparty": "Molino Caputo GmbH", "reference": "Flour and semolina delivery"},
                    {"every": EVERY_WEEK, "offset": 5, "amount": Decimal("1200.00"), "type": "TRANSFER", "category": "internal_transfer",
                     "counterparty": "Pizzeria Amalfi Operating Account", "reference": "Supplier budget top-up"},
                    {"every": EVERY_MONTH, "offset": 10, "amount": Decimal("-389.00"), "type": "SEPA DIRECT DEBIT", "category": "utility",
                     "counterparty": "Mainova AG", "reference": "Gas and electricity"},
                ],
            },
        ],
    },
    {
        "id": "wise-business",
        "name": "Wise Business",
        "bic": "TRWIBEB1XXX",
        "country": "BE",
        "accounts": [
            {
                "iban": "BE71967000000012",
                "name": "Swiss Franc Account",
                "currency": "CHF",
                "opening_balance": Decimal("2150.00"),
                "transactions": [
                    {"every": EVERY_MONTH, "offset": 15, "amount": Decimal("-860.00"), "type": "SEPA TRANSFER", "category": "supplier",
                     "counterparty": "Caseificio Ticino SA", "reference": "Mozzarella and burrata order"},
                    {"every": EVERY_WEEK, "offset": 2, "amount": Decimal("420.00"), "type": "TRANSFER", "category": "revenue_catering",
                     "counterparty": "Basel Catering Partners", "reference": "Catering event payment"},
                ],
            },
        ],
    },
]

