from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4
import unittest

from app.models.transaction import Transaction
from app.services.cash_flow import (
    CashFlowValidationError,
    analyze_cash_flow,
    calculate_cash_flow,
    expenses_by_category,
    group_cash_flow,
    validate_transactions,
)


ACCOUNT_ID = uuid4()
OTHER_ACCOUNT_ID = uuid4()


def transaction(
    day: date,
    amount: Decimal | None,
    category: str | None = "revenue_pos",
    currency: str = "EUR",
    account_id=ACCOUNT_ID,
    **kwargs,
) -> Transaction:
    return Transaction(
        account_id=account_id,
        booking_date=day,
        value_date=kwargs.pop("value_date", day),
        amount=amount,
        currency=currency,
        amount_base_currency=amount if amount is not None else Decimal("0"),
        category=category,
        transaction_type=kwargs.pop("transaction_type", "CARD"),
        counterparty_name=kwargs.pop("counterparty_name", "Example Co"),
        payment_reference=kwargs.pop("payment_reference", "INV-1"),
        **kwargs,
    )


class CashFlowTests(unittest.TestCase):
    def test_totals_use_signed_amount_convention_and_decimal(self):
        rows = [
            transaction(date(2025, 5, 5), Decimal("100.00")),
            transaction(date(2025, 5, 5), Decimal("-30.00"), "supplier"),
            transaction(date(2025, 5, 6), Decimal("50.00")),
            transaction(date(2025, 5, 12), Decimal("-20.00"), "rent"),
        ]
        result = calculate_cash_flow(rows, date(2025, 5, 1), date(2025, 5, 31), ACCOUNT_ID, "EUR")
        self.assertEqual(result, {
            "inflows": Decimal("150.00"),
            "outflows": Decimal("50.00"),
            "net": Decimal("100.00"),
        })
        self.assertTrue(all(isinstance(value, Decimal) for value in result.values()))

    def test_daily_weekly_monthly_grouping_and_empty_day(self):
        rows = [
            transaction(date(2025, 5, 5), Decimal("100.00")),
            transaction(date(2025, 5, 5), Decimal("-30.00"), "supplier"),
            transaction(date(2025, 5, 6), Decimal("50.00")),
            transaction(date(2025, 5, 12), Decimal("-20.00"), "rent"),
        ]
        daily = group_cash_flow(rows, date(2025, 5, 5), date(2025, 5, 6), ACCOUNT_ID, "EUR", "day")
        self.assertEqual(daily, [
            {"period": "2025-05-05", "inflows": Decimal("100.00"), "outflows": Decimal("30.00"), "net": Decimal("70.00")},
            {"period": "2025-05-06", "inflows": Decimal("50.00"), "outflows": Decimal("0"), "net": Decimal("50.00")},
        ])
        weekly = group_cash_flow(rows, date(2025, 5, 5), date(2025, 5, 12), ACCOUNT_ID, "EUR", "week")
        self.assertEqual([row["period"] for row in weekly], ["2025-W19", "2025-W20"])
        monthly = group_cash_flow(rows, date(2025, 5, 1), date(2025, 5, 31), ACCOUNT_ID, "EUR", "month")
        self.assertEqual(monthly[0]["net"], Decimal("100.00"))

    def test_expenses_by_category_and_uncategorized(self):
        rows = [
            transaction(date(2025, 5, 1), Decimal("-30.00"), "supplier"),
            transaction(date(2025, 5, 2), Decimal("-20.00"), "rent"),
            transaction(date(2025, 5, 3), Decimal("-10.00"), None),
            transaction(date(2025, 5, 4), Decimal("10.00"), "supplier"),
        ]
        result = expenses_by_category(rows, date(2025, 5, 1), date(2025, 5, 31), ACCOUNT_ID, "EUR")
        by_category = {row["category"]: row for row in result}
        self.assertEqual(by_category["supplier"]["amount"], Decimal("30.00"))
        self.assertEqual(by_category["supplier"]["percentage"], Decimal("50"))
        self.assertEqual(by_category["rent"]["percentage"], Decimal("100") / Decimal("3"))
        self.assertEqual(by_category["uncategorized"]["amount"], Decimal("10.00"))
        self.assertTrue(all(isinstance(row["percentage"], Decimal) for row in result))

    def test_currency_or_account_mismatch_blocks_calculation(self):
        for row in (
            transaction(date(2025, 5, 1), Decimal("10.00"), currency="CHF"),
            transaction(date(2025, 5, 1), Decimal("10.00"), account_id=OTHER_ACCOUNT_ID),
        ):
            with self.assertRaises(CashFlowValidationError):
                calculate_cash_flow([row], date(2025, 5, 1), date(2025, 5, 31), ACCOUNT_ID, "EUR")

    def test_out_of_range_currency_mismatch_does_not_block_analysis_or_warn(self):
        rows = [
            transaction(date(2025, 5, 10), Decimal("100.00")),
            transaction(date(2025, 4, 30), Decimal("-25.00"), None, currency="CHF"),
        ]
        report = analyze_cash_flow(rows, date(2025, 5, 1), date(2025, 5, 31), ACCOUNT_ID, "EUR")
        self.assertEqual(report["totals"]["inflows"], Decimal("100.00"))
        self.assertEqual(report["totals"]["outflows"], Decimal("0"))
        self.assertEqual(report["warnings"], ())

    def test_in_range_currency_mismatch_blocks_analysis(self):
        rows = [
            transaction(date(2025, 5, 10), Decimal("100.00")),
            transaction(date(2025, 5, 15), Decimal("-25.00"), "supplier", currency="CHF"),
        ]
        with self.assertRaises(CashFlowValidationError) as raised:
            analyze_cash_flow(rows, date(2025, 5, 1), date(2025, 5, 31), ACCOUNT_ID, "EUR")
        self.assertTrue(any(issue.code == "currency_mismatch" for issue in raised.exception.errors))

    def test_other_category_warns_and_remains_in_expense_breakdown(self):
        rows = [
            transaction(date(2025, 5, 10), Decimal("-25.00"), "other"),
            transaction(date(2025, 5, 11), Decimal("-5.00"), "  OTHER "),
        ]
        report = analyze_cash_flow(rows, date(2025, 5, 1), date(2025, 5, 31), ACCOUNT_ID, "EUR")
        unclassified_warnings = [issue for issue in report["warnings"] if issue.code == "unclassified_category"]
        self.assertEqual(len(unclassified_warnings), 2)
        by_category = {row["category"]: row for row in report["expenses_by_category"]}
        self.assertEqual(by_category["other"]["amount"], Decimal("25.00"))
        self.assertEqual(by_category["OTHER"]["amount"], Decimal("5.00"))
        self.assertEqual(report["totals"]["outflows"], Decimal("30.00"))

    def test_missing_date_or_amount_is_blocking(self):
        rows = [
            transaction(date(2025, 5, 1), Decimal("10.00"), value_date=None),
            transaction(date(2025, 5, 2), None),
        ]
        result = validate_transactions(rows, ACCOUNT_ID, "EUR", "value_date")
        self.assertFalse(result.is_valid)
        self.assertEqual({issue.code for issue in result.errors}, {"missing_or_invalid_date", "missing_or_invalid_amount"})
        with self.assertRaises(CashFlowValidationError):
            calculate_cash_flow(rows, date(2025, 5, 1), date(2025, 5, 31), ACCOUNT_ID, "EUR", "value_date")

    def test_booking_date_and_value_date_select_filter_and_monthly_group(self):
        row = transaction(
            date(2025, 5, 31),
            Decimal("17.00"),
            value_date=date(2025, 6, 1),
        )

        booking_months = group_cash_flow(
            [row], date(2025, 5, 1), date(2025, 6, 30), ACCOUNT_ID, "EUR", "month",
            date_field="booking_date",
        )
        value_months = group_cash_flow(
            [row], date(2025, 5, 1), date(2025, 6, 30), ACCOUNT_ID, "EUR", "month",
            date_field="value_date",
        )
        self.assertEqual([item["net"] for item in booking_months], [Decimal("17.00"), Decimal("0")])
        self.assertEqual([item["net"] for item in value_months], [Decimal("0"), Decimal("17.00")])

        may_booking = calculate_cash_flow(
            [row], date(2025, 5, 1), date(2025, 5, 31), ACCOUNT_ID, "EUR",
            date_field="booking_date",
        )
        may_value = calculate_cash_flow(
            [row], date(2025, 5, 1), date(2025, 5, 31), ACCOUNT_ID, "EUR",
            date_field="value_date",
        )
        self.assertEqual(may_booking["inflows"], Decimal("17.00"))
        self.assertEqual(may_value["inflows"], Decimal("0"))

    def test_missing_booking_date_only_blocks_booking_date_mode(self):
        row = transaction(
            None,
            Decimal("17.00"),
            value_date=date(2025, 6, 1),
        )
        with self.assertRaises(CashFlowValidationError) as raised:
            calculate_cash_flow(
                [row], date(2025, 5, 1), date(2025, 6, 30), ACCOUNT_ID, "EUR",
                date_field="booking_date",
            )
        self.assertIn("missing_or_invalid_date", {issue.code for issue in raised.exception.errors})

        result = calculate_cash_flow(
            [row], date(2025, 5, 1), date(2025, 6, 30), ACCOUNT_ID, "EUR",
            date_field="value_date",
        )
        self.assertEqual(result["inflows"], Decimal("17.00"))

    def test_missing_value_date_only_blocks_value_date_mode(self):
        row = transaction(
            date(2025, 5, 31),
            Decimal("17.00"),
            value_date=None,
        )
        with self.assertRaises(CashFlowValidationError) as raised:
            calculate_cash_flow(
                [row], date(2025, 5, 1), date(2025, 6, 30), ACCOUNT_ID, "EUR",
                date_field="value_date",
            )
        self.assertIn("missing_or_invalid_date", {issue.code for issue in raised.exception.errors})

        result = calculate_cash_flow(
            [row], date(2025, 5, 1), date(2025, 6, 30), ACCOUNT_ID, "EUR",
            date_field="booking_date",
        )
        self.assertEqual(result["inflows"], Decimal("17.00"))

    def test_datetime_is_rejected_for_selected_date_field(self):
        row = transaction(
            datetime(2025, 5, 31, 12, 0),
            Decimal("17.00"),
            value_date=date(2025, 6, 1),
        )
        with self.assertRaises(CashFlowValidationError) as raised:
            calculate_cash_flow(
                [row], date(2025, 5, 1), date(2025, 6, 30), ACCOUNT_ID, "EUR",
                date_field="booking_date",
            )
        self.assertIn("missing_or_invalid_date", {issue.code for issue in raised.exception.errors})

    def test_possible_duplicates_are_warned_but_both_remain_in_totals(self):
        first = transaction(date(2025, 5, 1), Decimal("-20.00"), "supplier")
        second = transaction(date(2025, 5, 1), Decimal("-20.00"), "supplier")
        result = validate_transactions([first, second], ACCOUNT_ID, "EUR")
        self.assertTrue(result.is_valid)
        self.assertTrue(any(issue.code == "possible_duplicate" for issue in result.warnings))
        totals = calculate_cash_flow([first, second], date(2025, 5, 1), date(2025, 5, 1), ACCOUNT_ID, "EUR")
        self.assertEqual(totals["outflows"], Decimal("40.00"))

    def test_iso_week_year_boundary_and_analysis_warnings(self):
        rows = [
            transaction(date(2024, 12, 30), Decimal("10.00"), category=None),
            transaction(date(2025, 1, 5), Decimal("-3.00"), "rent"),
        ]
        weeks = group_cash_flow(rows, date(2024, 12, 30), date(2025, 1, 5), ACCOUNT_ID, "EUR", "week")
        self.assertEqual(len(weeks), 1)
        self.assertEqual(weeks[0]["period"], "2025-W01")
        self.assertEqual(weeks[0]["net"], Decimal("7.00"))
        report = analyze_cash_flow(rows, date(2024, 12, 30), date(2025, 1, 5), ACCOUNT_ID, "EUR")
        self.assertTrue(any(issue.code == "missing_category" for issue in report["warnings"]))

    def test_empty_expense_total_has_zero_decimal_percentage(self):
        rows = [transaction(date(2025, 5, 1), Decimal("5.00"))]
        self.assertEqual(expenses_by_category(rows, date(2025, 5, 1), date(2025, 5, 1), ACCOUNT_ID, "EUR"), [])


if __name__ == "__main__":
    unittest.main()
