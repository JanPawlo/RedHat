from decimal import Decimal

DEMO_PROFILE_NORTHSTAR = "northstar"
DEMO_PROFILE_PIZZERIA = "pizzeria"
DEFAULT_DEMO_PROFILE = DEMO_PROFILE_NORTHSTAR

DEMO_PROFILES = {
    DEMO_PROFILE_NORTHSTAR: {
        "company_name": "Northstar Logistics GmbH",
        "industry": "Courier and light freight",
        "owner_name": "Alex Morgan",
        "staff_count": 4,
        "balance": Decimal("25000.00"),
        "account_name": "Northstar Logistics Operating Account",
        "bank_name": "Synthetic demo bank",
        "planned_expense": {
            "label": "Replace delivery van 2",
            "amount": "18500.00",
            "days_from_now": 22,
            "movable": True,
        },
    },
    DEMO_PROFILE_PIZZERIA: {
        "company_name": "Pizzeria Amalfi",
        "industry": "Gastronomy",
        "owner_name": "Vincenzo Amalfi",
        "staff_count": 4,
        "balance": Decimal("33266.35"),
        "account_name": "Pizzeria Amalfi Operative Account",
        "bank_name": "Commerzbank Frankfurt",
        "planned_expense": {
            "label": "new pizza oven",
            "amount": "8500.00",
            "days_from_now": 22,
            "movable": True,
        },
    },
}

DEMO_PROFILE_FILES = {
    DEMO_PROFILE_NORTHSTAR: "northstar-logistics-bank-statement-2025.csv",
    DEMO_PROFILE_PIZZERIA: "pizzeria-amalfi-bank-statement-2025-v6.csv",
}

DEMO_PROFILE_CSV_DIRECTORY = "sample_data"
DEMO_COUNTRY = "DE"
DEMO_CURRENCY = "EUR"
