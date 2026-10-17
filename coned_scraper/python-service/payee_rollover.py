"""Payee rollover: how much of one bill carries into the next.

Portion owed for a bill is ``bill_total * responsibility_percent`` once.
Rollover mode adds a signed carry on top of that portion. It does not
multiply the carry by the responsibility percent again.

Carry sign (same dict ``apply_rollover_clear_at_bill`` already zeroes):
  positive = dollars still owed, added to the next portion
  negative = credit from an overpayment, subtracted from the next portion

A "balance cleared as of month" adjustment belongs in
``rollover_clear.apply_rollover_clear_at_bill``. Call it on the running
carry dict before ``settle_payee_bill``. Zeroing works for both signs.
Do not clamp a negative carry back to zero — that drops the credit and
makes the next bill charge the portion again.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from rollover_clear import apply_rollover_clear_at_bill


def portion_of_bill(bill_total: float, responsibility_percent: float) -> float:
    """This bill's portion only. Responsibility percent is applied once, here."""
    total = float(bill_total or 0.0)
    percent = float(responsibility_percent or 0.0)
    return round(total * (percent / 100.0), 2)


def amount_due_with_rollover(portion: float, incoming_rollover: float) -> float:
    """Portion plus the signed carry from earlier bills.

    ``incoming_rollover`` is already that payee's remaining dollars.
    It is not scaled by responsibility percent.
    """
    return round(float(portion or 0.0) + float(incoming_rollover or 0.0), 2)


def carry_to_next_bill(amount_due: float, amount_paid: float) -> float:
    """Signed dollars to add to the next bill's portion.

    ``amount_due`` already includes the incoming carry, so the result is
    the remaining position (due minus paid), not another copy of the portion.
    Positive = still owed. Negative = credit. Sub-cent residuals are zero.
    """
    carried = round(float(amount_due or 0.0) - float(amount_paid or 0.0), 2)
    if abs(carried) < 0.01:
        return 0.0
    return carried


def settle_payee_bill(
    portion: float,
    amount_paid: float,
    incoming_rollover: float,
) -> Dict[str, Any]:
    """One payee on one bill. Portion is unchanged; rollover changes amount due."""
    share = round(float(portion or 0.0), 2)
    incoming = round(float(incoming_rollover or 0.0), 2)
    paid = round(float(amount_paid or 0.0), 2)
    amount_due = amount_due_with_rollover(share, incoming)
    difference = round(paid - amount_due, 2)
    outgoing = carry_to_next_bill(amount_due, paid)

    status = "paid"
    if difference < -0.01:
        status = "underpaid"
    elif difference > 0.01:
        status = "overpaid"

    return {
        "share_of_bill": share,
        "amount_due": amount_due,
        "share_of_bill_cumulative": amount_due,
        "amount_paid": paid,
        "difference": difference,
        "rollover_from_previous": incoming,
        "current_balance": outgoing,
        "status": status,
    }


def walk_payee_rollover(
    bills: Sequence[Mapping[str, Any]],
    payees: Sequence[Mapping[str, Any]],
    clear_month: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Oldest-first chain. ``clear_month`` (YYYY-MM) zeros incoming carry once.

    Each bill mapping needs ``bill_total``, ``payments`` ({payee id: dollars}),
    and ``month`` (YYYY-MM) when a clear marker is used.
    """
    rollover_by_user = {p["id"]: 0.0 for p in payees}
    marker = clear_month
    rows: List[Dict[str, Any]] = []

    for bill in bills:
        rollover_by_user, marker = apply_rollover_clear_at_bill(
            rollover_by_user, bill.get("month"), marker
        )
        payments = bill.get("payments") or {}
        payee_rows = []
        for payee in payees:
            payee_id = payee["id"]
            incoming = float(rollover_by_user.get(payee_id) or 0.0)
            settled = settle_payee_bill(
                portion_of_bill(bill.get("bill_total") or 0.0, payee.get("responsibility_percent") or 0),
                payments.get(payee_id, 0.0),
                incoming,
            )
            rollover_by_user[payee_id] = settled["current_balance"]
            payee_rows.append(
                {
                    "user_id": payee_id,
                    "name": payee.get("name"),
                    "responsibility_percent": payee.get("responsibility_percent") or 0,
                    **settled,
                }
            )
        rows.append({"month": bill.get("month"), "payees": payee_rows})
    return rows
