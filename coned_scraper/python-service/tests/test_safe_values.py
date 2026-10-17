"""Guards that used to turn ledger and bill-history requests into HTTP 500s."""
from datetime import datetime, timezone

from safe_values import aware_datetime, as_charge_map, charge_total, safe_float


def test_mixed_payment_dates_can_be_sorted():
    aware = datetime(2026, 3, 2, tzinfo=timezone.utc)
    naive = datetime(2026, 1, 5)
    keys = [aware_datetime(aware), aware_datetime(None), aware_datetime(naive)]
    ordered = sorted(keys)
    assert ordered[0] == aware_datetime(None)
    assert ordered[1] == aware_datetime(naive)
    assert ordered[2] == aware_datetime(aware)


def test_naive_and_aware_comparison_used_to_throw():
    try:
        datetime.min < datetime.now(timezone.utc)
        raised = False
    except TypeError:
        raised = True
    assert raised
    assert aware_datetime(None) < aware_datetime(datetime.now(timezone.utc))


def test_charge_json_string_and_non_dict_do_not_throw():
    assert charge_total('{"total": 12.5, "supply_charge": 1}') == 12.5
    assert charge_total(["not", "a", "map"]) == 0.0
    assert charge_total(None) == 0.0
    assert as_charge_map("not-json") == {}


def test_connection_errors_are_retryable():
    from safe_values import is_db_connection_error

    assert is_db_connection_error(RuntimeError("Environment variable not found: DATABASE_URL"))
    assert is_db_connection_error(RuntimeError("Can't reach database server at localhost:5432"))
    assert not is_db_connection_error(TypeError("can't compare offset-naive and offset-aware datetimes"))
    assert safe_float(None) is None
    assert safe_float("nope") is None
    assert safe_float(float("nan")) is None
    assert safe_float("18.25") == 18.25
