"""Payee summary attributes are a nested list keyed by payee id, not names."""
import unittest
from datetime import date

from ha_sensors import build_payee_summary_attributes, map_ha_sensor_payload

# Names in fixtures are display labels only. Attribute keys must not use them.
TOP_LEVEL_KEYS = {
    "bill_cycle_date",
    "bill_total",
    "total_paid",
    "bill_balance",
    "bill_status",
    "month_range",
    "payees",
    "payee_names",
    "payees_by_id",
}


def _name_derived_keys(attrs):
    return [key for key in attrs if key not in TOP_LEVEL_KEYS]


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
                    "user_id": 7,
                    "name": "Alex",
                    "responsibility_percent": 50,
                    "amount_paid": 90.25,
                    "amount_due": 90.23,
                    "share_of_bill": 91.03,
                    "current_balance": -0.02,
                    "status": "overpaid",
                    "owing_since": None,
                },
                {
                    "user_id": 9,
                    "name": "Sam",
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
        first = attrs["payees"][0]
        second = attrs["payees"][1]
        self.assertEqual(first["user_id"], 7)
        self.assertEqual(first["name"], "Alex")
        self.assertEqual(first["amount_to_pay"], 0.0)
        self.assertEqual(first["days_owing"], 0)
        self.assertEqual(first["credit"], 0.02)
        self.assertEqual(second["user_id"], 9)
        self.assertEqual(second["balance"], 177.76)
        self.assertEqual(second["amount_to_pay"], 177.76)
        self.assertEqual(second["days_owing"], 82)
        self.assertEqual(second["owing_since"], "2026-08-14")
        self.assertEqual(attrs["payee_names"], ["Alex", "Sam"])
        self.assertEqual(attrs["payees_by_id"]["7"]["amount_to_pay"], 0.0)
        self.assertEqual(attrs["payees_by_id"]["9"]["amount_to_pay"], 177.76)
        self.assertEqual(attrs["payees_by_id"]["9"]["days_owing"], 82)
        self.assertIs(attrs["payees_by_id"]["7"], first)
        self.assertEqual(_name_derived_keys(attrs), [])

    def test_display_names_are_not_attribute_keys(self):
        """Configured names (including Brandon/Nigel) never become schema keys."""
        summary = {
            "bill_total": 100.0,
            "total_paid": 0.0,
            "bill_balance": 100.0,
            "bill_status": "unpaid",
            "payees": [
                {
                    "user_id": 1,
                    "name": "Brandon",
                    "responsibility_percent": 50,
                    "amount_paid": 0,
                    "amount_due": 50.0,
                    "status": "underpaid",
                    "owing_since": "2026-08-14",
                },
                {
                    "user_id": 2,
                    "name": "Nigel",
                    "responsibility_percent": 50,
                    "amount_paid": 0,
                    "amount_due": 50.0,
                    "status": "underpaid",
                    "owing_since": "2026-08-14",
                },
                {
                    "user_id": 3,
                    "name": "Pending Manual Verification",
                    "responsibility_percent": 0,
                    "amount_paid": 0,
                    "amount_due": 0,
                    "current_balance": 0,
                    "status": "paid",
                },
            ],
        }
        attrs = build_payee_summary_attributes(summary, today=date(2026, 11, 4))
        for forbidden in (
            "brandon_amount_due",
            "brandon_amount_to_pay",
            "brandon_days_owing",
            "nigel_amount_due",
            "nigel_amount_to_pay",
            "nigel_days_owing",
            "pending_manual_verification_amount_due",
            "pending_manual_verification_status",
        ):
            self.assertNotIn(forbidden, attrs)
        self.assertEqual(_name_derived_keys(attrs), [])
        self.assertEqual(list(attrs["payees_by_id"]), ["1", "2"])
        self.assertEqual(attrs["payees_by_id"]["1"]["name"], "Brandon")
        self.assertEqual(attrs["payees_by_id"]["2"]["amount_to_pay"], 50.0)

    def test_empty_summary_has_generic_containers(self):
        attrs = build_payee_summary_attributes(None)
        self.assertEqual(attrs["payees"], [])
        self.assertEqual(attrs["payees_by_id"], {})
        self.assertEqual(attrs["payee_names"], [])
        self.assertEqual(_name_derived_keys(attrs), [])

    def test_map_includes_every_matched_sensor_key(self):
        payload = map_ha_sensor_payload(
            {
                "account_balance": "$177.74",
                "bills": [
                    {"id": 2, "bill_total": "$317.99", "payments": []},
                    {"id": 1, "bill_total": "$271.93", "payments": []},
                ],
                "latest_payment": {"amount": "$90.25", "payee_name": "Alex"},
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
                        "user_id": 7,
                        "name": "Alex",
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
        data = payload["payee_summary_data"]
        self.assertIn("payees", data)
        self.assertIn("payees_by_id", data)
        self.assertEqual(data["payees_by_id"]["7"]["name"], "Alex")
        self.assertEqual(_name_derived_keys(data), [])


if __name__ == "__main__":
    unittest.main()
