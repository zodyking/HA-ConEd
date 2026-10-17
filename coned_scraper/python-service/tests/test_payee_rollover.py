"""Rollover carries both unpaid amounts and overpayment credits.

Portion owed stays bill_total * responsibility percent. That percent is not
applied to the carry. A clear month still zeroes the incoming carry.
"""
import unittest

from payee_rollover import portion_of_bill, settle_payee_bill, walk_payee_rollover


ALICE = {"id": 1, "name": "Alice", "responsibility_percent": 60}
BOB = {"id": 2, "name": "Bob", "responsibility_percent": 40}

# $100 bills. Alice's portion is always $60, Bob's always $40.
BILLS = [
    {"month": "2024-01", "bill_total": 100.0, "payments": {1: 40.0, 2: 50.0}},
    {"month": "2024-02", "bill_total": 100.0, "payments": {1: 80.0, 2: 30.0}},
    {"month": "2024-03", "bill_total": 100.0, "payments": {1: 100.0, 2: 20.0}},
    {"month": "2024-04", "bill_total": 100.0, "payments": {1: 20.0, 2: 60.0}},
]


def _payee(rows, index, user_id):
    return next(p for p in rows[index]["payees"] if p["user_id"] == user_id)


class PayeeRolloverTests(unittest.TestCase):
    def test_portion_and_percent_ignore_carry(self):
        self.assertEqual(portion_of_bill(100.0, 60), 60.0)
        self.assertEqual(portion_of_bill(100.0, 40), 40.0)
        # A $20 debt is added in full. It is not multiplied by 60% again ($12).
        settled = settle_payee_bill(60.0, 0.0, 20.0)
        self.assertEqual(settled["share_of_bill"], 60.0)
        self.assertEqual(settled["amount_due"], 80.0)

    def test_overpayment_credit_reduces_the_next_bill(self):
        """$100 portion, pay $140. Next $100 bill is $60, not $100.

        Before: the $40 credit was dropped, so the next bill still showed $100
        and a $60 payment was $40 under. After: the next bill is $60 and $60
        settles it.
        """
        first = settle_payee_bill(100.0, 140.0, 0.0)
        self.assertEqual(first["share_of_bill"], 100.0)
        self.assertEqual(first["current_balance"], -40.0)
        second = settle_payee_bill(100.0, 60.0, first["current_balance"])
        self.assertEqual(second["rollover_from_previous"], -40.0)
        self.assertEqual(second["amount_due"], 60.0)
        self.assertEqual(second["share_of_bill_cumulative"], 60.0)
        self.assertEqual(second["status"], "paid")
        self.assertEqual(second["current_balance"], 0.0)

    def test_multi_bill_chain_carries_debt_and_credit(self):
        rows = walk_payee_rollover(BILLS, [ALICE, BOB])

        # January: Alice short $20. Bob over by $10.
        alice_jan = _payee(rows, 0, 1)
        bob_jan = _payee(rows, 0, 2)
        self.assertEqual(alice_jan["share_of_bill"], 60.0)
        self.assertEqual(bob_jan["share_of_bill"], 40.0)
        self.assertEqual(alice_jan["current_balance"], 20.0)
        self.assertEqual(bob_jan["current_balance"], -10.0)

        # February: Alice pays the $60 portion plus the $20 debt.
        # Bob's $10 credit makes $30 the amount due, and $30 settles it.
        # Before the fix Bob's credit was dropped, so $30 against a $40
        # portion was $10 under.
        alice_feb = _payee(rows, 1, 1)
        bob_feb = _payee(rows, 1, 2)
        self.assertEqual(alice_feb["amount_due"], 80.0)
        self.assertEqual(alice_feb["status"], "paid")
        self.assertEqual(alice_feb["current_balance"], 0.0)
        self.assertEqual(bob_feb["rollover_from_previous"], -10.0)
        self.assertEqual(bob_feb["share_of_bill"], 40.0)
        self.assertEqual(bob_feb["amount_due"], 30.0)
        self.assertEqual(bob_feb["status"], "paid")

        # March: Alice overpays the $60 portion by $40. Bob is short $20.
        alice_mar = _payee(rows, 2, 1)
        bob_mar = _payee(rows, 2, 2)
        self.assertEqual(alice_mar["current_balance"], -40.0)
        self.assertEqual(bob_mar["current_balance"], 20.0)

        # April: Alice owes $20 ($60 - $40 credit) and pays $20.
        # Before the fix April still showed $60, so $20 was $40 under.
        # Bob owes $60 ($40 + $20) and pays $60.
        alice_apr = _payee(rows, 3, 1)
        bob_apr = _payee(rows, 3, 2)
        self.assertEqual(alice_apr["share_of_bill"], 60.0)
        self.assertEqual(alice_apr["rollover_from_previous"], -40.0)
        self.assertEqual(alice_apr["amount_due"], 20.0)
        self.assertEqual(alice_apr["status"], "paid")
        self.assertEqual(bob_apr["amount_due"], 60.0)
        self.assertEqual(bob_apr["status"], "paid")
        self.assertEqual(bob_apr["current_balance"], 0.0)

    def test_underpayment_chain_still_adds_the_remainder(self):
        bills = [
            {"month": "2024-01", "bill_total": 100.0, "payments": {1: 40.0}},
            {"month": "2024-02", "bill_total": 100.0, "payments": {1: 100.0}},
            {"month": "2024-03", "bill_total": 100.0, "payments": {1: 70.0}},
            {"month": "2024-04", "bill_total": 100.0, "payments": {1: 100.0}},
        ]
        payees = [{"id": 1, "name": "Alex", "responsibility_percent": 100}]
        rows = walk_payee_rollover(bills, payees)
        self.assertEqual(_payee(rows, 0, 1)["current_balance"], 60.0)
        self.assertEqual(_payee(rows, 1, 1)["amount_due"], 160.0)
        self.assertEqual(_payee(rows, 1, 1)["current_balance"], 60.0)
        self.assertEqual(_payee(rows, 2, 1)["amount_due"], 160.0)
        self.assertEqual(_payee(rows, 2, 1)["current_balance"], 90.0)
        self.assertEqual(_payee(rows, 3, 1)["rollover_from_previous"], 90.0)
        self.assertEqual(_payee(rows, 3, 1)["amount_due"], 190.0)

    def test_coned_rollover_stays_with_the_payee_who_underpaid(self):
        """$200 cycle. A pays $100, B pays $50. Next ConEd bill is $250.

        The $50 is B's underpayment. It is not split, so A does not owe $125.
        """
        bills = [
            {
                "month": "2026-10",
                "cycle_date": "10/15/2026",
                "cycle_total": 200.0,
                "bill_total": 200.0,
                "payments": {1: 100.0, 2: 50.0},
            },
            {
                "month": "2026-11",
                "cycle_date": "11/15/2026",
                "bill_total": 250.0,
                "balance_from_previous": 50.0,
                "payments": {1: 100.0, 2: 100.0},
            },
        ]
        payees = [
            {"id": 1, "name": "Tenant A", "responsibility_percent": 50},
            {"id": 2, "name": "Tenant B", "responsibility_percent": 50},
        ]
        rows = walk_payee_rollover(bills, payees)
        tenant_a = _payee(rows, 1, 1)
        tenant_b = _payee(rows, 1, 2)
        self.assertEqual(tenant_a["share_of_bill"], 100.0)
        self.assertEqual(tenant_a["amount_due"], 100.0)
        self.assertEqual(tenant_a["portion_reasons"], ["$100 cycle charge", "$0 rollover balance"])
        self.assertEqual(tenant_a["current_balance"], 0.0)
        self.assertEqual(tenant_b["share_of_bill"], 100.0)
        self.assertEqual(tenant_b["amount_due"], 150.0)
        self.assertEqual(
            tenant_b["portion_reasons"],
            ["$100 cycle charge", "$50 rollover balance", "$50 from 10/15/26 underpayment"],
        )
        # B paid this cycle only, so October's $50 is still theirs next time.
        self.assertEqual(tenant_b["current_balance"], 50.0)
        self.assertEqual(_payee(rows, 0, 2)["current_balance"], 50.0)

    def test_unpaid_rollover_keeps_its_original_bill_date(self):
        bills = [
            {"month": "2026-10", "cycle_date": "10/15/2026", "cycle_total": 200.0, "payments": {1: 150.0}},
            {"month": "2026-11", "cycle_date": "11/15/2026", "cycle_total": 200.0, "payments": {1: 200.0}},
            {"month": "2026-12", "cycle_date": "12/15/2026", "cycle_total": 200.0, "payments": {1: 0.0}},
        ]
        payees = [{"id": 1, "name": "Tenant B", "responsibility_percent": 100}]
        rows = walk_payee_rollover(bills, payees)
        december = _payee(rows, 2, 1)
        self.assertEqual(
            december["portion_reasons"],
            ["$200 cycle charge", "$50 rollover balance", "$50 from 10/15/26 underpayment"],
        )
        self.assertEqual(december["amount_due"], 250.0)

    def test_switches_start_rollover_without_changing_earlier_bills(self):
        bills = [
            {"month": "2026-09", "cycle_date": "9/15/2026", "cycle_total": 200.0, "payments": {1: 50.0, 2: 100.0}},
            {"month": "2026-10", "cycle_date": "10/15/2026", "cycle_total": 200.0, "payments": {1: 100.0, 2: 50.0}},
            {"month": "2026-11", "cycle_date": "11/15/2026", "cycle_total": 200.0, "payments": {1: 100.0, 2: 100.0}},
            {"month": "2026-12", "cycle_date": "12/15/2026", "cycle_total": 200.0, "payments": {1: 100.0, 2: 100.0}},
            {"month": "2027-01", "cycle_date": "1/15/2027", "cycle_total": 200.0, "payments": {1: 0.0, 2: 0.0}},
        ]
        payees = [
            {"id": 1, "name": "Tenant A", "responsibility_percent": 50},
            {"id": 2, "name": "Tenant B", "responsibility_percent": 50},
        ]
        switches = [
            {"month": "2026-10", "mode": "rollover"},
            {"month": "2026-12", "mode": "bill_only"},
            {"month": "2027-01", "mode": "rollover"},
        ]
        rows = walk_payee_rollover(bills, payees, switches=switches)

        september = _payee(rows, 0, 2)
        self.assertFalse(rows[0]["uses_rollover"])
        self.assertIsNone(rows[0]["calculation_note"])
        self.assertEqual(september["amount_due"], 100.0)
        self.assertEqual(september["portion_reasons"][1], "Rollover balance not applied")
        self.assertEqual(september["current_balance"], 0.0)

        october = rows[1]
        self.assertTrue(october["uses_rollover"])
        self.assertEqual(october["calculation_note"]["title"], "Rollover starts October 2026")
        self.assertIn("earlier bills stay as they were", october["calculation_note"]["body"])
        self.assertEqual(_payee(rows, 1, 2)["rollover_from_previous"], 0.0)
        self.assertEqual(_payee(rows, 1, 2)["amount_due"], 100.0)
        self.assertEqual(_payee(rows, 1, 2)["current_balance"], 50.0)

        november_b = _payee(rows, 2, 2)
        self.assertEqual(november_b["amount_due"], 150.0)
        self.assertIn("$50 from 10/15/26 underpayment", november_b["portion_reasons"])

        december = rows[3]
        self.assertFalse(december["uses_rollover"])
        self.assertEqual(december["calculation_note"]["title"], "Bill only starts December 2026")
        self.assertEqual(_payee(rows, 3, 2)["amount_due"], 100.0)
        self.assertEqual(_payee(rows, 3, 2)["rollover_from_previous"], 0.0)

        january = rows[4]
        self.assertTrue(january["uses_rollover"])
        self.assertEqual(january["calculation_note"]["mode"], "rollover")
        self.assertEqual(_payee(rows, 4, 2)["rollover_from_previous"], 0.0)
        self.assertEqual(_payee(rows, 4, 2)["amount_due"], 100.0)

    def test_clear_month_zeroes_a_credit_then_later_bills_carry(self):
        rows = walk_payee_rollover(BILLS, [ALICE, BOB], clear_month="2024-02")
        uncleared = walk_payee_rollover(BILLS, [ALICE, BOB])

        self.assertEqual(_payee(rows, 0, 1)["current_balance"], 20.0)
        self.assertEqual(_payee(rows, 0, 2)["current_balance"], -10.0)
        # February incoming debt and credit are both cleared.
        self.assertEqual(_payee(rows, 1, 1)["rollover_from_previous"], 0.0)
        self.assertEqual(_payee(rows, 1, 1)["amount_due"], 60.0)
        self.assertEqual(_payee(rows, 1, 2)["rollover_from_previous"], 0.0)
        self.assertEqual(_payee(rows, 1, 2)["amount_due"], 40.0)
        # Alice paid $80 against a cleared $60 portion, so $20 credit carries to March.
        self.assertEqual(_payee(rows, 2, 1)["rollover_from_previous"], -20.0)
        self.assertEqual(_payee(rows, 2, 1)["amount_due"], 40.0)
        self.assertNotEqual(
            _payee(rows, 1, 2)["amount_due"],
            _payee(uncleared, 1, 2)["amount_due"],
        )


if __name__ == "__main__":
    unittest.main()
