"""Payee summary attributes must be mappable lists, not only brandon_* keys."""
import unittest
from datetime import date

from ha_sensors import build_payee_summary_attributes, map_ha_sensor_payload, payee_slug


class PayeeSummaryAttributeTests(unittest.TestCase):
    def test_payees_list_has_balance_days_owing_and_amount_to_pay(self):
        summary = {
            "bill_cycle_date": "10/14/2026",
            "month_range": "SEP - OCT",
            "bill_total": 317.99,
            "total_paid": 140.25,
            "bill_balance": 177.74,
            "bill_status": "partial",
            "payees": [
                {
                    "name": "Brandon",
                    "responsibility_percent": 50,
                    "amount_paid": 90.25,
                    "amount_due": 90.23,
                    "share_of_bill": 91.03,
                    "current_balance": -0.02,
                    "status": "overpaid",
                    "owing_since": None,
                },
                {
                    "name": "Nigel",
                    "responsibility_percent": 50,
                    "amount_paid": 50.0,
                    "amount_due": 227.76,
                    "share_of_bill": 91.03,
                    "current_balance": 177.76,
                    "status": "underpaid",
                    "owing_since": "2026-08-14",
                },
            ],
        }
        attrs = build_payee_summary_attributes(summary, today=date(2026, 11, 4))
        self.assertEqual(attrs["bill_balance"], 177.74)
        self.assertEqual(len(attrs["payees"]), 2)
        brandon = attrs["payees"][0]
        nigel = attrs["payees"][1]
        self.assertEqual(brandon["name"], "Brandon")
        self.assertEqual(brandon["amount_to_pay"], 0.0)
        self.assertEqual(brandon["days_owing"], 0)
        self.assertEqual(brandon["credit"], 0.02)
        self.assertEqual(nigel["balance"], 177.76)
        self.assertEqual(nigel["amount_to_pay"], 177.76)
        self.assertEqual(nigel["days_owing"], 82)
        self.assertEqual(nigel["owing_since"], "2026-08-14")
        self.assertEqual(attrs["payee_names"], ["Brandon", "Nigel"])
        # Flattened keys stay for templates that already use them.
        self.assertEqual(attrs["brandon_amount_due"], 90.23)
        self.assertEqual(attrs["nigel_amount_to_pay"], 177.76)
        self.assertEqual(attrs["nigel_days_owing"], 82)

    def test_slug_strips_spaces_and_punctuation(self):
        self.assertEqual(payee_slug("Pending Manual Verification"), "pending_manual_verification")

    def test_map_includes_every_matched_sensor_key(self):
        payload = map_ha_sensor_payload(
            {
                "account_balance": "$177.74",
                "bills": [
                    {"id": 2, "bill_total": "$317.99", "payments": []},
                    {"id": 1, "bill_total": "$271.93", "payments": []},
                ],
                "latest_payment": {"amount": "$90.25", "payee_name": "Brandon"},
            },
            {"due_date": "Nov 09, 2026", "kwh_cost": 0.21, "kwh_used": 490},
            {
                "cost": 12.0,
                "usage_to_date_cost": 88.5,
                "reading": {"value": 1234.5},
                "forecast": {
                    "start_date": "2026-10-15",
                    "end_date": "2026-11-14",
                    "usage_to_date": 400,
                    "forecasted_usage": 490,
                },
            },
            {
                "bill_balance": 177.74,
                "bill_total": 317.99,
                "total_paid": 140.25,
                "bill_status": "partial",
                "payees": [
                    {
                        "name": "Brandon",
                        "responsibility_percent": 50,
                        "amount_paid": 90.25,
                        "amount_due": 90.23,
                        "status": "overpaid",
                    }
                ],
            },
            today=date(2026, 11, 4),
        )
        self.assertEqual(payload["account_balance"], 177.74)
        self.assertEqual(payload["latest_bill"], 317.99)
        self.assertEqual(payload["previous_bill"], 271.93)
        self.assertEqual(payload["last_payment"], 90.25)
        self.assertEqual(payload["due_date"], "Nov 09, 2026")
        self.assertEqual(payload["kwh_cost"], 0.21)
        self.assertEqual(payload["last_bill_kwh"], 490)
        self.assertEqual(payload["current_usage_cost"], 88.5)
        self.assertEqual(payload["current_meter_usage"], 1234.5)
        self.assertEqual(payload["current_cycle_usage"], 400)
        self.assertEqual(payload["forecasted_usage"], 490)
        self.assertEqual(payload["payee_summary"], 177.74)
        self.assertIn("payees", payload["payee_summary_data"])


if __name__ == "__main__":
    unittest.main()
