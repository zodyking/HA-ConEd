"""
Database module using Prisma ORM with PostgreSQL.
Provides async database operations for the ConEd Scraper addon.
"""
import json
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

from prisma import Prisma
from prisma.models import (
    Bill, Payment, BillDetails, BillDocument, PayeeUser, UserCard,
    AccountBalanceHistory, ScrapedData, Log, ScrapeHistory, AppSetting
)

logger = logging.getLogger(__name__)

# Global Prisma client instance
db = Prisma()

def utc_now() -> datetime:
    """Get current UTC time"""
    return datetime.now(timezone.utc)

def utc_now_iso() -> str:
    """Get current UTC time as ISO string"""
    return utc_now().isoformat()

# =============================================================================
# Connection Management
# =============================================================================

async def connect():
    """Connect to the database"""
    if not db.is_connected():
        await db.connect()
        logger.info("Connected to PostgreSQL database")

async def disconnect():
    """Disconnect from the database"""
    if db.is_connected():
        await db.disconnect()
        logger.info("Disconnected from PostgreSQL database")

async def ensure_connected():
    """Ensure database is connected"""
    if not db.is_connected():
        await connect()

# =============================================================================
# Helper Functions
# =============================================================================

def parse_amount(amount_str: str) -> float:
    """Parse amount string like '$123.45' to float"""
    if not amount_str:
        return 0.0
    cleaned = ''.join(c for c in str(amount_str) if c.isdigit() or c in '.-')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def generate_payment_hash(payment_date: str, amount: str, description: str, bill_cycle_date: str = "") -> str:
    """Generate unique hash for payment deduplication"""
    data = f"{payment_date}|{amount}|{description}|{bill_cycle_date}"
    return hashlib.md5(data.encode()).hexdigest()

def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats to datetime"""
    if not date_str:
        return None
    
    formats = [
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%m/%d/%y",
        "%B %d, %Y",
        "%b %d, %Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    
    return None

def model_to_dict(model) -> Dict[str, Any]:
    """Convert Prisma model to dictionary"""
    if model is None:
        return None
    if hasattr(model, 'model_dump'):
        return model.model_dump()
    elif hasattr(model, 'dict'):
        return model.dict()
    return dict(model)

def decimal_to_float(val) -> Optional[float]:
    """Convert Decimal to float safely"""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    return float(val)

# =============================================================================
# Bills
# =============================================================================

async def upsert_bill(
    bill_cycle_date: str,
    bill_date: Optional[str] = None,
    month_range: Optional[str] = None,
    bill_total: Optional[str] = None
) -> Bill:
    """Insert or update a bill"""
    await ensure_connected()
    
    amount_numeric = parse_amount(bill_total) if bill_total else None
    cycle_date = parse_date(bill_cycle_date) or utc_now()
    bill_dt = parse_date(bill_date) if bill_date else None
    
    existing = await db.bill.find_first(
        where={
            "billCycleDate": cycle_date,
            "monthRange": month_range
        }
    )
    
    if existing:
        return await db.bill.update(
            where={"id": existing.id},
            data={
                "billDate": bill_dt,
                "billTotal": Decimal(str(amount_numeric)) if amount_numeric else None,
                "scrapeCount": existing.scrapeCount + 1
            }
        )
    else:
        return await db.bill.create(
            data={
                "billCycleDate": cycle_date,
                "billDate": bill_dt,
                "monthRange": month_range,
                "billTotal": Decimal(str(amount_numeric)) if amount_numeric else None,
                "scrapeCount": 1
            }
        )

async def get_all_bills() -> List[Dict[str, Any]]:
    """Get all bills sorted by cycle date (newest first)"""
    await ensure_connected()
    
    bills = await db.bill.find_many(
        order_by={"billCycleDate": "desc"},
        include={"payments": True, "details": True, "document": True}
    )
    
    result = []
    for bill in bills:
        bill_dict = {
            "id": bill.id,
            "bill_cycle_date": bill.billCycleDate.strftime("%m/%d/%Y") if bill.billCycleDate else None,
            "bill_date": bill.billDate.strftime("%Y-%m-%d") if bill.billDate else None,
            "month_range": bill.monthRange,
            "bill_total": f"${decimal_to_float(bill.billTotal):.2f}" if bill.billTotal else None,
            "amount_numeric": decimal_to_float(bill.billTotal),
            "first_scraped_at": bill.firstScrapedAt.isoformat() if bill.firstScrapedAt else None,
            "last_scraped_at": bill.lastScrapedAt.isoformat() if bill.lastScrapedAt else None,
            "scrape_count": bill.scrapeCount,
        }
        result.append(bill_dict)
    
    return result

async def get_bill_by_id(bill_id: int) -> Optional[Dict[str, Any]]:
    """Get a single bill by ID"""
    await ensure_connected()
    
    bill = await db.bill.find_unique(
        where={"id": bill_id},
        include={"payments": True, "details": True, "document": True}
    )
    
    if not bill:
        return None
    
    return {
        "id": bill.id,
        "bill_cycle_date": bill.billCycleDate.strftime("%m/%d/%Y") if bill.billCycleDate else None,
        "bill_date": bill.billDate.strftime("%Y-%m-%d") if bill.billDate else None,
        "month_range": bill.monthRange,
        "bill_total": f"${decimal_to_float(bill.billTotal):.2f}" if bill.billTotal else None,
        "amount_numeric": decimal_to_float(bill.billTotal),
    }

async def get_latest_bill_with_details() -> Optional[Dict[str, Any]]:
    """Get the most recent bill with its details"""
    await ensure_connected()
    
    bill = await db.bill.find_first(
        order_by={"billCycleDate": "desc"},
        include={"details": True}
    )
    
    if not bill:
        return None
    
    result = {
        "id": bill.id,
        "bill_cycle_date": bill.billCycleDate.strftime("%m/%d/%Y") if bill.billCycleDate else None,
        "bill_date": bill.billDate.strftime("%Y-%m-%d") if bill.billDate else None,
        "month_range": bill.monthRange,
        "bill_total": f"${decimal_to_float(bill.billTotal):.2f}" if bill.billTotal else None,
        "amount_numeric": decimal_to_float(bill.billTotal),
    }
    
    if bill.details:
        result.update({
            "due_date": bill.details.dueDate.strftime("%b %d, %Y") if bill.details.dueDate else None,
            "kwh_used": decimal_to_float(bill.details.kwhUsed),
            "kwh_cost": decimal_to_float(bill.details.kwhCost),
            "electricity_total": decimal_to_float(bill.details.electricityTotal),
            "total_from_billing_period": decimal_to_float(bill.details.totalFromBillingPeriod),
            "balance_from_previous_bill": decimal_to_float(bill.details.balanceFromPreviousBill),
            "billing_days": bill.details.billingDays,
            "supply_charges": bill.details.supplyCharges,
            "delivery_charges": bill.details.deliveryCharges,
        })
    else:
        result.update({
            "due_date": None,
            "kwh_used": None,
            "kwh_cost": None,
            "electricity_total": None,
            "total_from_billing_period": None,
            "balance_from_previous_bill": None,
            "billing_days": None,
            "supply_charges": None,
            "delivery_charges": None,
        })
    
    return result

async def get_bill_history_for_graph() -> List[Dict[str, Any]]:
    """Get bill history data for graphing"""
    await ensure_connected()
    
    bills = await db.bill.find_many(
        order_by={"billCycleDate": "asc"},
        include={"details": True}
    )
    
    results = []
    for bill in bills:
        kwh_used = decimal_to_float(bill.details.kwhUsed) if bill.details else 0
        
        result = {
            "bill_id": bill.id,
            "month_range": bill.monthRange,
            "bill_cycle_date": bill.billCycleDate.strftime("%m/%d/%Y") if bill.billCycleDate else None,
            "bill_total": f"${decimal_to_float(bill.billTotal):.2f}" if bill.billTotal else None,
            "amount_numeric": decimal_to_float(bill.billTotal),
            "kwh_used": kwh_used,
            "kwh_cost": decimal_to_float(bill.details.kwhCost) if bill.details else None,
            "electricity_total": decimal_to_float(bill.details.electricityTotal) if bill.details else None,
            "total_from_billing_period": decimal_to_float(bill.details.totalFromBillingPeriod) if bill.details else None,
            "balance_from_previous_bill": decimal_to_float(bill.details.balanceFromPreviousBill) if bill.details else None,
            "billing_days": bill.details.billingDays if bill.details else None,
        }
        
        # Calculate supply and delivery totals/rates from JSON
        if bill.details:
            supply = bill.details.supplyCharges or {}
            delivery = bill.details.deliveryCharges or {}
            
            result["supply_total"] = supply.get("total", 0)
            result["delivery_total"] = delivery.get("total", 0)
            
            if kwh_used > 0:
                result["supply_rate"] = round(result["supply_total"] / kwh_used, 4) if result["supply_total"] else 0
                result["delivery_rate"] = round(result["delivery_total"] / kwh_used, 4) if result["delivery_total"] else 0
            else:
                result["supply_rate"] = 0
                result["delivery_rate"] = 0
        else:
            result["supply_total"] = 0
            result["delivery_total"] = 0
            result["supply_rate"] = 0
            result["delivery_rate"] = 0
        
        results.append(result)
    
    return results

# =============================================================================
# Bill Details
# =============================================================================

async def upsert_bill_details(
    bill_id: int,
    due_date: Optional[str] = None,
    kwh_used: Optional[float] = None,
    kwh_cost: Optional[float] = None,
    electricity_total: Optional[float] = None,
    total_from_billing_period: Optional[float] = None,
    balance_from_previous_bill: Optional[float] = None,
    billing_days: Optional[int] = None,
    supply_charges: Optional[Dict] = None,
    delivery_charges: Optional[Dict] = None,
    billing_period_start: Optional[str] = None,
    billing_period_end: Optional[str] = None,
) -> BillDetails:
    """Insert or update bill details"""
    await ensure_connected()
    
    due_dt = parse_date(due_date) if due_date else None
    start_dt = parse_date(billing_period_start) if billing_period_start else None
    end_dt = parse_date(billing_period_end) if billing_period_end else None
    
    existing = await db.billdetails.find_unique(where={"billId": bill_id})
    
    data = {
        "dueDate": due_dt,
        "kwhUsed": Decimal(str(kwh_used)) if kwh_used is not None else None,
        "kwhCost": Decimal(str(kwh_cost)) if kwh_cost is not None else None,
        "electricityTotal": Decimal(str(electricity_total)) if electricity_total is not None else None,
        "totalFromBillingPeriod": Decimal(str(total_from_billing_period)) if total_from_billing_period is not None else None,
        "balanceFromPreviousBill": Decimal(str(balance_from_previous_bill)) if balance_from_previous_bill is not None else None,
        "billingDays": billing_days,
        "supplyCharges": supply_charges,
        "deliveryCharges": delivery_charges,
        "billingPeriodStart": start_dt,
        "billingPeriodEnd": end_dt,
    }
    
    if existing:
        return await db.billdetails.update(
            where={"id": existing.id},
            data=data
        )
    else:
        data["billId"] = bill_id
        return await db.billdetails.create(data=data)

async def get_bill_details(bill_id: int) -> Optional[Dict[str, Any]]:
    """Get bill details by bill ID"""
    await ensure_connected()
    
    details = await db.billdetails.find_unique(where={"billId": bill_id})
    
    if not details:
        return None
    
    return {
        "id": details.id,
        "bill_id": details.billId,
        "due_date": details.dueDate.strftime("%b %d, %Y") if details.dueDate else None,
        "kwh_used": decimal_to_float(details.kwhUsed),
        "kwh_cost": decimal_to_float(details.kwhCost),
        "electricity_total": decimal_to_float(details.electricityTotal),
        "total_from_billing_period": decimal_to_float(details.totalFromBillingPeriod),
        "balance_from_previous_bill": decimal_to_float(details.balanceFromPreviousBill),
        "billing_days": details.billingDays,
        "supply_charges": details.supplyCharges,
        "delivery_charges": details.deliveryCharges,
    }

async def get_bill_details_by_id(bill_id: int) -> Optional[Dict[str, Any]]:
    """Alias for get_bill_details"""
    return await get_bill_details(bill_id)

async def get_all_bill_details() -> List[Dict[str, Any]]:
    """Get all bill details with bill metadata"""
    await ensure_connected()
    
    details_list = await db.billdetails.find_many(
        include={"bill": True},
        order_by={"bill": {"billCycleDate": "desc"}}
    )
    
    results = []
    for d in details_list:
        results.append({
            "id": d.id,
            "bill_id": d.billId,
            "month_range": d.bill.monthRange if d.bill else None,
            "bill_cycle_date": d.bill.billCycleDate.strftime("%m/%d/%Y") if d.bill and d.bill.billCycleDate else None,
            "scraped_bill_total": f"${decimal_to_float(d.bill.billTotal):.2f}" if d.bill and d.bill.billTotal else None,
            "due_date": d.dueDate.strftime("%b %d, %Y") if d.dueDate else None,
            "kwh_used": decimal_to_float(d.kwhUsed),
            "kwh_cost": decimal_to_float(d.kwhCost),
            "electricity_total": decimal_to_float(d.electricityTotal),
            "total_from_billing_period": decimal_to_float(d.totalFromBillingPeriod),
            "balance_from_previous_bill": decimal_to_float(d.balanceFromPreviousBill),
            "billing_days": d.billingDays,
            "supply_charges": d.supplyCharges,
            "delivery_charges": d.deliveryCharges,
        })
    
    return results

async def delete_bill_details(bill_id: int) -> bool:
    """Delete bill details"""
    await ensure_connected()
    
    try:
        await db.billdetails.delete(where={"billId": bill_id})
        return True
    except Exception:
        return False

# =============================================================================
# Bill Documents
# =============================================================================

async def upsert_bill_document(bill_id: int, pdf_path: str, source_url: Optional[str] = None) -> BillDocument:
    """Insert or update bill document"""
    await ensure_connected()
    
    existing = await db.billdocument.find_unique(where={"billId": bill_id})
    
    if existing:
        return await db.billdocument.update(
            where={"id": existing.id},
            data={"pdfPath": pdf_path, "sourceUrl": source_url}
        )
    else:
        return await db.billdocument.create(
            data={"billId": bill_id, "pdfPath": pdf_path, "sourceUrl": source_url}
        )

async def get_bill_document(bill_id: int) -> Optional[Dict[str, Any]]:
    """Get bill document by bill ID"""
    await ensure_connected()
    
    doc = await db.billdocument.find_unique(where={"billId": bill_id})
    
    if not doc:
        return None
    
    return {
        "id": doc.id,
        "bill_id": doc.billId,
        "pdf_path": doc.pdfPath,
        "source_url": doc.sourceUrl,
        "created_at": doc.createdAt.isoformat() if doc.createdAt else None,
    }

async def get_all_bill_documents_with_periods() -> List[Dict[str, Any]]:
    """Get all bill documents with month range"""
    await ensure_connected()
    
    docs = await db.billdocument.find_many(
        include={"bill": True},
        order_by={"bill": {"billCycleDate": "desc"}}
    )
    
    return [
        {
            "bill_id": doc.billId,
            "pdf_path": doc.pdfPath,
            "month_range": doc.bill.monthRange if doc.bill else None,
        }
        for doc in docs
    ]

async def get_latest_bill_id_with_document() -> Optional[int]:
    """Get the most recent bill ID that has a document"""
    await ensure_connected()
    
    doc = await db.billdocument.find_first(
        include={"bill": True},
        order_by={"bill": {"billCycleDate": "desc"}}
    )
    
    return doc.billId if doc else None

async def delete_bill_document(bill_id: int) -> bool:
    """Delete bill document"""
    await ensure_connected()
    
    try:
        await db.billdocument.delete(where={"billId": bill_id})
        return True
    except Exception:
        return False

# =============================================================================
# Payments
# =============================================================================

async def upsert_payment(
    payment_date: str,
    description: str,
    amount: str,
    bill_id: Optional[int] = None,
    scrape_order: Optional[int] = None,
) -> Payment:
    """Insert or update a payment"""
    await ensure_connected()
    
    # Get bill cycle date for hash
    bill_cycle = ""
    if bill_id:
        bill = await db.bill.find_unique(where={"id": bill_id})
        if bill:
            bill_cycle = bill.billCycleDate.strftime("%m/%d/%Y") if bill.billCycleDate else ""
    
    payment_hash = generate_payment_hash(payment_date, amount, description, bill_cycle)
    amount_numeric = parse_amount(amount)
    payment_dt = parse_date(payment_date) or utc_now()
    
    existing = await db.payment.find_unique(where={"paymentHash": payment_hash})
    
    if existing:
        # Don't overwrite manually set bill
        update_data = {"scrapeOrder": scrape_order}
        if not existing.billManuallySet and bill_id:
            update_data["billId"] = bill_id
        
        return await db.payment.update(
            where={"id": existing.id},
            data=update_data
        )
    else:
        return await db.payment.create(
            data={
                "paymentDate": payment_dt,
                "description": description,
                "amount": Decimal(str(amount_numeric)),
                "paymentHash": payment_hash,
                "billId": bill_id,
                "scrapeOrder": scrape_order,
            }
        )

async def get_all_payments(bill_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all payments with payee and bill info"""
    await ensure_connected()
    
    where = {"billId": bill_id} if bill_id else {}
    
    payments = await db.payment.find_many(
        where=where,
        include={"payeeUser": True, "bill": True},
        order_by={"paymentDate": "desc"}
    )
    
    return [
        {
            "id": p.id,
            "bill_id": p.billId,
            "payment_date": p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else None,
            "description": p.description,
            "amount": f"${decimal_to_float(p.amount):.2f}" if p.amount else None,
            "amount_numeric": decimal_to_float(p.amount),
            "payee_status": p.payeeStatus,
            "payee_name": p.payeeUser.name if p.payeeUser else None,
            "payee_user_id": p.payeeUserId,
            "card_last_four": p.cardLastFour,
            "verification_method": p.verificationMethod,
            "bill_month": p.bill.monthRange if p.bill else None,
            "bill_cycle": p.bill.billCycleDate.strftime("%m/%d/%Y") if p.bill and p.bill.billCycleDate else None,
            "bill_manually_set": p.billManuallySet,
            "manual_order": p.manualOrder,
        }
        for p in payments
    ]

async def get_payment_by_id(payment_id: int) -> Optional[Dict[str, Any]]:
    """Get a single payment by ID"""
    await ensure_connected()
    
    p = await db.payment.find_unique(
        where={"id": payment_id},
        include={"payeeUser": True, "bill": True}
    )
    
    if not p:
        return None
    
    return {
        "id": p.id,
        "bill_id": p.billId,
        "payment_date": p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else None,
        "description": p.description,
        "amount": f"${decimal_to_float(p.amount):.2f}" if p.amount else None,
        "amount_numeric": decimal_to_float(p.amount),
        "payee_status": p.payeeStatus,
        "payee_name": p.payeeUser.name if p.payeeUser else None,
        "payee_user_id": p.payeeUserId,
        "card_last_four": p.cardLastFour,
        "bill_month": p.bill.monthRange if p.bill else None,
        "bill_cycle": p.bill.billCycleDate.strftime("%m/%d/%Y") if p.bill and p.bill.billCycleDate else None,
    }

async def get_latest_payment() -> Optional[Dict[str, Any]]:
    """Get the most recent payment overall"""
    await ensure_connected()
    
    p = await db.payment.find_first(
        order_by={"paymentDate": "desc"},
        include={"payeeUser": True, "bill": True}
    )
    
    if not p:
        return None
    
    return {
        "id": p.id,
        "bill_id": p.billId,
        "payment_date": p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else None,
        "description": p.description,
        "amount": f"${decimal_to_float(p.amount):.2f}" if p.amount else None,
        "amount_numeric": decimal_to_float(p.amount),
        "payee_name": p.payeeUser.name if p.payeeUser else None,
    }

async def get_last_payment_for_latest_bill() -> Optional[Dict[str, Any]]:
    """Get the most recent payment for the most recent bill - CORRECT last payment logic"""
    await ensure_connected()
    
    # Get the latest bill
    latest_bill = await db.bill.find_first(order_by={"billCycleDate": "desc"})
    
    if not latest_bill:
        return None
    
    # Get the most recent payment for that bill
    p = await db.payment.find_first(
        where={"billId": latest_bill.id},
        order_by={"paymentDate": "desc"},
        include={"payeeUser": True, "bill": True}
    )
    
    if not p:
        return None
    
    return {
        "id": p.id,
        "bill_id": p.billId,
        "payment_date": p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else None,
        "description": p.description,
        "amount": f"${decimal_to_float(p.amount):.2f}" if p.amount else None,
        "amount_numeric": decimal_to_float(p.amount),
        "payee_name": p.payeeUser.name if p.payeeUser else None,
        "bill_cycle_date": p.bill.billCycleDate.strftime("%m/%d/%Y") if p.bill and p.bill.billCycleDate else None,
    }

async def get_payments_for_bill(bill_id: int) -> List[Dict[str, Any]]:
    """Get all payments for a specific bill"""
    return await get_all_payments(bill_id=bill_id)

async def get_most_recent_bill_payment_count() -> Dict[str, Any]:
    """Get payment count and last payment for the most recent bill"""
    await ensure_connected()
    
    latest_bill = await db.bill.find_first(order_by={"billCycleDate": "desc"})
    
    if not latest_bill:
        return {"count": 0, "last_payment": None}
    
    count = await db.payment.count(where={"billId": latest_bill.id})
    
    last_payment = await db.payment.find_first(
        where={"billId": latest_bill.id},
        order_by=[
            {"manualOrder": "asc"},
            {"paymentDate": "desc"},
            {"firstScrapedAt": "desc"}
        ],
        include={"payeeUser": True}
    )
    
    last_payment_dict = None
    if last_payment:
        last_payment_dict = {
            "id": last_payment.id,
            "payment_date": last_payment.paymentDate.strftime("%m/%d/%Y") if last_payment.paymentDate else None,
            "description": last_payment.description,
            "amount": f"${decimal_to_float(last_payment.amount):.2f}" if last_payment.amount else None,
            "amount_numeric": decimal_to_float(last_payment.amount),
            "payee_name": last_payment.payeeUser.name if last_payment.payeeUser else None,
        }
    
    return {"count": count, "last_payment": last_payment_dict}

async def update_payment_bill(payment_id: int, bill_id: Optional[int], manually_set: bool = False) -> bool:
    """Update payment's bill association"""
    await ensure_connected()
    
    try:
        await db.payment.update(
            where={"id": payment_id},
            data={
                "billId": bill_id,
                "billManuallySet": manually_set
            }
        )
        return True
    except Exception:
        return False

async def update_payment_order(payment_id: int, bill_id: int, order: int) -> bool:
    """Update payment's bill and manual order"""
    await ensure_connected()
    
    try:
        await db.payment.update(
            where={"id": payment_id},
            data={
                "billId": bill_id,
                "billManuallySet": True,
                "manualOrder": order
            }
        )
        return True
    except Exception:
        return False

async def clear_payment_manual_audit() -> bool:
    """Clear all manual audit flags"""
    await ensure_connected()
    
    try:
        await db.payment.update_many(
            where={},
            data={
                "billManuallySet": False,
                "manualOrder": None
            }
        )
        return True
    except Exception:
        return False

async def attribute_payment(
    payment_id: int,
    payee_user_id: int,
    payee_status: str = "verified",
    verification_method: Optional[str] = None,
    card_last_four: Optional[str] = None
) -> bool:
    """Attribute a payment to a payee"""
    await ensure_connected()
    
    try:
        await db.payment.update(
            where={"id": payment_id},
            data={
                "payeeUserId": payee_user_id,
                "payeeStatus": payee_status,
                "verificationMethod": verification_method,
                "cardLastFour": card_last_four
            }
        )
        return True
    except Exception:
        return False

async def clear_payment_attribution(payment_id: int) -> bool:
    """Clear payment attribution"""
    await ensure_connected()
    
    try:
        await db.payment.update(
            where={"id": payment_id},
            data={
                "payeeUserId": None,
                "payeeStatus": "unverified",
                "verificationMethod": None,
                "cardLastFour": None
            }
        )
        return True
    except Exception:
        return False

async def get_unverified_payments() -> List[Dict[str, Any]]:
    """Get payments with unverified status"""
    await ensure_connected()
    
    payments = await db.payment.find_many(
        where={"payeeStatus": "unverified"},
        include={"bill": True}
    )
    
    return [
        {
            "id": p.id,
            "payment_date": p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else None,
            "description": p.description,
            "amount": f"${decimal_to_float(p.amount):.2f}" if p.amount else None,
            "amount_numeric": decimal_to_float(p.amount),
            "bill_id": p.billId,
        }
        for p in payments
    ]

# =============================================================================
# Payee Users
# =============================================================================

async def create_payee_user(name: str, is_default: bool = False, responsibility_percent: int = 0, is_admin: bool = False) -> PayeeUser:
    """Create a new payee user"""
    await ensure_connected()
    
    # If setting as default, unset other defaults
    if is_default:
        await db.payeeuser.update_many(
            where={"isDefault": True},
            data={"isDefault": False}
        )
    
    return await db.payeeuser.create(
        data={
            "name": name,
            "isDefault": is_default,
            "responsibilityPercent": responsibility_percent,
            "isAdmin": is_admin
        }
    )

async def get_payee_users() -> List[Dict[str, Any]]:
    """Get all payee users with their cards"""
    await ensure_connected()
    
    users = await db.payeeuser.find_many(
        include={"cards": True},
        order_by={"name": "asc"}
    )
    
    return [
        {
            "id": u.id,
            "name": u.name,
            "is_default": u.isDefault,
            "responsibility_percent": u.responsibilityPercent,
            "is_admin": u.isAdmin,
            "cards": ",".join([c.cardLastFour for c in u.cards]) if u.cards else "",
            "created_at": u.createdAt.isoformat() if u.createdAt else None,
        }
        for u in users
    ]

async def get_default_payee() -> Optional[Dict[str, Any]]:
    """Get the default payee user"""
    await ensure_connected()
    
    user = await db.payeeuser.find_first(where={"isDefault": True})
    
    if not user:
        return None
    
    return {
        "id": user.id,
        "name": user.name,
        "responsibility_percent": user.responsibilityPercent,
    }

async def get_admin_users() -> List[Dict[str, Any]]:
    """Get all admin users"""
    await ensure_connected()
    
    users = await db.payeeuser.find_many(where={"isAdmin": True})
    
    return [{"id": u.id, "name": u.name} for u in users]

async def update_payee_user(user_id: int, name: Optional[str] = None, is_default: Optional[bool] = None, is_admin: Optional[bool] = None) -> bool:
    """Update payee user"""
    await ensure_connected()
    
    data = {}
    if name is not None:
        data["name"] = name
    if is_default is not None:
        if is_default:
            await db.payeeuser.update_many(where={"isDefault": True}, data={"isDefault": False})
        data["isDefault"] = is_default
    if is_admin is not None:
        data["isAdmin"] = is_admin
    
    if not data:
        return False
    
    try:
        await db.payeeuser.update(where={"id": user_id}, data=data)
        return True
    except Exception:
        return False

async def delete_payee_user(user_id: int) -> bool:
    """Delete payee user"""
    await ensure_connected()
    
    try:
        await db.payeeuser.delete(where={"id": user_id})
        return True
    except Exception:
        return False

async def set_user_admin(user_id: int, is_admin: bool) -> bool:
    """Set user admin status"""
    return await update_payee_user(user_id, is_admin=is_admin)

async def update_payee_responsibilities(responsibilities: Dict[int, int]) -> bool:
    """Update responsibility percentages for multiple payees"""
    await ensure_connected()
    
    # Verify total is 100%
    total = sum(responsibilities.values())
    if total != 100:
        return False
    
    try:
        for user_id, percent in responsibilities.items():
            await db.payeeuser.update(
                where={"id": user_id},
                data={"responsibilityPercent": percent}
            )
        return True
    except Exception:
        return False

# =============================================================================
# User Cards
# =============================================================================

async def add_user_card(user_id: int, card_last_four: str, card_label: Optional[str] = None) -> UserCard:
    """Add a card to a user"""
    await ensure_connected()
    
    return await db.usercard.create(
        data={
            "userId": user_id,
            "cardLastFour": card_last_four,
            "cardLabel": card_label
        }
    )

async def get_user_cards(user_id: int) -> List[Dict[str, Any]]:
    """Get all cards for a user"""
    await ensure_connected()
    
    cards = await db.usercard.find_many(where={"userId": user_id})
    
    return [
        {
            "id": c.id,
            "card_last_four": c.cardLastFour,
            "card_label": c.cardLabel,
        }
        for c in cards
    ]

async def get_user_by_card(card_last_four: str) -> Optional[Dict[str, Any]]:
    """Get user by card last four digits"""
    await ensure_connected()
    
    card = await db.usercard.find_unique(
        where={"cardLastFour": card_last_four},
        include={"user": True}
    )
    
    if not card or not card.user:
        return None
    
    return {
        "id": card.user.id,
        "name": card.user.name,
    }

async def update_user_card(card_id: int, card_label: str) -> bool:
    """Update card label"""
    await ensure_connected()
    
    try:
        await db.usercard.update(where={"id": card_id}, data={"cardLabel": card_label})
        return True
    except Exception:
        return False

async def delete_user_card(card_id: int) -> bool:
    """Delete a card"""
    await ensure_connected()
    
    try:
        await db.usercard.delete(where={"id": card_id})
        return True
    except Exception:
        return False

# =============================================================================
# Account Balance
# =============================================================================

async def record_account_balance(balance: str) -> bool:
    """Record account balance, return True if changed"""
    await ensure_connected()
    
    balance_numeric = parse_amount(balance)
    
    # Get previous balance
    prev = await db.accountbalancehistory.find_first(order_by={"scrapedAt": "desc"})
    
    changed = True
    if prev:
        prev_numeric = decimal_to_float(prev.balance)
        changed = abs(balance_numeric - prev_numeric) > 0.01
    
    await db.accountbalancehistory.create(
        data={
            "balance": Decimal(str(balance_numeric)),
            "changedFromPrevious": changed
        }
    )
    
    return changed

async def get_current_balance() -> Optional[Dict[str, Any]]:
    """Get current account balance"""
    await ensure_connected()
    
    balance = await db.accountbalancehistory.find_first(order_by={"scrapedAt": "desc"})
    
    if not balance:
        return None
    
    return {
        "balance": f"${decimal_to_float(balance.balance):.2f}",
        "balance_numeric": decimal_to_float(balance.balance),
        "scraped_at": balance.scrapedAt.isoformat() if balance.scrapedAt else None,
    }

# =============================================================================
# Scraped Data & Logs
# =============================================================================

async def save_scraped_data(data: Dict[str, Any], status: str, error_message: Optional[str] = None, screenshot_path: Optional[str] = None) -> int:
    """Save raw scraped data"""
    await ensure_connected()
    
    record = await db.scrapeddata.create(
        data={
            "data": data,
            "status": status,
            "errorMessage": error_message,
            "screenshotPath": screenshot_path
        }
    )
    
    # Sync to normalized tables if successful
    if status == "success" and data:
        await sync_from_scrape(data)
    
    return record.id

async def get_latest_scraped_data(limit: int = 1) -> List[Dict[str, Any]]:
    """Get latest scraped data records"""
    await ensure_connected()
    
    records = await db.scrapeddata.find_many(
        order_by={"timestamp": "desc"},
        take=limit
    )
    
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "data": r.data,
            "status": r.status,
            "error_message": r.errorMessage,
            "screenshot_path": r.screenshotPath,
        }
        for r in records
    ]

async def get_all_scraped_data() -> List[Dict[str, Any]]:
    """Get all scraped data"""
    await ensure_connected()
    
    records = await db.scrapeddata.find_many(order_by={"timestamp": "desc"})
    
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "data": r.data,
            "status": r.status,
        }
        for r in records
    ]

async def add_log(level: str, message: str):
    """Add a log entry"""
    try:
        await ensure_connected()
        await db.log.create(data={"level": level, "message": message})
    except Exception as e:
        logger.warning(f"Failed to add log to database: {e}")

async def get_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent logs"""
    await ensure_connected()
    
    logs = await db.log.find_many(
        order_by={"timestamp": "desc"},
        take=limit
    )
    
    return [
        {
            "id": l.id,
            "timestamp": l.timestamp.isoformat() if l.timestamp else None,
            "level": l.level,
            "message": l.message,
        }
        for l in logs
    ]

async def get_log_count() -> int:
    """Get total log count"""
    await ensure_connected()
    return await db.log.count()

async def get_bill_count() -> int:
    """Get total bill count"""
    await ensure_connected()
    return await db.bill.count()

async def clear_logs():
    """Clear all logs"""
    await ensure_connected()
    await db.log.delete_many()

async def add_scrape_history(success: bool, error_message: Optional[str] = None, failure_step: Optional[str] = None, duration_seconds: Optional[float] = None):
    """Add scrape history entry"""
    await ensure_connected()
    
    await db.scrapehistory.create(
        data={
            "success": success,
            "errorMessage": error_message,
            "failureStep": failure_step,
            "durationSeconds": duration_seconds
        }
    )
    
    # Keep only last 100
    count = await db.scrapehistory.count()
    if count > 100:
        oldest = await db.scrapehistory.find_many(
            order_by={"timestamp": "asc"},
            take=count - 100
        )
        for record in oldest:
            await db.scrapehistory.delete(where={"id": record.id})

async def get_scrape_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent scrape history"""
    await ensure_connected()
    
    history = await db.scrapehistory.find_many(
        order_by={"timestamp": "desc"},
        take=limit
    )
    
    return [
        {
            "id": h.id,
            "timestamp": h.timestamp.isoformat() if h.timestamp else None,
            "success": h.success,
            "error_message": h.errorMessage,
            "failure_step": h.failureStep,
            "duration_seconds": h.durationSeconds,
        }
        for h in history
    ]

# =============================================================================
# App Settings
# =============================================================================

async def get_app_setting(key: str) -> Optional[Any]:
    """Get app setting value"""
    await ensure_connected()
    
    setting = await db.appsetting.find_unique(where={"key": key})
    
    if not setting:
        return None
    
    return setting.value

async def set_app_setting(key: str, value: Any):
    """Set app setting value"""
    await ensure_connected()
    
    existing = await db.appsetting.find_unique(where={"key": key})
    
    if existing:
        await db.appsetting.update(where={"key": key}, data={"value": value})
    else:
        await db.appsetting.create(data={"key": key, "value": value})

async def get_tts_config_db() -> Optional[Dict[str, Any]]:
    """Get TTS config from database"""
    return await get_app_setting("tts_config")

async def save_tts_config_db(config: Dict[str, Any]):
    """Save TTS config to database"""
    await set_app_setting("tts_config", config)

async def get_tts_schedule_db() -> Optional[Dict[str, Any]]:
    """Get TTS schedule from database"""
    return await get_app_setting("tts_schedule")

async def save_tts_schedule_db(schedule: Dict[str, Any]):
    """Save TTS schedule to database"""
    await set_app_setting("tts_schedule", schedule)

async def get_meter_config_db() -> Optional[Dict[str, Any]]:
    """Get meter tracking config"""
    return await get_app_setting("meter_config")

async def save_meter_config_db(config: Dict[str, Any]):
    """Save meter tracking config"""
    await set_app_setting("meter_config", config)

async def get_meter_reading_db() -> Optional[Dict[str, Any]]:
    """Get cached meter reading"""
    return await get_app_setting("meter_reading_cache")

async def save_meter_reading_db(reading: Dict[str, Any]):
    """Save meter reading to cache"""
    await set_app_setting("meter_reading_cache", reading)

async def get_meter_forecast_db() -> Optional[Dict[str, Any]]:
    """Get cached meter forecast"""
    return await get_app_setting("meter_forecast_cache")

async def save_meter_forecast_db(forecast: Dict[str, Any]):
    """Save meter forecast to cache"""
    await set_app_setting("meter_forecast_cache", forecast)

async def get_realtime_readings_db() -> Optional[List[Dict[str, Any]]]:
    """Get cached realtime readings"""
    return await get_app_setting("realtime_readings_cache")

async def save_realtime_readings_db(readings: List[Dict[str, Any]]):
    """Save realtime readings to cache"""
    await set_app_setting("realtime_readings_cache", readings)

# =============================================================================
# Data Sync
# =============================================================================

async def sync_from_scrape(data: Dict[str, Any]):
    """Sync scraped data to normalized tables"""
    try:
        # Record balance
        if "account_balance" in data:
            await record_account_balance(data["account_balance"])
        
        # Process bills
        if "bills" in data:
            for bill_data in data["bills"]:
                bill = await upsert_bill(
                    bill_cycle_date=bill_data.get("bill_cycle_date", ""),
                    bill_date=bill_data.get("bill_date"),
                    month_range=bill_data.get("month_range"),
                    bill_total=bill_data.get("bill_total")
                )
                
                # Process payments for this bill
                if "payments" in bill_data:
                    for i, payment_data in enumerate(bill_data["payments"]):
                        await upsert_payment(
                            payment_date=payment_data.get("payment_date", ""),
                            description=payment_data.get("description", ""),
                            amount=payment_data.get("amount", ""),
                            bill_id=bill.id,
                            scrape_order=i
                        )
        
        logger.info("Synced scraped data to normalized tables")
    except Exception as e:
        logger.warning(f"Failed to sync scraped data: {e}")

# =============================================================================
# Ledger Data
# =============================================================================

async def get_ledger_data() -> Dict[str, Any]:
    """Get complete ledger data for UI"""
    await ensure_connected()
    
    # Get current balance
    balance_record = await get_current_balance()
    account_balance = balance_record["balance"] if balance_record else "$0.00"
    
    # Get all bills with payments
    bills = await db.bill.find_many(
        order_by={"billCycleDate": "desc"},
        include={
            "payments": {
                "include": {"payeeUser": True},
                "order_by": [{"paymentDate": "desc"}]
            },
            "details": True
        }
    )
    
    bills_data = []
    for bill in bills:
        bill_dict = {
            "id": bill.id,
            "bill_cycle_date": bill.billCycleDate.strftime("%m/%d/%Y") if bill.billCycleDate else None,
            "bill_date": bill.billDate.strftime("%Y-%m-%d") if bill.billDate else None,
            "month_range": bill.monthRange,
            "bill_total": f"${decimal_to_float(bill.billTotal):.2f}" if bill.billTotal else None,
            "amount_numeric": decimal_to_float(bill.billTotal),
            "payments": [
                {
                    "id": p.id,
                    "payment_date": p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else None,
                    "description": p.description,
                    "amount": f"${decimal_to_float(p.amount):.2f}" if p.amount else None,
                    "amount_numeric": decimal_to_float(p.amount),
                    "payee_status": p.payeeStatus,
                    "payee_name": p.payeeUser.name if p.payeeUser else None,
                    "payee_user_id": p.payeeUserId,
                    "card_last_four": p.cardLastFour,
                    "bill_manually_set": p.billManuallySet,
                    "manual_order": p.manualOrder,
                }
                for p in bill.payments
            ]
        }
        bills_data.append(bill_dict)
    
    # Get orphan payments (no bill)
    orphan_payments = await db.payment.find_many(
        where={"billId": None},
        include={"payeeUser": True},
        order_by={"paymentDate": "desc"}
    )
    
    orphans = [
        {
            "id": p.id,
            "payment_date": p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else None,
            "description": p.description,
            "amount": f"${decimal_to_float(p.amount):.2f}" if p.amount else None,
            "amount_numeric": decimal_to_float(p.amount),
            "payee_status": p.payeeStatus,
            "payee_name": p.payeeUser.name if p.payeeUser else None,
        }
        for p in orphan_payments
    ]
    
    return {
        "account_balance": account_balance,
        "bills": bills_data,
        "orphan_payments": orphans,
    }

# =============================================================================
# Payee Balance Calculations
# =============================================================================

async def calculate_all_payee_balances() -> List[Dict[str, Any]]:
    """Calculate payee balances for all bills"""
    await ensure_connected()
    
    # Get all payee users
    users = await db.payeeuser.find_many()
    user_map = {u.id: u for u in users}
    
    # Get all bills
    bills = await db.bill.find_many(
        order_by={"billCycleDate": "desc"},
        include={"payments": True}
    )
    
    results = []
    rollover_by_user = {u.id: 0.0 for u in users}
    
    for bill in reversed(bills):  # Process oldest first for rollover
        bill_total = decimal_to_float(bill.billTotal) or 0
        
        bill_result = {
            "bill_id": bill.id,
            "month_range": bill.monthRange,
            "bill_cycle_date": bill.billCycleDate.strftime("%m/%d/%Y") if bill.billCycleDate else None,
            "bill_total": bill_total,
            "total_paid": 0,
            "bill_balance": bill_total,
            "payees": []
        }
        
        # Calculate payments by user
        payments_by_user = {}
        for p in bill.payments:
            user_id = p.payeeUserId or 0  # 0 for unassigned
            if user_id not in payments_by_user:
                payments_by_user[user_id] = 0
            payments_by_user[user_id] += decimal_to_float(p.amount) or 0
        
        total_paid = sum(payments_by_user.values())
        bill_result["total_paid"] = total_paid
        bill_result["bill_balance"] = bill_total - total_paid
        
        # Calculate per-user status
        for user in users:
            responsibility = user.responsibilityPercent / 100.0
            amount_due = bill_total * responsibility + rollover_by_user[user.id]
            amount_paid = payments_by_user.get(user.id, 0)
            difference = amount_paid - amount_due
            
            status = "paid"
            if difference < -0.01:
                status = "underpaid"
            elif difference > 0.01:
                status = "overpaid"
            
            # Update rollover for next bill
            rollover_by_user[user.id] = -difference if difference < 0 else 0
            
            bill_result["payees"].append({
                "user_id": user.id,
                "name": user.name,
                "responsibility_percent": user.responsibilityPercent,
                "amount_due": round(amount_due, 2),
                "amount_paid": round(amount_paid, 2),
                "difference": round(difference, 2),
                "status": status
            })
        
        results.append(bill_result)
    
    return list(reversed(results))  # Return newest first

async def get_bill_payee_summary(bill_id: int) -> Optional[Dict[str, Any]]:
    """Get payee summary for a specific bill"""
    all_summaries = await calculate_all_payee_balances()
    
    for summary in all_summaries:
        if summary["bill_id"] == bill_id:
            return summary
    
    return None

async def get_all_bill_summaries() -> List[Dict[str, Any]]:
    """Get summaries for all bills"""
    return await calculate_all_payee_balances()

# =============================================================================
# Cleanup Functions
# =============================================================================

async def wipe_bills_and_payments():
    """Delete all bills and payments"""
    await ensure_connected()
    
    await db.payment.delete_many()
    await db.billdetails.delete_many()
    await db.billdocument.delete_many()
    await db.bill.delete_many()
    
    logger.info("Wiped all bills and payments")

async def get_all_bills_with_payments() -> List[Dict[str, Any]]:
    """Get all bills with their payments for audit"""
    await ensure_connected()
    
    bills = await db.bill.find_many(
        order_by={"billCycleDate": "desc"},
        include={"payments": {"include": {"payeeUser": True}}}
    )
    
    return [
        {
            "id": b.id,
            "month_range": b.monthRange,
            "bill_cycle_date": b.billCycleDate.strftime("%m/%d/%Y") if b.billCycleDate else None,
            "bill_total": f"${decimal_to_float(b.billTotal):.2f}" if b.billTotal else None,
            "payments": [
                {
                    "id": p.id,
                    "payment_date": p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else None,
                    "amount": f"${decimal_to_float(p.amount):.2f}" if p.amount else None,
                    "payee_name": p.payeeUser.name if p.payeeUser else None,
                }
                for p in b.payments
            ]
        }
        for b in bills
    ]

async def get_payments_by_user(user_id: int) -> List[Dict[str, Any]]:
    """Get all payments for a specific user"""
    await ensure_connected()
    
    payments = await db.payment.find_many(
        where={"payeeUserId": user_id},
        include={"bill": True},
        order_by={"paymentDate": "desc"}
    )
    
    return [
        {
            "id": p.id,
            "payment_date": p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else None,
            "amount": f"${decimal_to_float(p.amount):.2f}" if p.amount else None,
            "amount_numeric": decimal_to_float(p.amount),
            "bill_month": p.bill.monthRange if p.bill else None,
        }
        for p in payments
    ]

async def auto_assign_expired_pending_payments():
    """Auto-assign payments past 2hr pending window to default payee"""
    await ensure_connected()
    
    default_payee = await get_default_payee()
    if not default_payee:
        return
    
    now = utc_now()
    
    # Find payments with expired pending window
    payments = await db.payment.find_many(
        where={
            "payeeStatus": "pending",
            "payeePendingUntil": {"lt": now}
        }
    )
    
    for p in payments:
        await db.payment.update(
            where={"id": p.id},
            data={
                "payeeUserId": default_payee["id"],
                "payeeStatus": "auto_assigned",
                "verificationMethod": "auto_pending_expired"
            }
        )
    
    if payments:
        logger.info(f"Auto-assigned {len(payments)} expired pending payments")
