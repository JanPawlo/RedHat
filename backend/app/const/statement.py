STATEMENT_FILE_EXTENSION = ".csv"
STATEMENT_MAX_MB = 5
STATEMENT_MAX_BYTES = STATEMENT_MAX_MB * 1024 * 1024
STATEMENT_ENCODINGS = ("utf-8-sig", "cp1252", "cp1250")

IMPORTED_ACCOUNT_NAME = "Imported Bank Account"
UNKNOWN_ACCOUNT_NUMBER = "UNKNOWN-ACCOUNT"
DEFAULT_CURRENCY = "EUR"
IMPORT_STATUS_SUCCESS = "success"

DEFAULT_CHF_EUR_RATE = "1.04"
THOUSANDS_ONLY_AMOUNT_PATTERN = r"^-?\d{1,3}(\.\d{3})+$"

STATEMENT_TEXT_MAX_LENGTHS = {
    "account_number": 64,
    "transaction_type": 64,
    "counterparty_name": 255,
    "counterparty_account": 64,
    "counterparty_bank_code": 32,
}
