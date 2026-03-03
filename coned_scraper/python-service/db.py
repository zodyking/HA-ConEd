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
from prisma import Json
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
        try:
            logger.info("Connecting to PostgreSQL database...")
            await db.connect()
            logger.info("SUCCESS: Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"FAILED to connect to PostgreSQL: {e}")
            raise

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
        order={"billCycleDate": "desc"},
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
        order={"billCycleDate": "desc"},
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
        order={"billCycleDate": "asc"},
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
    total_amount_due: Optional[float] = None,
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
        "totalAmountDue": Decimal(str(total_amount_due)) if total_amount_due is not None else None,
        "billingDays": billing_days,
        "supplyCharges": Json(supply_charges) if supply_charges is not None else None,
        "deliveryCharges": Json(delivery_charges) if delivery_charges is not None else None,
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
        include={"bill": True}
    )
    # Sort by bill cycle date descending in Python (nested order not supported)
    details_list = sorted(
        details_list,
        key=lambda d: d.bill.billCycleDate if d.bill and d.bill.billCycleDate else datetime.min,
        reverse=True
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
        include={"bill": True}
    )
    # Sort by bill cycle date descending in Python (nested order not supported)
    docs = sorted(
        docs,
        key=lambda d: d.bill.billCycleDate if d.bill and d.bill.billCycleDate else datetime.min,
        reverse=True
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
    
    bill = await db.bill.find_first(
        where={"document": {"isNot": None}},
        order={"billCycleDate": "desc"},
        include={"document": True}
    )
    
    return bill.id if bill else None

async def delete_bill_document(bill_id: int) -> bool:
    """Delete bill document"""
    await ensure_connected()
    
    try:
        await db.billdocument.delete(where={"billId": bill_id})
        return True
    except Exception:
        return False

async def get_month_ranges_with_pdf() -> set:
    """Get month_range values for bills that already have a PDF document"""
    await ensure_connected()
    docs = await db.billdocument.find_many(include={"bill": True})
    result = set()
    for d in docs:
        if d.bill and d.bill.monthRange:
            result.add(d.bill.monthRange.strip())
    return result

async def get_bill_id_by_month_range(month_range: str) -> Optional[int]:
    """Get bill id by month_range (e.g. 'JAN - FEB'). Returns most recent if multiple."""
    await ensure_connected()
    if not month_range or not month_range.strip():
        return None
    bill = await db.bill.find_first(
        where={"monthRange": month_range.strip()},
        order={"billCycleDate": "desc"}
    )
    return bill.id if bill else None

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
        order={"paymentDate": "desc"}
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
        order={"paymentDate": "desc"},
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
    latest_bill = await db.bill.find_first(order={"billCycleDate": "desc"})
    
    if not latest_bill:
        return None
    
    # Get the most recent payment for that bill
    p = await db.payment.find_first(
        where={"billId": latest_bill.id},
        order={"paymentDate": "desc"},
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
    
    latest_bill = await db.bill.find_first(order={"billCycleDate": "desc"})
    
    if not latest_bill:
        return {"bill_id": None, "payment_count": 0, "last_payment": None}
    
    count = await db.payment.count(where={"billId": latest_bill.id})
    
    last_payment = await db.payment.find_first(
        where={"billId": latest_bill.id},
        order=[
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
    
    return {"bill_id": latest_bill.id, "payment_count": count, "last_payment": last_payment_dict}

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
        order={"name": "asc"}
    )
    
    return [
        {
            "id": u.id,
            "name": u.name,
            "ha_user_id": u.haUserId,
            "notify_service": u.notifyService,
            "notifications_enabled": u.notificationsEnabled,
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

async def update_payee_notify_settings(
    user_id: int,
    ha_user_id: Optional[str] = None,
    notify_service: Optional[str] = None,
    notifications_enabled: Optional[bool] = None
) -> bool:
    """Update payee notification settings"""
    await ensure_connected()
    
    data = {}
    if ha_user_id is not None:
        data["haUserId"] = ha_user_id
    if notify_service is not None:
        data["notifyService"] = notify_service
    if notifications_enabled is not None:
        data["notificationsEnabled"] = notifications_enabled
    
    if not data:
        return False
    
    try:
        await db.payeeuser.update(where={"id": user_id}, data=data)
        return True
    except Exception:
        return False

async def get_payees_with_notifications() -> List[Dict[str, Any]]:
    """Get payees that have notifications enabled and a notify service configured"""
    await ensure_connected()
    
    users = await db.payeeuser.find_many(
        where={
            "notificationsEnabled": True,
            "notifyService": {"not": None}
        }
    )
    
    return [
        {
            "id": u.id,
            "name": u.name,
            "ha_user_id": u.haUserId,
            "notify_service": u.notifyService,
        }
        for u in users
    ]

async def create_payee_user_with_ha(
    name: str,
    ha_user_id: Optional[str] = None,
    notify_service: Optional[str] = None,
    notifications_enabled: bool = True,
    is_default: bool = False
) -> Dict[str, Any]:
    """Create a new payee user with HA integration fields"""
    await ensure_connected()
    
    if is_default:
        await db.payeeuser.update_many(
            where={"isDefault": True},
            data={"isDefault": False}
        )
    
    user = await db.payeeuser.create(
        data={
            "name": name,
            "haUserId": ha_user_id,
            "notifyService": notify_service,
            "notificationsEnabled": notifications_enabled,
            "isDefault": is_default,
            "responsibilityPercent": 0,
            "isAdmin": False
        }
    )
    
    return {
        "id": user.id,
        "name": user.name,
        "ha_user_id": user.haUserId,
        "notify_service": user.notifyService,
        "notifications_enabled": user.notificationsEnabled,
        "is_default": user.isDefault,
    }

# =============================================================================
# Notification Config
# =============================================================================

DEFAULT_NOTIFICATION_CONFIGS = [
    {
        "event_type": "new_bill",
        "title": "Con Edison Billing",
        "template": "A new bill for {amount} has posted, due {due_date}",
    },
    {
        "event_type": "payment_received",
        "title": "Con Edison Payment",
        "template": "Payment of {amount} received. Remaining balance: {balance}",
    },
    {
        "event_type": "due_reminder",
        "title": "Con Edison Reminder",
        "template": "Your bill of {amount} is due in {days_until} days on {due_date}",
        "days_before_due": 3,
    },
    {
        "event_type": "balance_change",
        "title": "Con Edison Balance",
        "template": "Your account balance changed from {old_balance} to {new_balance}",
    },
]

async def get_notification_config(event_type: str) -> Optional[Dict[str, Any]]:
    """Get notification config for a specific event type"""
    await ensure_connected()
    
    config = await db.notificationconfig.find_unique(where={"eventType": event_type})
    
    if not config:
        return None
    
    return {
        "id": config.id,
        "event_type": config.eventType,
        "enabled": config.enabled,
        "title": config.title,
        "template": config.template,
        "days_before_due": config.daysBeforeDue,
    }

async def get_all_notification_configs() -> List[Dict[str, Any]]:
    """Get all notification configs, creating defaults if needed"""
    await ensure_connected()
    
    configs = await db.notificationconfig.find_many()
    
    if not configs:
        for default_config in DEFAULT_NOTIFICATION_CONFIGS:
            await db.notificationconfig.create(
                data={
                    "eventType": default_config["event_type"],
                    "title": default_config["title"],
                    "template": default_config["template"],
                    "daysBeforeDue": default_config.get("days_before_due"),
                    "enabled": True,
                }
            )
        configs = await db.notificationconfig.find_many()
    
    return [
        {
            "id": c.id,
            "event_type": c.eventType,
            "enabled": c.enabled,
            "title": c.title,
            "template": c.template,
            "days_before_due": c.daysBeforeDue,
        }
        for c in configs
    ]

async def update_notification_config(
    event_type: str,
    enabled: Optional[bool] = None,
    title: Optional[str] = None,
    template: Optional[str] = None,
    days_before_due: Optional[int] = None
) -> bool:
    """Update a notification config"""
    await ensure_connected()
    
    data = {}
    if enabled is not None:
        data["enabled"] = enabled
    if title is not None:
        data["title"] = title
    if template is not None:
        data["template"] = template
    if days_before_due is not None:
        data["daysBeforeDue"] = days_before_due
    
    if not data:
        return False
    
    try:
        await db.notificationconfig.update(
            where={"eventType": event_type},
            data=data
        )
        return True
    except Exception:
        return False

async def ensure_notification_configs_exist():
    """Ensure default notification configs exist in database"""
    await ensure_connected()
    
    for default_config in DEFAULT_NOTIFICATION_CONFIGS:
        existing = await db.notificationconfig.find_unique(
            where={"eventType": default_config["event_type"]}
        )
        if not existing:
            await db.notificationconfig.create(
                data={
                    "eventType": default_config["event_type"],
                    "title": default_config["title"],
                    "template": default_config["template"],
                    "daysBeforeDue": default_config.get("days_before_due"),
                    "enabled": True,
                }
            )

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
    prev = await db.accountbalancehistory.find_first(order={"scrapedAt": "desc"})
    
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
    
    balance = await db.accountbalancehistory.find_first(order={"scrapedAt": "desc"})
    
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
            "data": Json(data),
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
        order={"timestamp": "desc"},
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
    
    records = await db.scrapeddata.find_many(order={"timestamp": "desc"})
    
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
        order={"timestamp": "desc"},
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
            order={"timestamp": "asc"},
            take=count - 100
        )
        for record in oldest:
            await db.scrapehistory.delete(where={"id": record.id})

async def get_scrape_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent scrape history"""
    await ensure_connected()
    
    history = await db.scrapehistory.find_many(
        order={"timestamp": "desc"},
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
    
    # Wrap value with Json() for Prisma JSON fields
    json_value = Json(value)
    
    if existing:
        await db.appsetting.update(where={"key": key}, data={"value": json_value})
    else:
        await db.appsetting.create(data={"key": key, "value": json_value})

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
    """Get cached realtime readings from dedicated table (last 96 = 24h of 15-min intervals)"""
    await ensure_connected()
    rows = await db.realtimereading.find_many(order={"endTime": "desc"}, take=96)
    if not rows:
        return None
    # Return ascending by start_time for chart
    rows = list(reversed(rows))
    return [
        {
            "start_time": r.startTime.isoformat(),
            "end_time": r.endTime.isoformat(),
            "consumption": float(r.consumption),
        }
        for r in rows
    ]


async def save_realtime_readings_db(readings: List[Dict[str, Any]]):
    """Save realtime readings to dedicated table (replaces previous cache)"""
    await ensure_connected()
    from datetime import datetime
    # Delete all existing readings (we replace with fresh fetch)
    await db.realtimereading.delete_many()
    if not readings:
        return
    # Limit to last 96 (24h of 15-min intervals)
    to_save = readings[-96:] if len(readings) > 96 else readings
    data_list = []
    for r in to_save:
        start_str = r.get("start_time") or ""
        end_str = r.get("end_time") or ""
        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        data_list.append({
            "startTime": start_dt,
            "endTime": end_dt,
            "consumption": float(r.get("consumption", 0) or 0),
        })
    if data_list:
        await db.realtimereading.create_many(data=data_list)

# =============================================================================
# Credentials (migrated from file to database)
# =============================================================================

async def get_credentials_db() -> Optional[Dict[str, Any]]:
    """Get encrypted credentials from database"""
    return await get_app_setting("credentials")

async def save_credentials_db(credentials: Dict[str, Any]):
    """Save encrypted credentials to database"""
    await set_app_setting("credentials", credentials)

# =============================================================================
# App Settings (time offset, etc.) - migrated from file to database
# =============================================================================

async def get_app_settings_db() -> Optional[Dict[str, Any]]:
    """Get app settings from database"""
    return await get_app_setting("app_settings")

async def save_app_settings_db(settings: Dict[str, Any]):
    """Save app settings to database"""
    await set_app_setting("app_settings", settings)

# =============================================================================
# Schedule Config (migrated from file to database)
# =============================================================================

async def get_schedule_config_db() -> Optional[Dict[str, Any]]:
    """Get schedule config from database"""
    return await get_app_setting("schedule_config")

async def save_schedule_config_db(config: Dict[str, Any]):
    """Save schedule config to database"""
    await set_app_setting("schedule_config", config)

# =============================================================================
# Payment State (migrated from file to database)
# =============================================================================

async def get_payment_state_db() -> Optional[Dict[str, Any]]:
    """Get last payment state from database"""
    return await get_app_setting("payment_state")

async def save_payment_state_db(state: Dict[str, Any]):
    """Save payment state to database"""
    await set_app_setting("payment_state", state)

# =============================================================================
# TTS States (migrated from file to database)
# =============================================================================

async def get_tts_payment_state_db() -> Optional[Dict[str, Any]]:
    """Get TTS payment state from database"""
    return await get_app_setting("tts_payment_state")

async def save_tts_payment_state_db(state: Dict[str, Any]):
    """Save TTS payment state to database"""
    await set_app_setting("tts_payment_state", state)

async def get_tts_bill_state_db() -> Optional[Dict[str, Any]]:
    """Get TTS bill state from database"""
    return await get_app_setting("tts_bill_state")

async def save_tts_bill_state_db(state: Dict[str, Any]):
    """Save TTS bill state to database"""
    await set_app_setting("tts_bill_state", state)

# =============================================================================
# Payment-to-Bill Relinking (database relational logic)
# =============================================================================

async def relink_payments_to_bills() -> int:
    """
    Assign orphan payments to bills using date logic: a payment belongs to the bill
    where bill_date <= payment_date < next_bill_date (bill is posted, then payments follow).
    Persists bill_id in the database.
    """
    await ensure_connected()
    
    # Bills sorted by marker date ascending (oldest first)
    bills = await db.bill.find_many(order={"billCycleDate": "asc"}, include={})
    if not bills:
        return 0
    
    # Build (marker_date, bill_id) - use bill_date as marker, fallback to bill_cycle_date
    def _marker(b):
        if b.billDate:
            d = b.billDate
        else:
            d = b.billCycleDate
        return (d.replace(tzinfo=timezone.utc) if d and d.tzinfo is None else d, b.id)
    
    markers = [_marker(b) for b in bills]
    markers = [(d, bid) for d, bid in markers if d]
    markers.sort(key=lambda x: x[0])
    
    # Get orphan payments (skip manually assigned)
    orphans = await db.payment.find_many(
        where={"billId": None, "billManuallySet": False},
        order={"paymentDate": "asc"}
    )
    
    updated = 0
    for p in orphans:
        payment_dt = p.paymentDate
        if not payment_dt:
            continue
        if payment_dt.tzinfo is None:
            payment_dt = payment_dt.replace(tzinfo=timezone.utc)
        
        # Find bill where bill_date <= payment_date < next_bill_date
        # = largest bill_date <= payment_date
        candidates = [(d, bid) for d, bid in markers if d <= payment_dt]
        if candidates:
            bill_id = candidates[-1][1]
        else:
            # Payment before all bills - assign to oldest
            bill_id = markers[0][1]
        
        await db.payment.update(where={"id": p.id}, data={"billId": bill_id})
        updated += 1
    
    if updated:
        logger.info(f"Relinked {updated} payments to bills by date logic")
    return updated


# =============================================================================
# Data Sync
# =============================================================================

async def sync_from_scrape(data: Dict[str, Any]):
    """Sync scraped data to normalized tables"""
    try:
        # Record balance
        if "account_balance" in data:
            await record_account_balance(data["account_balance"])
        
        # Process bills (nested format: bills with payments inside)
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
        
        # Process bill_history.ledger format (flat list from ConEd scraper)
        bill_history = data.get("bill_history") or {}
        ledger = bill_history.get("ledger") or []
        if ledger:
            # First pass: upsert all bills
            for item in ledger:
                if item.get("type") != "bill":
                    continue
                bill_cycle = item.get("bill_cycle_date") or ""
                month_range = item.get("month_range") or ""
                if not bill_cycle and not item.get("bill_total"):
                    continue
                await upsert_bill(
                    bill_cycle_date=bill_cycle,
                    bill_date=item.get("bill_date"),
                    month_range=month_range,
                    bill_total=item.get("bill_total")
                )
            
            # Second pass: upsert payments (bill_id assigned by relink after)
            # Use bill_cycle_date as fallback for payment_date - ConEd often doesn't show
            # exact payment date in description, so without this we'd default to utc_now()
            payment_order = 0
            for item in ledger:
                if item.get("type") != "payment":
                    continue
                bill_cycle = item.get("bill_cycle_date") or ""
                if not bill_cycle and not item.get("amount"):
                    continue
                payment_date = item.get("payment_date") or bill_cycle
                await upsert_payment(
                    payment_date=payment_date,
                    description=item.get("description") or "Payment Received",
                    amount=item.get("amount") or "0",
                    bill_id=None,  # Relink assigns by date logic
                    scrape_order=payment_order
                )
                payment_order += 1
            
            # Relink: assign payments to bills by database logic (bill_date markers)
            await relink_payments_to_bills()
            
            logger.info(f"Synced {len([i for i in ledger if i.get('type')=='bill'])} bills and {len([i for i in ledger if i.get('type')=='payment'])} payments from ledger")
        elif "bills" in data:
            logger.info("Synced scraped data to normalized tables")
    except Exception as e:
        logger.warning(f"Failed to sync scraped data: {e}")

# =============================================================================
# Ledger Data
# =============================================================================

async def get_ledger_data() -> Dict[str, Any]:
    """Get complete ledger data for UI"""
    await ensure_connected()
    from data_config import DATA_DIR

    # Get current balance
    balance_record = await get_current_balance()
    account_balance = balance_record["balance"] if balance_record else "$0.00"
    
    # Get all bills with payments and documents
    bills = await db.bill.find_many(
        order={"billCycleDate": "desc"},
        include={
            "payments": {"include": {"payeeUser": True}},
            "details": True,
            "document": True,
        }
    )
    # Sort payments within each bill by date descending (nested order not supported in include)
    for bill in bills:
        if bill.payments:
            bill.payments.sort(key=lambda p: p.paymentDate if p.paymentDate else datetime.min, reverse=True)
    
    bills_data = []
    for bill in bills:
        pdf_exists = False
        pdf_source_url = None
        if bill.document:
            full_path = DATA_DIR / bill.document.pdfPath
            pdf_exists = full_path.is_file() if full_path else False
            pdf_source_url = bill.document.sourceUrl
        due_date_str = None
        if bill.details and bill.details.dueDate:
            due_date_str = bill.details.dueDate.strftime("%b %d, %Y")
        bill_dict = {
            "id": bill.id,
            "bill_cycle_date": bill.billCycleDate.strftime("%m/%d/%Y") if bill.billCycleDate else None,
            "bill_date": bill.billDate.strftime("%Y-%m-%d") if bill.billDate else None,
            "month_range": bill.monthRange,
            "bill_total": f"${decimal_to_float(bill.billTotal):.2f}" if bill.billTotal else None,
            "amount_numeric": decimal_to_float(bill.billTotal),
            "due_date": due_date_str,
            "pdf_exists": pdf_exists,
            "pdf_source_url": pdf_source_url,
            "payments": [
                {
                    "id": p.id,
                    "payment_date": p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else None,
                    "description": p.description,
                    "amount": f"${decimal_to_float(p.amount):.2f}" if p.amount else None,
                    "amount_numeric": decimal_to_float(p.amount),
                    "payee_status": p.payeeStatus or "unverified",
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
    
    # Get orphan payments (no bill) - merge into correct bills for display
    # They show under the bill with status Unverified, no separate section
    orphan_payments = await db.payment.find_many(
        where={"billId": None},
        include={"payeeUser": True},
        order={"paymentDate": "desc"}
    )
    
    if orphan_payments and bills_data:
        bills_by_date = [(parse_date(b.get("bill_cycle_date") or ""), b) for b in bills_data]
        bills_by_date = [(d, b) for d, b in bills_by_date if d]
        bills_by_date.sort(key=lambda x: x[0])
        
        for p in orphan_payments:
            payment_dt = p.paymentDate
            if not payment_dt:
                continue
            if payment_dt.tzinfo is None:
                payment_dt = payment_dt.replace(tzinfo=timezone.utc)
            payment_dict = {
                "id": p.id,
                "payment_date": p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else None,
                "description": p.description or "Payment Received",
                "amount": f"${decimal_to_float(p.amount):.2f}" if p.amount else None,
                "amount_numeric": decimal_to_float(p.amount),
                "payee_status": p.payeeStatus or "unverified",
                "payee_name": p.payeeUser.name if p.payeeUser else None,
                "payee_user_id": p.payeeUserId,
                "card_last_four": p.cardLastFour,
            }
            # Match to bill: largest cycle_date <= payment date
            candidates = [(d, b) for d, b in bills_by_date if d <= payment_dt]
            if candidates:
                target_bill = candidates[-1][1]
            else:
                target_bill = bills_by_date[0][1]
            target_bill["payments"].append(payment_dict)
        
        # Re-sort payments within each bill
        for b in bills_data:
            b["payments"].sort(
                key=lambda p: parse_date(p.get("payment_date") or "") or datetime.min,
                reverse=True
            )

    # Include payee summaries in ledger response for fast frontend loading
    raw_summaries = await calculate_all_payee_balances()
    payee_summaries = _format_payee_summaries_for_frontend(raw_summaries)

    return {
        "account_balance": account_balance,
        "bills": bills_data,
        "orphan_payments": [],  # No separate section - merged into bills
        "payee_summaries": payee_summaries,
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
        order={"billCycleDate": "desc"},
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
            share_current = bill_total * responsibility  # Current bill only - default view
            amount_due = bill_total * responsibility + rollover_by_user[user.id]  # Cumulative with rollover
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
                "share_of_bill": round(share_current, 2),
                "share_of_bill_cumulative": round(amount_due, 2),
                "amount_paid": round(amount_paid, 2),
                "difference": round(difference, 2),
                "status": status
            })
        
        results.append(bill_result)
    
    return list(reversed(results))  # Return newest first


def _format_payee_summaries_for_frontend(raw: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Transform calculate_all_payee_balances output to BillPayeeSummary format, keyed by bill_id"""
    out: Dict[int, Dict[str, Any]] = {}
    for s in raw:
        bid = s.get("bill_id")
        if bid is None:
            continue
        bill_total = s.get("bill_total") or 0
        total_paid = s.get("total_paid") or 0
        bill_balance = s.get("bill_balance") or 0
        if bill_balance < 0.01:
            bill_status = "paid"
        elif total_paid > 0.01:
            bill_status = "partial"
        else:
            bill_status = "unpaid"
        payee_summaries = [
            {
                "user_id": p["user_id"],
                "name": p["name"],
                "responsibility_percent": p["responsibility_percent"],
                "amount_owed": p.get("share_of_bill", 0),
                "amount_paid": p.get("amount_paid", 0),
                "share_of_bill": p.get("share_of_bill", 0),
                "share_of_bill_cumulative": p.get("share_of_bill_cumulative", 0),
                "rollover_from_previous": 0,
                "current_balance": 0,
                "status": "paid" if p.get("status") == "paid" else "partial" if p.get("status") == "overpaid" else "unpaid",
            }
            for p in s.get("payees") or []
        ]
        out[bid] = {
            "bill_id": bid,
            "bill_total": bill_total,
            "total_paid": total_paid,
            "bill_balance": bill_balance,
            "bill_status": bill_status,
            "payee_summaries": payee_summaries,
        }
    return out


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

async def wipe_bills_and_payments() -> Dict[str, int]:
    """Delete all bills and payments. Returns counts deleted."""
    await ensure_connected()
    
    pb = await db.payment.delete_many()
    await db.billdetails.delete_many()
    await db.billdocument.delete_many()
    bb = await db.bill.delete_many()
    
    bills_deleted = getattr(bb, "count", 0) or 0
    payments_deleted = getattr(pb, "count", 0) or 0
    logger.info("Wiped all bills and payments")
    return {"bills_deleted": bills_deleted, "payments_deleted": payments_deleted}

async def get_all_bills_with_payments() -> Dict[str, Any]:
    """Get all bills with their payments and orphan payments for audit tab"""
    await ensure_connected()
    
    bills = await db.bill.find_many(
        order={"billCycleDate": "desc"},
        include={"payments": {"include": {"payeeUser": True}}}
    )
    
    bills_data = [
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
                    "payee_user_id": p.payeeUserId,
                    "payee_status": p.payeeStatus or "unverified",
                    "bill_id": p.billId,
                }
                for p in b.payments
            ]
        }
        for b in bills
    ]
    
    orphan_payments = await db.payment.find_many(
        where={"billId": None},
        include={"payeeUser": True},
        order={"paymentDate": "desc"}
    )
    
    orphan_data = [
        {
            "id": p.id,
            "payment_date": p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else None,
            "amount": f"${decimal_to_float(p.amount):.2f}" if p.amount else None,
            "payee_name": p.payeeUser.name if p.payeeUser else None,
            "payee_user_id": p.payeeUserId,
            "payee_status": p.payeeStatus or "unverified",
            "bill_id": None,
        }
        for p in orphan_payments
    ]
    
    return {"bills": bills_data, "orphan_payments": orphan_data}

async def get_payments_by_user(user_id: int) -> List[Dict[str, Any]]:
    """Get all payments for a specific user"""
    await ensure_connected()
    
    payments = await db.payment.find_many(
        where={"payeeUserId": user_id},
        include={"bill": True},
        order={"paymentDate": "desc"}
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
