"""Boundary tests for an undoable rollover clear.

The chain uses payee_rollover.walk_payee_rollover, which is the landed
carry (debt and credit) plus apply_rollover_clear_at_bill at each bill.
"""
import unittest

from payee_rollover import walk_payee_rollover
from rollover_clear import (
    apply_rollover_clear,
    apply_rollover_clear_at_bill,
    format_clear_month_label,
    marker_from_setting,
    normalize_clear_month,
)


PAYEES = [{"id": 1, "name": "Alex", "responsibility_percent": 100}]
BILLS = [
    {"month": "2024-01", "bill_total": 100.0, "payments": {1: 40.0}},
    {"month": "2024-02", "bill_total": 100.0, "payments": {1: 100.0}},
    {"month": "2024-03", "bill_total": 100.0, "payments": {1: 70.0}},
    {"month": "2024-04", "bill_total": 100.0, "payments": {1: 100.0}},
]


def _row(rows, index):
    return rows[index]["payees"][0]


class RolloverClearBoundaryTests(unittest.TestCase):
    def test_normalize_and_label(self):
        self.assertEqual(normalize_clear_month("2024-3"), "2024-03")
        self.assertEqual(normalize_clear_month("03/15/2024"), "2024-03")
        self.assertIsNone(normalize_clear_month("2024-13"))
        self.assertIsNone(normalize_clear_month(None))
        self.assertEqual(format_clear_month_label("2024-03"), "March 2024")

    def test_undo_payload_removes_marker(self):
        self.assertEqual(marker_from_setting({"month": "2024-03"}), "2024-03")
        self.assertIsNone(marker_from_setting({"month": None}))
        self.assertIsNone(marker_from_setting(None))

    def test_bills_before_clear_keep_history_and_later_bills_carry_from_zero(self):
        original = walk_payee_rollover(BILLS, PAYEES, None)
        cleared = walk_payee_rollover(BILLS, PAYEES, "2024-03")

        self.assertEqual(_row(original, 0)["rollover_from_previous"], 0.0)
        self.assertEqual(_row(original, 0)["current_balance"], 60.0)
        self.assertEqual(_row(original, 1)["rollover_from_previous"], 60.0)
        self.assertEqual(_row(original, 1)["current_balance"], 60.0)
        self.assertEqual(_row(original, 2)["rollover_from_previous"], 60.0)
        self.assertEqual(_row(original, 2)["amount_due"], 160.0)
        self.assertEqual(_row(original, 2)["current_balance"], 90.0)
        self.assertEqual(_row(original, 3)["rollover_from_previous"], 90.0)

        # January and February are unchanged.
        self.assertEqual(cleared[0], original[0])
        self.assertEqual(cleared[1], original[1])

        # March's incoming rollover is zero. April carries March's new shortfall.
        self.assertEqual(_row(cleared, 2)["rollover_from_previous"], 0.0)
        self.assertEqual(_row(cleared, 2)["amount_due"], 100.0)
        self.assertEqual(_row(cleared, 2)["current_balance"], 30.0)
        self.assertEqual(_row(cleared, 3)["rollover_from_previous"], 30.0)
        self.assertEqual(_row(cleared, 3)["amount_due"], 130.0)
        self.assertEqual(_row(cleared, 3)["current_balance"], 30.0)

    def test_undo_restores_previous_rollover_chain(self):
        original = walk_payee_rollover(BILLS, PAYEES, None)
        cleared = walk_payee_rollover(BILLS, PAYEES, "2024-03")
        undone = walk_payee_rollover(BILLS, PAYEES, marker_from_setting({"month": None}))
        self.assertNotEqual(
            _row(cleared, 2)["rollover_from_previous"],
            _row(original, 2)["rollover_from_previous"],
        )
        self.assertEqual(undone, original)

    def test_gap_month_clears_the_next_bill(self):
        bills = [
            {"month": "2024-01", "bill_total": 100.0, "payments": {1: 40.0}},
            {"month": "2024-02", "bill_total": 100.0, "payments": {1: 100.0}},
            {"month": "2024-04", "bill_total": 100.0, "payments": {1: 80.0}},
        ]
        cleared = walk_payee_rollover(bills, PAYEES, "2024-03")
        self.assertEqual(_row(cleared, 1)["current_balance"], 60.0)
        self.assertEqual(_row(cleared, 2)["rollover_from_previous"], 0.0)
        self.assertEqual(_row(cleared, 2)["current_balance"], 20.0)

    def test_apply_does_not_zero_months_before_the_marker(self):
        self.assertEqual(apply_rollover_clear(60.0, "2024-02", "2024-03"), 60.0)
        self.assertEqual(apply_rollover_clear(60.0, "2024-03", "2024-03"), 0.0)

    def test_marker_is_consumed_so_later_months_can_carry(self):
        balances = {1: 60.0, 2: 15.0}
        at_boundary, marker = apply_rollover_clear_at_bill(balances, "2024-03", "2024-03")
        self.assertEqual(at_boundary, {1: 0.0, 2: 0.0})
        self.assertIsNone(marker)
        later, still = apply_rollover_clear_at_bill({1: 30.0}, "2024-04", marker)
        self.assertEqual(later[1], 30.0)
        self.assertIsNone(still)


if __name__ == "__main__":
    unittest.main()
