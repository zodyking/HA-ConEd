"""Payee rollover: how much of one bill carries into the next.

Responsibility percent applies to this cycle's new charges only
(detailed billing history "cycle total"), not to Con Edison's rolled-over
balance. That rolled-over balance is the earlier underpayment, and it stays
with the payee who created it.

Carry sign (same dict ``apply_rollover_clear_at_bill`` already zeroes):
  positive = dollars still owed, added to the next cycle portion
  negative = credit from an overpayment, subtracted from the next cycle portion

A "balance cleared as of month" adjustment belongs in
``rollover_clear.apply_rollover_clear_at_bill``. Call it on the running
carry dict before ``settle_payee_bill``. Zeroing works for both signs.
Do not clamp a negative carry back to zero — that drops the credit and
makes the next bill charge the portion again.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from rollover_clear import (
    apply_rollover_clear_at_bill,
    format_clear_month_label,
    normalize_clear_month,
)


def portion_of_bill(cycle_total: float, responsibility_percent: float) -> float:
    """This cycle's new charges only. Responsibility percent is applied once, here.

    ``cycle_total`` is the billing-period charges, not the Con Edison bill
    total that already includes a previous unpaid balance.
    """
    total = float(cycle_total or 0.0)
    percent = float(responsibility_percent or 0.0)
    return round(total * (percent / 100.0), 2)


def charge_to_split(bill: Mapping[str, Any]) -> float:
    """Dollars to divide by responsibility. Prefer the cycle total.

    A bill total that already includes ``balance_from_previous`` is reduced
    by that rollover so the unpaid amount is not split across every payee.
    """
    if bill.get("cycle_total") is not None:
        return round(float(bill.get("cycle_total") or 0.0), 2)
    total = float(bill.get("bill_total") or 0.0)
    if bill.get("balance_from_previous") is not None:
        return round(total - float(bill.get("balance_from_previous") or 0.0), 2)
    return round(total, 2)


def format_cycle_label(value: Any) -> Optional[str]:
    """Bill cycle date as M/D/YY, matching the ledger's underpayment notes."""
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return f"{value.month}/{value.day}/{value.year % 100:02d}"
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text[:10], fmt).date()
            return f"{parsed.month}/{parsed.day}/{parsed.year % 100:02d}"
        except ValueError:
            continue
    return text


def money_label(amount: float) -> str:
    value = round(float(amount or 0.0), 2)
    if abs(value - round(value)) < 0.001:
        return f"${value:.0f}"
    return f"${value:.2f}"


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


def _copy_items(items: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    copied = []
    for item in items or []:
        amount = round(float(item.get("amount") or 0.0), 2)
        if abs(amount) < 0.01:
            continue
        origin = str(item.get("origin") or "a previous bill")
        copied.append({"amount": amount, "origin": origin})
    return copied


def _sum_items(items: Sequence[Mapping[str, Any]]) -> float:
    return round(sum(float(item.get("amount") or 0.0) for item in items), 2)


def portion_reason_lines(items: Sequence[Mapping[str, Any]]) -> List[str]:
    """Origin of each carried underpayment or credit."""
    lines = []
    for item in _copy_items(items):
        amount = item["amount"]
        origin = item["origin"]
        if amount > 0:
            lines.append(f"{money_label(amount)} from {origin} underpayment")
        else:
            # A leading minus so the lines add up to the amount owed.
            lines.append(f"-{money_label(abs(amount))} credit from {origin} overpayment")
    return lines


def portion_breakdown_lines(
    cycle_portion: float,
    incoming_items: Sequence[Mapping[str, Any]],
    use_rollover: bool,
) -> List[str]:
    """Cycle charge plus rollover, so the owed amount can be read as a sum."""
    lines = [f"{money_label(cycle_portion)} cycle charge"]
    if not use_rollover:
        lines.append("Rollover balance not applied")
        return lines
    details = portion_reason_lines(incoming_items)
    if details:
        # The dated lines already add up to the rollover. Do not also print the total.
        lines.extend(details)
        return lines
    incoming = _sum_items(incoming_items)
    if incoming < -0.009:
        lines.append(f"{money_label(abs(incoming))} rollover credit")
    else:
        lines.append(f"{money_label(max(incoming, 0.0))} rollover balance")
    return lines


def normalize_switches(raw: Any) -> List[Dict[str, str]]:
    """Unique month switches, oldest first. Mode is bill_only or rollover."""
    items = raw.get("switches") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return []
    by_month: Dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        month = normalize_clear_month(item.get("month"))
        mode = item.get("mode")
        if not month or mode not in {"bill_only", "rollover"}:
            continue
        by_month[month] = mode
    return [{"month": month, "mode": by_month[month]} for month in sorted(by_month)]


def mode_for_month(month: Optional[str], switches: Sequence[Mapping[str, str]]) -> str:
    """Bill only until the first switch, then the latest switch at or before this month."""
    bill_month = normalize_clear_month(month)
    mode = "bill_only"
    if not bill_month:
        return mode
    for switch in normalize_switches(list(switches)):
        if switch["month"] <= bill_month:
            mode = switch["mode"]
        else:
            break
    return mode


def calculation_switch_note(mode: str, month: Optional[str]) -> Dict[str, str]:
    """Ledger note for the first bill of a calculation method."""
    label = format_clear_month_label(month) or "this bill"
    if mode == "rollover":
        return {
            "mode": "rollover",
            "month": month or "",
            "label": label,
            "title": f"Rollover starts {label}",
            "body": (
                "Counting starts with this bill, so earlier bills stay as they were. "
                "Each payee owes their share of this cycle's new charges, plus any unpaid "
                "amount from this point forward. Rollover fits a household that needs the "
                "unpaid balance carried onto the next bill when someone cannot pay in full."
            ),
        }
    return {
        "mode": "bill_only",
        "month": month or "",
        "label": label,
        "title": f"Bill only starts {label}",
        "body": (
            "From this bill on, each payee owes only their share of this cycle's new charges. "
            "An unpaid amount is not added to the next bill. Bill only fits a household where "
            "everyone pays their share in full each month."
        ),
    }


def _apply_funds(debts: List[Dict[str, Any]], funds: float) -> Tuple[List[Dict[str, Any]], float]:
    """Pay the oldest underpayment first. Leftover funds are returned."""
    remaining: List[Dict[str, Any]] = []
    left = round(float(funds or 0.0), 2)
    for debt in debts:
        amount = debt["amount"]
        if left >= amount - 0.009:
            left = round(left - amount, 2)
        elif left > 0.009:
            remaining.append({"amount": round(amount - left, 2), "origin": debt["origin"]})
            left = 0.0
        else:
            remaining.append(dict(debt))
    return remaining, round(max(left, 0.0), 2)


def next_carry_items(
    incoming: Sequence[Mapping[str, Any]],
    cycle_portion: float,
    amount_paid: float,
    origin: str,
) -> List[Dict[str, Any]]:
    """Open items after this bill. Unpaid cycle charges are dated to this bill.

    A prior credit retires the oldest underpayment, then this cycle. Cash paid
    on this bill covers this cycle first, then the oldest underpayment, so an
    unpaid October balance stays labeled October until it is paid.
    """
    items = _copy_items(incoming)
    debts = [item for item in items if item["amount"] > 0]
    credit = round(-sum(item["amount"] for item in items if item["amount"] < 0), 2)
    debts, credit = _apply_funds(debts, credit)

    cycle_left = round(max(float(cycle_portion or 0.0), 0.0), 2)
    if credit > 0.009:
        if credit >= cycle_left - 0.009:
            credit = round(credit - cycle_left, 2)
            cycle_left = 0.0
        else:
            cycle_left = round(cycle_left - credit, 2)
            credit = 0.0

    pay_left = round(float(amount_paid or 0.0), 2)
    if pay_left >= cycle_left - 0.009:
        pay_left = round(pay_left - cycle_left, 2)
        cycle_left = 0.0
    elif pay_left > 0.009:
        cycle_left = round(cycle_left - pay_left, 2)
        pay_left = 0.0
    debts, pay_left = _apply_funds(debts, pay_left)

    outgoing = list(debts)
    label = origin or "a previous bill"
    if cycle_left > 0.009:
        outgoing.append({"amount": round(cycle_left, 2), "origin": label})
    surplus = round(pay_left + credit, 2)
    if surplus > 0.009:
        outgoing.append({"amount": round(-surplus, 2), "origin": label})
    return outgoing


def _zero_carry(
    payees: Sequence[Mapping[str, Any]],
) -> Tuple[Dict[Any, float], Dict[Any, List[Dict[str, Any]]]]:
    return (
        {payee["id"]: 0.0 for payee in payees},
        {payee["id"]: [] for payee in payees},
    )


def settle_bill_payees(
    payees: Sequence[Mapping[str, Any]],
    payments: Mapping[Any, float],
    rollover_by_user: Dict[Any, float],
    items_by_user: Dict[Any, List[Dict[str, Any]]],
    cycle_total: float,
    origin: str,
    month: Optional[str],
    clear_marker: Optional[str],
    use_rollover: bool = True,
    reset_incoming: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[Any, float], Dict[Any, List[Dict[str, Any]]], Optional[str]]:
    """Settle every payee on one bill. Percent applies to ``cycle_total`` only.

    ``reset_incoming`` drops the carry before this bill (a new rollover span,
    or a bill-only bill). Bill-only bills also drop whatever would have
    carried out, so a later rollover span starts from zero.
    """
    prior_marker = clear_marker
    rollover_by_user, clear_marker = apply_rollover_clear_at_bill(
        rollover_by_user, month, clear_marker
    )
    if (prior_marker and not clear_marker) or reset_incoming or not use_rollover:
        rollover_by_user, items_by_user = _zero_carry(payees)

    rows = []
    new_rollover = dict(rollover_by_user)
    new_items = {payee["id"]: _copy_items(items_by_user.get(payee["id"]) or []) for payee in payees}
    for payee in payees:
        payee_id = payee["id"]
        incoming_items = new_items.get(payee_id) or []
        incoming = float(new_rollover.get(payee_id) or 0.0)
        if abs(incoming - _sum_items(incoming_items)) >= 0.02 and incoming_items:
            incoming_items = [{"amount": incoming, "origin": "a previous bill"}]
        elif not incoming_items and abs(incoming) >= 0.01:
            incoming_items = [{"amount": incoming, "origin": "a previous bill"}]
        portion = portion_of_bill(cycle_total, payee.get("responsibility_percent") or 0)
        paid = float((payments or {}).get(payee_id, 0.0) or 0.0)
        settled = settle_payee_bill(portion, paid, _sum_items(incoming_items) if incoming_items else incoming)
        carried = next_carry_items(incoming_items, portion, paid, origin)
        new_items[payee_id] = carried
        new_rollover[payee_id] = settled["current_balance"]
        rows.append(
            {
                "user_id": payee_id,
                "name": payee.get("name"),
                "responsibility_percent": payee.get("responsibility_percent") or 0,
                "uses_rollover": use_rollover,
                "portion_reasons": portion_breakdown_lines(portion, incoming_items, use_rollover),
                **settled,
            }
        )
    if not use_rollover:
        new_rollover, new_items = _zero_carry(payees)
    return rows, new_rollover, new_items, clear_marker


def span_flags(
    month: Optional[str],
    switches: Sequence[Mapping[str, str]],
    previous_mode: Optional[str],
) -> Tuple[bool, bool, Optional[Dict[str, str]], Optional[str]]:
    """Return use_rollover, reset_incoming, note, and the mode to remember.

    An empty timeline is bill only for every bill, with no ledger note.
    """
    timeline = normalize_switches(list(switches))
    if not timeline:
        return False, True, None, previous_mode
    use_rollover = mode_for_month(month, timeline) == "rollover"
    mode = "rollover" if use_rollover else "bill_only"
    started = _timeline_started(month, timeline)
    note = None
    reset = (not use_rollover) or previous_mode != "rollover"
    if started and (previous_mode is None or previous_mode != mode):
        note = calculation_switch_note(mode, month)
        reset = True
    return use_rollover, reset, note, (mode if started else previous_mode)


def _timeline_started(month: Optional[str], switches: Sequence[Mapping[str, str]]) -> bool:
    bill_month = normalize_clear_month(month)
    if not bill_month:
        return False
    return any(switch["month"] <= bill_month for switch in switches)


def walk_payee_rollover(
    bills: Sequence[Mapping[str, Any]],
    payees: Sequence[Mapping[str, Any]],
    clear_month: Optional[str] = None,
    switches: Optional[Sequence[Mapping[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """Oldest-first chain.

    ``clear_month`` zeros incoming carry once and keeps rollover on every bill.
    ``switches`` is a timeline of ``bill_only`` and ``rollover`` starts. Bills
    before the first switch stay bill only. Entering rollover starts from zero
    and does not pull a balance out of earlier bills. Entering bill only stops
    the carry so the next rollover span also starts from zero.
    """
    rollover_by_user = {p["id"]: 0.0 for p in payees}
    items_by_user: Dict[Any, List[Dict[str, Any]]] = {p["id"]: [] for p in payees}
    timeline = normalize_switches(list(switches)) if switches is not None else None
    marker = None if timeline is not None else clear_month
    previous_mode: Optional[str] = None
    rows: List[Dict[str, Any]] = []

    for bill in bills:
        origin = format_cycle_label(bill.get("cycle_date")) or str(bill.get("month") or "a previous bill")
        month = bill.get("month")
        note = None
        use_rollover = True
        reset_incoming = False
        if timeline is not None:
            use_rollover, reset_incoming, note, previous_mode = span_flags(
                month, timeline, previous_mode
            )
        payee_rows, rollover_by_user, items_by_user, marker = settle_bill_payees(
            payees,
            bill.get("payments") or {},
            rollover_by_user,
            items_by_user,
            charge_to_split(bill),
            origin,
            month,
            marker,
            use_rollover=use_rollover,
            reset_incoming=reset_incoming,
        )
        rows.append({
            "month": month,
            "uses_rollover": use_rollover if timeline is not None else True,
            "calculation_note": note,
            "payees": payee_rows,
        })
    return rows
