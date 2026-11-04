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

import math
from datetime import date, datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from rollover_clear import (
    apply_rollover_clear_at_bill,
    format_clear_month_label,
    normalize_clear_month,
)


def _cents(amount: float) -> int:
    return int(round(float(amount or 0.0) * 100))


def _from_cents(cents: int) -> float:
    return round(cents / 100.0, 2)


def allocate_portions(total: float, payees: Sequence[Mapping[str, Any]]) -> Dict[Any, float]:
    """Split a dollar total by responsibility so the shares add up to the cent.

    Independent rounding can charge two 50% payees a penny more than the bill.
    Leftover cents go to the largest remainders.
    """
    shares = {payee["id"]: 0.0 for payee in payees}
    responsible = [payee for payee in payees if float(payee.get("responsibility_percent") or 0) > 0]
    if not responsible:
        return shares
    total_cents = _cents(total)
    weights = [(payee["id"], float(payee.get("responsibility_percent") or 0)) for payee in responsible]
    weight_sum = sum(weight for _, weight in weights)
    target = int(round(total_cents * weight_sum / 100.0))
    rows = []
    for payee_id, weight in weights:
        exact = total_cents * weight / 100.0
        base = int(math.floor(exact + 1e-9))
        rows.append({"id": payee_id, "cents": base, "frac": exact - base})
    leftover = target - sum(row["cents"] for row in rows)
    if leftover > 0:
        order = sorted(rows, key=lambda row: (row["frac"], row["id"]), reverse=True)
        for index in range(leftover):
            order[index % len(order)]["cents"] += 1
    elif leftover < 0:
        order = sorted(rows, key=lambda row: (row["frac"], row["id"]))
        for index in range(-leftover):
            order[index % len(order)]["cents"] -= 1
    for row in rows:
        shares[row["id"]] = _from_cents(row["cents"])
    return shares


def split_amount_evenly(total: float, payee_ids: Sequence[Any]) -> Dict[Any, float]:
    """Split a charge into equal cent shares. Extra cents follow the given order."""
    ids = list(payee_ids)
    cents = _cents(total)
    if cents <= 0 or not ids:
        return {}
    base, extra = divmod(cents, len(ids))
    return {
        payee_id: _from_cents(base + (1 if index < extra else 0))
        for index, payee_id in enumerate(ids)
    }


def payees_who_caused_late_fee(
    prior_payees: Sequence[Mapping[str, Any]],
    due_date: Any,
    payment_events: Sequence[Mapping[str, Any]],
) -> List[Any]:
    """Payees who still owed their share on the due date, largest shortfall first.

    A payment after the due date does not erase the late fee. When the due
    date is unknown, someone who never paid their share is treated as late.
    """
    due = _as_date(due_date)
    events = list(payment_events or [])
    late = []
    for payee in prior_payees or []:
        if float(payee.get("responsibility_percent") or 0) <= 0:
            continue
        payee_id = payee.get("user_id")
        owed = float(payee.get("amount_due") or 0.0)
        paid_on_time = 0.0
        saw_event = False
        for event in events:
            if event.get("user_id") != payee_id:
                continue
            saw_event = True
            event_date = _as_date(event.get("date"))
            if due is not None and event_date is not None and event_date > due:
                continue
            paid_on_time += float(event.get("amount") or 0.0)
        if due is None and not saw_event:
            paid_on_time = float(payee.get("amount_paid") or 0.0)
        shortfall = round(owed - paid_on_time, 2)
        if shortfall > 0.009:
            late.append((shortfall, payee_id))
    late.sort(key=lambda row: (-row[0], str(row[1])))
    return [payee_id for _, payee_id in late]


def late_fee_line(share: float, total: float, label: str) -> str:
    """One readable late-fee bullet. The date is the PDF that shows the charge."""
    when = label or "the bill"
    refer = f"Refer to bill PDF from {when}"
    if total > share + 0.009 and abs((share * 2) - total) < 0.02:
        return f"{money_label(share)} late fee (your half of {money_label(total)}). {refer}"
    if total > share + 0.009:
        return f"{money_label(share)} late fee (your share of {money_label(total)}). {refer}"
    return f"{money_label(share)} late fee. {refer}"


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


def _as_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


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
        entry = {"amount": amount, "origin": origin}
        if item.get("kind"):
            entry["kind"] = item.get("kind")
        copied.append(entry)
    return copied


def _sum_items(items: Sequence[Mapping[str, Any]]) -> float:
    return round(sum(float(item.get("amount") or 0.0) for item in items), 2)


def portion_reason_lines(items: Sequence[Mapping[str, Any]]) -> List[str]:
    """Origin of each carried unpaid amount or credit.

    Dates are left as stored (M/D/YY). A leading minus on credits means the
    lines can be added to this bill's share to get the amount owed.
    """
    lines = []
    for item in _copy_items(items):
        amount = item["amount"]
        origin = item["origin"]
        if item.get("kind") == "late_fee":
            lines.append(f"{money_label(amount)} late fee. Refer to bill PDF from {origin}")
        elif amount > 0:
            lines.append(f"{money_label(amount)} unpaid from {origin}")
        else:
            # A leading minus so the lines add up to the amount owed.
            lines.append(f"-{money_label(abs(amount))} credit from {origin}")
    return lines


def portion_breakdown_lines(
    cycle_portion: float,
    incoming_items: Sequence[Mapping[str, Any]],
    use_rollover: bool,
    late_share: float = 0.0,
    late_total: float = 0.0,
    late_label: str = "",
) -> List[str]:
    """This bill's share plus dated carry, so the owed amount can be read as a sum."""
    lines = [f"{money_label(cycle_portion)} share of this bill"]
    if late_share > 0.009:
        lines.append(late_fee_line(late_share, late_total or late_share, late_label))
    if not use_rollover:
        lines.append("Earlier unpaid amounts are not added to this bill")
        return lines
    details = portion_reason_lines(incoming_items)
    if details:
        # The dated lines already add up to the carry. Do not also print the total.
        lines.extend(details)
        return lines
    incoming = _sum_items(incoming_items)
    if incoming < -0.009:
        lines.append(f"-{money_label(abs(incoming))} credit from earlier bills")
    elif incoming > 0.009:
        lines.append(f"{money_label(incoming)} unpaid from earlier bills")
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
            reduced = {"amount": round(amount - left, 2), "origin": debt["origin"]}
            if debt.get("kind"):
                reduced["kind"] = debt.get("kind")
            remaining.append(reduced)
            left = 0.0
        else:
            remaining.append(dict(debt))
    return remaining, round(max(left, 0.0), 2)


def _pay_down(balance: float, funds: float) -> Tuple[float, float]:
    left = round(max(float(balance or 0.0), 0.0), 2)
    available = round(max(float(funds or 0.0), 0.0), 2)
    if available >= left - 0.009:
        return 0.0, round(available - left, 2)
    if available > 0.009:
        return round(left - available, 2), 0.0
    return left, available


def next_carry_items(
    incoming: Sequence[Mapping[str, Any]],
    cycle_portion: float,
    amount_paid: float,
    origin: str,
    late_fee: float = 0.0,
    late_origin: str = "",
) -> List[Dict[str, Any]]:
    """Open items after this bill. Unpaid cycle charges are dated to this bill.

    A prior credit retires the oldest underpayment, then this cycle, then a
    late fee. Cash pays this cycle, then the late fee, then the oldest
    underpayment, so an unpaid October balance stays labeled October.
    """
    items = _copy_items(incoming)
    debts = [item for item in items if item["amount"] > 0]
    credit = round(-sum(item["amount"] for item in items if item["amount"] < 0), 2)
    debts, credit = _apply_funds(debts, credit)

    cycle_left, credit = _pay_down(cycle_portion, credit)
    late_left, credit = _pay_down(late_fee, credit)

    pay_left = round(float(amount_paid or 0.0), 2)
    cycle_left, pay_left = _pay_down(cycle_left, pay_left)
    late_left, pay_left = _pay_down(late_left, pay_left)
    debts, pay_left = _apply_funds(debts, pay_left)

    outgoing = list(debts)
    label = origin or "a previous bill"
    if cycle_left > 0.009:
        outgoing.append({"amount": round(cycle_left, 2), "origin": label})
    if late_left > 0.009:
        outgoing.append({
            "amount": round(late_left, 2),
            "origin": late_origin or label,
            "kind": "late_fee",
        })
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


def _cycle_excluding_late_fee(
    cycle_total: float,
    late_fee: float,
    incoming_total: float,
    statement_total: Optional[float],
) -> float:
    """Keep a late fee out of the shared cycle when the statement already includes it there."""
    cycle = round(float(cycle_total or 0.0), 2)
    fee = round(max(float(late_fee or 0.0), 0.0), 2)
    if fee <= 0.009 or statement_total is None:
        return cycle
    statement = round(float(statement_total), 2)
    previous = round(float(incoming_total or 0.0), 2)
    fee_inside = abs((cycle + previous) - statement)
    fee_outside = abs((cycle + previous + fee) - statement)
    if fee_inside <= fee_outside + 0.001 and cycle - fee >= -0.009:
        return round(cycle - fee, 2)
    return cycle


def _shift_portions(portions: Dict[Any, float], gap_cents: int, payee_ids: Sequence[Any]) -> None:
    """Move leftover pennies onto cycle shares so the payees add up to the statement."""
    ids = [payee_id for payee_id in payee_ids if payee_id in portions]
    if gap_cents == 0 or not ids:
        return
    step = 1 if gap_cents > 0 else -1
    for index in range(abs(gap_cents)):
        payee_id = ids[index % len(ids)]
        portions[payee_id] = _from_cents(_cents(portions[payee_id]) + step)


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
    statement_total: Optional[float] = None,
    late_fee: float = 0.0,
    late_fee_ids: Optional[Sequence[Any]] = None,
    late_fee_label: str = "",
) -> Tuple[List[Dict[str, Any]], Dict[Any, float], Dict[Any, List[Dict[str, Any]]], Optional[str]]:
    """Settle every payee on one bill. Percent applies to ``cycle_total`` only.

    ``reset_incoming`` drops the carry before this bill (a new rollover span,
    or a bill-only bill). Bill-only bills also drop whatever would have
    carried out, so a later rollover span starts from zero.

    ``statement_total`` is the Con Edison amount due. In rollover mode the
    cycle shares absorb the leftover pennies so the payees add up to it.
    A late fee is not split by responsibility: the payees who missed the due
    date pay it, or they split it evenly when more than one of them did.
    """
    prior_marker = clear_marker
    rollover_by_user, clear_marker = apply_rollover_clear_at_bill(
        rollover_by_user, month, clear_marker
    )
    if (prior_marker and not clear_marker) or reset_incoming or not use_rollover:
        rollover_by_user, items_by_user = _zero_carry(payees)

    prepared = []
    incoming_total = 0.0
    for payee in payees:
        payee_id = payee["id"]
        incoming_items = _copy_items(items_by_user.get(payee_id) or [])
        incoming = float(rollover_by_user.get(payee_id) or 0.0)
        if abs(incoming - _sum_items(incoming_items)) >= 0.02 and incoming_items:
            incoming_items = [{"amount": incoming, "origin": "a previous bill"}]
        elif not incoming_items and abs(incoming) >= 0.01:
            incoming_items = [{"amount": incoming, "origin": "a previous bill"}]
        incoming = _sum_items(incoming_items) if incoming_items else incoming
        incoming_total = round(incoming_total + incoming, 2)
        prepared.append((payee, incoming_items, incoming))

    fee = round(max(float(late_fee or 0.0), 0.0), 2)
    cycle_for_split = _cycle_excluding_late_fee(cycle_total, fee, incoming_total, statement_total if use_rollover else None)
    portions = allocate_portions(cycle_for_split, payees)
    responsible_ids = [payee["id"] for payee in payees if float(payee.get("responsibility_percent") or 0) > 0]
    fee_ids = [payee_id for payee_id in (late_fee_ids or []) if payee_id in portions]
    if fee > 0.009 and not fee_ids:
        fee_ids = list(responsible_ids)
    late_shares = split_amount_evenly(fee, fee_ids) if fee > 0.009 else {}

    if use_rollover and statement_total is not None and float(statement_total) > 0:
        computed = round(
            sum(portions.values()) + incoming_total + sum(late_shares.values()),
            2,
        )
        # Only leftover pennies. A larger gap is a real previous balance or an
        # unparsed charge, and must not be quietly split into the cycle.
        gap_cents = _cents(float(statement_total) - computed)
        if abs(gap_cents) <= 10:
            _shift_portions(portions, gap_cents, responsible_ids)

    rows = []
    new_rollover: Dict[Any, float] = {}
    new_items: Dict[Any, List[Dict[str, Any]]] = {}
    for payee, incoming_items, incoming in prepared:
        payee_id = payee["id"]
        portion = portions.get(payee_id, 0.0)
        late_share = late_shares.get(payee_id, 0.0)
        paid = float((payments or {}).get(payee_id, 0.0) or 0.0)
        settled = settle_payee_bill(portion, paid, incoming)
        if late_share > 0.009:
            settled["amount_due"] = round(settled["amount_due"] + late_share, 2)
            settled["share_of_bill_cumulative"] = settled["amount_due"]
            settled["difference"] = round(paid - settled["amount_due"], 2)
            settled["current_balance"] = carry_to_next_bill(settled["amount_due"], paid)
            if settled["difference"] < -0.01:
                settled["status"] = "underpaid"
            elif settled["difference"] > 0.01:
                settled["status"] = "overpaid"
            else:
                settled["status"] = "paid"
        carried = next_carry_items(
            incoming_items,
            portion,
            paid,
            origin,
            late_fee=late_share,
            late_origin=late_fee_label or origin,
        )
        new_items[payee_id] = carried
        new_rollover[payee_id] = settled["current_balance"]
        owing_dates = []
        for item in carried:
            if float(item.get("amount") or 0) > 0.009:
                parsed = _as_date(item.get("origin"))
                if parsed:
                    owing_dates.append(parsed)
        rows.append(
            {
                "user_id": payee_id,
                "name": payee.get("name"),
                "responsibility_percent": payee.get("responsibility_percent") or 0,
                "uses_rollover": use_rollover,
                "owing_since": min(owing_dates).isoformat() if owing_dates else None,
                "portion_reasons": portion_breakdown_lines(
                    portion,
                    incoming_items,
                    use_rollover,
                    late_share=late_share,
                    late_total=fee,
                    late_label=late_fee_label or origin,
                ),
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
    previous_bill: Optional[Dict[str, Any]] = None
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
        late_fee = round(max(float(bill.get("late_fee") or 0.0), 0.0), 2)
        late_ids: List[Any] = []
        if late_fee > 0.009 and previous_bill is not None:
            late_ids = payees_who_caused_late_fee(
                previous_bill["payees"],
                previous_bill.get("due_date"),
                previous_bill.get("payment_events") or [],
            )
            if not late_ids:
                late_ids = [
                    payee["user_id"]
                    for payee in previous_bill["payees"]
                    if float(payee.get("responsibility_percent") or 0) > 0
                    and float(payee.get("current_balance") or 0) > 0.009
                ]
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
            statement_total=bill.get("statement_total"),
            late_fee=late_fee,
            late_fee_ids=late_ids,
            late_fee_label=origin,
        )
        previous_bill = {
            "payees": payee_rows,
            "due_date": bill.get("due_date"),
            "payment_events": bill.get("payment_events") or [],
        }
        rows.append({
            "month": month,
            "uses_rollover": use_rollover if timeline is not None else True,
            "calculation_note": note,
            "payees": payee_rows,
        })
    return rows
