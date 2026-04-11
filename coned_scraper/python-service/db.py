"""
Database module using Prisma ORM with PostgreSQL.
Provides async database operations for the ConEd Scraper addon.
"""
import json
import logging
import hashlib
import re
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

from prisma import Prisma
from prisma import Json
from prisma.models import (
    Bill, Payment, BillDetails, BillDocument, PayeeUser,
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

async def run_migrations():
    """Run pending database migrations on startup."""
    try:
        import asyncpg
        import os
        
        database_url = os.environ.get("DATABASE_URL", "")
        if not database_url:
            logger.warning("DATABASE_URL not set, skipping migrations")
            return
        
        conn = await asyncpg.connect(database_url)
        try:
            # Migration: Add reminder_send_time to notification_configs
            await conn.execute("""
                ALTER TABLE notification_configs 
                ADD COLUMN IF NOT EXISTS reminder_send_time TEXT DEFAULT '09:00'
            """)
            
            # Migration: Create due_reminder_sent table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS due_reminder_sent (
                    id SERIAL PRIMARY KEY,
                    bill_id INTEGER NOT NULL,
                    sent_date TIMESTAMP(3) NOT NULL,
                    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS due_reminder_sent_bill_id_sent_date_key 
                ON due_reminder_sent(bill_id, sent_date)
            """)
            
            # Migration: Drop user_cards table (card feature removed)
            await conn.execute("DROP TABLE IF EXISTS user_cards CASCADE")
            
            # Migration: Payment claim responses (notification-based assignment)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payment_claim_responses (
                    id SERIAL PRIMARY KEY,
                    payment_id INTEGER NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
                    payee_id INTEGER NOT NULL REFERENCES payee_users(id) ON DELETE CASCADE,
                    claimed BOOLEAN NOT NULL,
                    responded_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(payment_id, payee_id)
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS payment_claim_responses_payment_id_idx 
                ON payment_claim_responses(payment_id)
            """)
            
            # Migration: Payment petitions (dispute/claim after assignment)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payment_petitions (
                    id SERIAL PRIMARY KEY,
                    payment_id INTEGER NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
                    petitioning_payee_id INTEGER NOT NULL REFERENCES payee_users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS payment_petitions_payment_id_idx 
                ON payment_petitions(payment_id)
            """)
            
            # Migration: Unique constraint on realtime_readings for upsert/append
            await conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS realtime_readings_start_end_key 
                ON realtime_readings(start_time, end_time)
            """)
            
            logger.info("Database migrations completed successfully")
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Migration check failed (may already exist): {e}")


async def connect():
    """Connect to the database"""
    if not db.is_connected():
        try:
            logger.info("Connecting to PostgreSQL database...")
            await run_migrations()
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

async def _raw_conn():
    """Get asyncpg connection for raw SQL (claim/petition tables)."""
    import asyncpg
    import os
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return await asyncpg.connect(url)

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
    """Get payments with unverified or needs_admin_verification status"""
    await ensure_connected()
    
    payments = await db.payment.find_many(
        where={"payeeStatus": {"in": ["unverified", "needs_admin_verification"]}},
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
            "payee_status": p.payeeStatus,
        }
        for p in payments
    ]

# =============================================================================
# Payment Claim Responses (notification-based assignment)
# =============================================================================

async def record_payment_claim_response(payment_id: int, payee_id: int, claimed: bool) -> Dict[str, Any]:
    """
    Record a payee's Yes/No response to a payment claim. Runs resolution logic after.
    Returns: {ok: bool, assignment?: {payee_id, payee_name, amount, payment_date}} when assignment occurs.
    """
    await ensure_connected()
    try:
        conn = await _raw_conn()
        try:
            await conn.execute(
                """
                INSERT INTO payment_claim_responses (payment_id, payee_id, claimed)
                VALUES ($1, $2, $3)
                ON CONFLICT (payment_id, payee_id) DO UPDATE SET claimed = $3, responded_at = NOW()
                """,
                payment_id, payee_id, claimed
            )
            assignment = await run_claim_resolution(payment_id, conn=conn)
            return {"ok": True, "assignment": assignment}
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Failed to record claim response: {e}")
        return {"ok": False}

async def run_claim_resolution(payment_id: int, conn=None) -> Optional[Dict[str, Any]]:
    """
    Run assignment resolution after each Yes/No response.
    1. Eliminate No payees from pool
    2. 1 Yes -> assign to that payee
    3. 2+ Yes -> needs_admin_verification
    4. Only 1 non-responder left -> assign to that payee
    5. All No -> schedule resend (handled by separate task)
    """
    import os
    own_conn = False
    if conn is None:
        conn = await _raw_conn()
        own_conn = True
    try:
        # Get payment
        p = await db.payment.find_unique(where={"id": payment_id}, include={"payeeUser": True})
        if not p or p.payeeStatus not in ("unverified", "needs_admin_verification"):
            return
        # Get payees with notifications (candidate pool)
        payees = await db.payeeuser.find_many(where={"notificationsEnabled": True, "notifyService": {"not": None}})
        payee_ids = [u.id for u in payees]
        if not payee_ids:
            return
        # Get responses
        rows = await conn.fetch(
            "SELECT payee_id, claimed FROM payment_claim_responses WHERE payment_id = $1",
            payment_id
        )
        responded = {r["payee_id"]: r["claimed"] for r in rows}
        yes_ids = [pid for pid, claimed in responded.items() if claimed]
        no_ids = [pid for pid, claimed in responded.items() if not claimed]
        non_responders = [pid for pid in payee_ids if pid not in responded]
        payee_id_to_name = {u.id: getattr(u, "name", "Unknown") for u in payees}
        amount_str = f"${decimal_to_float(p.amount):.2f}" if p.amount else "N/A"
        payment_date_str = p.paymentDate.strftime("%m/%d/%Y") if p.paymentDate else "N/A"
        # Eliminate No from pool
        if len(yes_ids) == 1:
            assigned_id = yes_ids[0]
            await attribute_payment(payment_id, assigned_id, "verified", "notification_claim")
            return {
                "payee_id": assigned_id,
                "payee_name": payee_id_to_name.get(assigned_id, "Unknown"),
                "amount": amount_str,
                "payment_date": payment_date_str,
            }
        if len(yes_ids) >= 2:
            await db.payment.update(where={"id": payment_id}, data={"payeeStatus": "needs_admin_verification"})
            return None
        if len(non_responders) == 1 and len(yes_ids) == 0:
            app_settings = await get_app_setting("app_settings")
            pv = (app_settings or {}).get("payment_verification") or {}
            auto_assign = pv.get("auto_assign_single_non_responder", True)
            if auto_assign:
                assigned_id = non_responders[0]
                await attribute_payment(payment_id, assigned_id, "verified", "notification_claim_single_remaining")
                return {
                    "payee_id": assigned_id,
                    "payee_name": payee_id_to_name.get(assigned_id, "Unknown"),
                    "amount": amount_str,
                    "payment_date": payment_date_str,
                }
            return None
        # All said No: nothing to do here; resend task handles it
        return None
    finally:
        if own_conn:
            await conn.close()

async def get_claim_responses(payment_id: int) -> List[Dict[str, Any]]:
    """Get all claim responses for a payment."""
    conn = await _raw_conn()
    try:
        rows = await conn.fetch(
            """SELECT pcr.payee_id, pcr.claimed, pcr.responded_at, pu.name
               FROM payment_claim_responses pcr
               JOIN payee_users pu ON pu.id = pcr.payee_id
               WHERE pcr.payment_id = $1""",
            payment_id
        )
        return [{"payee_id": r["payee_id"], "claimed": r["claimed"], "responded_at": r["responded_at"].isoformat(), "payee_name": r["name"]} for r in rows]
    finally:
        await conn.close()

async def get_unverified_payments_with_no_claim_responses() -> List[Dict[str, Any]]:
    """Unverified payments that have never had claim notifications sent (no responses yet)."""
    conn = await _raw_conn()
    try:
        rows = await conn.fetch("""
            SELECT p.id, p.payment_date, p.amount, p.description, p.bill_id
            FROM payments p
            LEFT JOIN payment_claim_responses pcr ON pcr.payment_id = p.id
            WHERE p.payee_status = 'unverified' AND pcr.id IS NULL
        """)
        return [
            {
                "id": r["id"],
                "payment_date": r["payment_date"].strftime("%m/%d/%Y") if r["payment_date"] else None,
                "amount": f"${float(r['amount']):.2f}" if r["amount"] else None,
                "amount_numeric": float(r["amount"]),
                "description": r["description"],
                "bill_id": r["bill_id"],
            }
            for r in rows
        ]
    finally:
        await conn.close()

async def get_payments_for_claim_resend(claim_resend_delay_hours: int = 24) -> List[Dict[str, Any]]:
    """
    Payments where all notified payees said No and the delay has passed.
    Returns list for resend: we will delete responses and resend.
    """
    conn = await _raw_conn()
    try:
        payees = await db.payeeuser.find_many(where={"notificationsEnabled": True, "notifyService": {"not": None}})
        payee_ids = set(u.id for u in payees)
        if not payee_ids:
            return []
        rows = await conn.fetch("""
            SELECT p.id, p.payment_date, p.amount, p.description,
                   MAX(pcr.responded_at) as last_response
            FROM payments p
            JOIN payment_claim_responses pcr ON pcr.payment_id = p.id
            WHERE p.payee_status = 'unverified'
            GROUP BY p.id, p.payment_date, p.amount, p.description
            HAVING COUNT(DISTINCT pcr.payee_id) = (
                SELECT COUNT(*) FROM payee_users WHERE notifications_enabled = true AND notify_service IS NOT NULL
            )
            AND NOT EXISTS (SELECT 1 FROM payment_claim_responses WHERE payment_id = p.id AND claimed = true)
        """)
        result = []
        from datetime import timedelta
        cutoff = utc_now() - timedelta(hours=claim_resend_delay_hours)
        for r in rows:
            if r["last_response"]:
                lr = r["last_response"]
                lr_aware = lr.replace(tzinfo=timezone.utc) if lr.tzinfo is None else lr
                if lr_aware <= cutoff:
                    result.append({
                        "id": r["id"],
                        "payment_date": r["payment_date"].strftime("%m/%d/%Y") if r["payment_date"] else None,
                        "amount": f"${float(r['amount']):.2f}" if r["amount"] else None,
                        "amount_numeric": float(r["amount"]),
                        "description": r["description"],
                    })
        return result
    finally:
        await conn.close()

async def reset_claim_responses_for_resend(payment_id: int) -> bool:
    """Delete all claim responses for a payment so we can resend notifications."""
    conn = await _raw_conn()
    try:
        await conn.execute("DELETE FROM payment_claim_responses WHERE payment_id = $1", payment_id)
        return True
    except Exception:
        return False
    finally:
        await conn.close()

async def create_payment_petition(payment_id: int, payee_id: int) -> bool:
    """Record a petition (payee disputing assignment). Does not change payment attribution; assignee is notified."""
    await ensure_connected()
    try:
        conn = await _raw_conn()
        try:
            await conn.execute(
                "DELETE FROM payment_petitions WHERE payment_id = $1 AND petitioning_payee_id = $2",
                payment_id,
                payee_id,
            )
            await conn.execute(
                "INSERT INTO payment_petitions (payment_id, petitioning_payee_id) VALUES ($1, $2)",
                payment_id,
                payee_id,
            )
            return True
        finally:
            await conn.close()
    except Exception:
        return False


async def delete_payment_petition_pair(payment_id: int, petitioning_payee_id: int) -> bool:
    """Remove a petition row after assignee responds (Yes or No)."""
    conn = await _raw_conn()
    try:
        await conn.execute(
            "DELETE FROM payment_petitions WHERE payment_id = $1 AND petitioning_payee_id = $2",
            payment_id,
            petitioning_payee_id,
        )
        return True
    except Exception:
        return False
    finally:
        await conn.close()


async def has_payment_petition(payment_id: int, petitioning_payee_id: int) -> bool:
    """Whether an open petition exists for this payment and petitioner."""
    conn = await _raw_conn()
    try:
        row = await conn.fetchrow(
            "SELECT 1 FROM payment_petitions WHERE payment_id = $1 AND petitioning_payee_id = $2 LIMIT 1",
            payment_id,
            petitioning_payee_id,
        )
        return row is not None
    finally:
        await conn.close()

async def get_payment_petitions(payment_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get petitions, optionally filtered by payment_id."""
    conn = await _raw_conn()
    try:
        if payment_id:
            rows = await conn.fetch(
                """SELECT pp.id, pp.payment_id, pp.petitioning_payee_id, pp.created_at, pu.name as payee_name
                   FROM payment_petitions pp
                   JOIN payee_users pu ON pu.id = pp.petitioning_payee_id
                   WHERE pp.payment_id = $1""",
                payment_id
            )
        else:
            rows = await conn.fetch(
                """SELECT pp.id, pp.payment_id, pp.petitioning_payee_id, pp.created_at, pu.name as payee_name
                   FROM payment_petitions pp
                   JOIN payee_users pu ON pu.id = pp.petitioning_payee_id
                   ORDER BY pp.created_at DESC"""
            )
        return [
            {
                "id": r["id"],
                "payment_id": r["payment_id"],
                "petitioning_payee_id": r["petitioning_payee_id"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "payee_name": r["payee_name"],
            }
            for r in rows
        ]
    finally:
        await conn.close()


async def get_active_petition_for_payee(payee_id: int) -> Optional[Dict[str, Any]]:
    """Get the active petition for a payee (if any). Only one petition per payee allowed."""
    conn = await _raw_conn()
    try:
        row = await conn.fetchrow(
            """SELECT pp.id, pp.payment_id, pp.petitioning_payee_id, pp.created_at,
                      p.amount, p.payment_date, p.payee_user_id as assignee_id
               FROM payment_petitions pp
               JOIN payments p ON p.id = pp.payment_id
               WHERE pp.petitioning_payee_id = $1
               LIMIT 1""",
            payee_id,
        )
        if not row:
            return None
        return {
            "id": row["id"],
            "payment_id": row["payment_id"],
            "petitioning_payee_id": row["petitioning_payee_id"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "amount": row["amount"],
            "payment_date": row["payment_date"],
            "assignee_id": row["assignee_id"],
        }
    finally:
        await conn.close()


async def cancel_petition(payment_id: int, petitioning_payee_id: int) -> bool:
    """Cancel/delete a petition. Returns True if a row was deleted."""
    conn = await _raw_conn()
    try:
        result = await conn.execute(
            "DELETE FROM payment_petitions WHERE payment_id = $1 AND petitioning_payee_id = $2",
            payment_id,
            petitioning_payee_id,
        )
        return result == "DELETE 1"
    except Exception:
        return False
    finally:
        await conn.close()


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

async def get_payee_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Single payee for notifications / petition flow."""
    await ensure_connected()
    u = await db.payeeuser.find_unique(where={"id": user_id})
    if not u:
        return None
    return {
        "id": u.id,
        "name": u.name,
        "ha_user_id": u.haUserId,
        "notify_service": u.notifyService,
        "notifications_enabled": u.notificationsEnabled,
    }


async def get_payee_users() -> List[Dict[str, Any]]:
    """Get all payee users"""
    await ensure_connected()
    
    users = await db.payeeuser.find_many(order={"name": "asc"})
    
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
    notifications_enabled: Optional[bool] = None,
    clear_ha_user: bool = False
) -> bool:
    """Update payee notification settings"""
    await ensure_connected()
    
    data = {}
    if clear_ha_user:
        data["haUserId"] = None
    elif ha_user_id is not None:
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
        "template": "Your bill of {amount} is due {days_until_text} on {due_date}",
        "days_before_due": 3,
        "reminder_send_time": "09:00",
    },
    {
        "event_type": "balance_change",
        "title": "Con Edison Balance",
        "template": "Your account balance changed from {old_balance} to {new_balance}",
    },
    {
        "event_type": "late_fee",
        "title": "Con Edison Late Fee",
        "template": "{late_fee_amount} has been added to your account balance as a late fee charge. To avoid late fees pay bill by the due date.",
    },
    {
        "event_type": "payment_claimed",
        "title": "Con Edison Payment Claimed",
        "template": "{payee_name} has claimed a payment of {amount} made on {payment_date}. If this was in error you can unclaim the payment via the account ledger.",
    },
    {
        "event_type": "payment_unclaimed",
        "title": "Con Edison Payment Unclaimed",
        "template": "{payee_name} has unclaimed a payment of {amount} made on {payment_date}. If this was in error you can claim the payment via the account ledger.",
    },
    {
        "event_type": "payment_claim_prompt",
        "title": "Payment to claim",
        "template": "Did you make the {amount} payment on {payment_date}? (Tap & hold to respond)",
    },
    {
        "event_type": "petition_assignee_question",
        "title": "Payment Petition",
        "template": "{petitioner_name} claims the {amount} payment on {payment_date}. Did you make it? (Tap & Hold To Respond)",
    },
    {
        "event_type": "petition_resolved_no_change",
        "title": "Petition Resolved",
        "template": "{payee_name} confirmed the {amount} payment on {payment_date} is theirs. No changes made.",
    },
    {
        "event_type": "petition_submitted",
        "title": "Petition Sent",
        "template": "Your petition for the {amount} payment on {payment_date} was sent to {assignee_name}.",
    },
    {
        "event_type": "petition_reassigned_to_you",
        "title": "Payment Reassigned",
        "template": "The {amount} payment on {payment_date} has been reassigned to you.",
    },
    {
        "event_type": "petition_lost",
        "title": "Payment Reassigned",
        "template": "Per your response, the {amount} payment on {payment_date} was reassigned to {petitioner_name}.",
    },
    {
        "event_type": "petition_cancelled",
        "title": "Petition Closed",
        "template": "The petition for the {amount} payment on {payment_date} has been closed.",
    },
    {
        "event_type": "payee_balance_reminder",
        "title": "Con Edison Balance",
        "template": "{payee_name}, you have a remaining balance of {remaining_balance} and {days_remaining_cycle} days to make a payment before the billing cycle ends.",
        "reminder_send_time": "09:00",
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
        "reminder_send_time": getattr(config, "reminderSendTime", None) or "09:00",
    }

async def get_all_notification_configs() -> List[Dict[str, Any]]:
    """Get all notification configs, creating defaults if needed"""
    await ensure_connected()
    
    # Ensure any new default configs (e.g. late_fee) exist for existing installs
    await ensure_notification_configs_exist()
    
    configs = await db.notificationconfig.find_many()
    
    if not configs:
        for default_config in DEFAULT_NOTIFICATION_CONFIGS:
            create_data = {
                "eventType": default_config["event_type"],
                "title": default_config["title"],
                "template": default_config["template"],
                "daysBeforeDue": default_config.get("days_before_due"),
                "enabled": True,
            }
            if "reminder_send_time" in default_config:
                create_data["reminderSendTime"] = default_config["reminder_send_time"]
            await db.notificationconfig.create(data=create_data)
        configs = await db.notificationconfig.find_many()
    
    return [
        {
            "id": c.id,
            "event_type": c.eventType,
            "enabled": c.enabled,
            "title": c.title,
            "template": c.template,
            "days_before_due": c.daysBeforeDue,
            "reminder_send_time": getattr(c, "reminderSendTime", None) or "09:00",
        }
        for c in configs
    ]

async def update_notification_config(
    event_type: str,
    enabled: Optional[bool] = None,
    title: Optional[str] = None,
    template: Optional[str] = None,
    days_before_due: Optional[int] = None,
    reminder_send_time: Optional[str] = None
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
    if reminder_send_time is not None:
        data["reminderSendTime"] = reminder_send_time
    
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
            create_data = {
                "eventType": default_config["event_type"],
                "title": default_config["title"],
                "template": default_config["template"],
                "daysBeforeDue": default_config.get("days_before_due"),
                "enabled": True,
            }
            if "reminder_send_time" in default_config:
                create_data["reminderSendTime"] = default_config["reminder_send_time"]
            await db.notificationconfig.create(data=create_data)


async def due_reminder_already_sent_today(bill_id: int) -> bool:
    """Check if we already sent a due reminder for this bill today."""
    await ensure_connected()
    try:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)
        existing = await db.dueremindersent.find_first(
            where={
                "billId": bill_id,
                "sentDate": {"gte": today_start, "lt": tomorrow_start}
            }
        )
        return existing is not None
    except Exception as e:
        logger.warning(f"due_reminder_already_sent_today check failed (table may not exist): {e}")
        return False


async def record_due_reminder_sent(bill_id: int) -> None:
    """Record that we sent a due reminder for this bill today."""
    await ensure_connected()
    try:
        now = datetime.now(timezone.utc)
        today_noon = now.replace(hour=12, minute=0, second=0, microsecond=0)
        await db.dueremindersent.create(
            data={"billId": bill_id, "sentDate": today_noon}
        )
    except Exception as e:
        logger.warning(f"record_due_reminder_sent failed: {e}")


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


async def get_previous_balance() -> Optional[Dict[str, Any]]:
    """Get the balance record before the current one (for balance_change tests)"""
    await ensure_connected()
    
    records = await db.accountbalancehistory.find_many(
        order={"scrapedAt": "desc"},
        take=2
    )
    if len(records) < 2:
        return None
    
    prev = records[1]
    return {
        "balance": f"${decimal_to_float(prev.balance):.2f}",
        "balance_numeric": decimal_to_float(prev.balance),
    }

# =============================================================================
# Scraped Data & Logs
# =============================================================================

async def save_scraped_data(data: Dict[str, Any], status: str, error_message: Optional[str] = None, screenshot_path: Optional[str] = None):
    """
    Save raw scraped data.
    Returns: (record_id, recheck_info) where recheck_info is None or a dict with recheck data.
    """
    await ensure_connected()
    
    record = await db.scrapeddata.create(
        data={
            "data": Json(data),
            "status": status,
            "errorMessage": error_message,
            "screenshotPath": screenshot_path
        }
    )
    
    recheck_info = None
    if status == "success" and data:
        sync_result = await sync_from_scrape(data)
        if isinstance(sync_result, dict) and not sync_result.get("recorded") and sync_result.get("recheck_needed"):
            recheck_info = sync_result
    
    return record.id, recheck_info

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
            "screenshot_path": r.screenshotPath,
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
    """Get all cached realtime readings (no limit - append storage)"""
    await ensure_connected()
    rows = await db.realtimereading.find_many(order={"endTime": "asc"})
    if not rows:
        return None
    return [
        {
            "start_time": r.startTime.isoformat(),
            "end_time": r.endTime.isoformat(),
            "consumption": float(r.consumption),
        }
        for r in rows
    ]


async def get_realtime_readings_for_day(day_offset: int = 0) -> tuple[List[Dict[str, Any]], int]:
    """
    Get readings for a specific day. Day 0 = most recent complete day we have, 1 = day before, etc.
    Returns (readings for that day, total_available_days).
    Uses Prisma only (no asyncpg) for addon compatibility.
    """
    await ensure_connected()
    # Fetch all readings and compute distinct dates in Python (Prisma-only, no raw SQL)
    rows = await db.realtimereading.find_many(order={"endTime": "desc"})
    if not rows:
        return [], 0
    # Get distinct dates (UTC) from endTime, most recent first
    seen: set = set()
    dates: List[datetime] = []
    for r in rows:
        d = r.endTime.date() if hasattr(r.endTime, "date") else r.endTime.replace(tzinfo=timezone.utc).date()
        if d not in seen:
            seen.add(d)
            dates.append(datetime(d.year, d.month, d.day, tzinfo=timezone.utc))
    dates.sort(reverse=True)
    total_days = len(dates)
    if day_offset >= total_days:
        return [], total_days
    day_start = dates[day_offset]
    day_end = day_start + timedelta(days=1)
    readings = await db.realtimereading.find_many(
        where={
            "endTime": {"gte": day_start, "lte": day_end}
        },
        order={"startTime": "asc"}
    )
    return [
        {
            "start_time": r.startTime.isoformat(),
            "end_time": r.endTime.isoformat(),
            "consumption": float(r.consumption),
        }
        for r in readings
    ], total_days


async def save_realtime_readings_db(readings: List[Dict[str, Any]]):
    """Append/merge realtime readings (upsert by start_time, end_time - no max days).
    Uses Prisma only (no asyncpg) for addon compatibility.
    """
    await ensure_connected()
    if not readings:
        return
    for r in readings:
        start_str = r.get("start_time") or ""
        end_str = r.get("end_time") or ""
        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        consumption = float(r.get("consumption", 0) or 0)
        try:
            await db.realtimereading.upsert(
                where={"startTime_endTime": {"startTime": start_dt, "endTime": end_dt}},
                create={"startTime": start_dt, "endTime": end_dt, "consumption": consumption},
                update={"consumption": consumption},
            )
        except Exception:
            # Fallback: find_first + create/update (compound unique name may vary by Prisma version)
            existing = await db.realtimereading.find_first(
                where={"startTime": start_dt, "endTime": end_dt}
            )
            if existing:
                await db.realtimereading.update(
                    where={"id": existing.id},
                    data={"consumption": consumption},
                )
            else:
                await db.realtimereading.create(
                    data={"startTime": start_dt, "endTime": end_dt, "consumption": consumption},
                )

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

async def calculate_expected_balance() -> Optional[float]:
    """
    Calculate expected account balance based on latest bill minus payments.
    Returns None if insufficient data to calculate.
    """
    result = await _calculate_expected_balance_with_bill()
    return result[0] if result else None


async def _calculate_expected_balance_with_bill() -> Optional[tuple]:
    """Returns (expected_balance, bill_id) or None.
    If late fee was reported for this bill cycle, adds it to expected so validation passes."""
    await ensure_connected()
    
    latest_bill = await db.bill.find_first(order={"billCycleDate": "desc"})
    if not latest_bill or not latest_bill.billTotal:
        return None
    
    bill_total = decimal_to_float(latest_bill.billTotal)
    payments = await db.payment.find_many(where={"billId": latest_bill.id})
    total_payments = sum(decimal_to_float(p.amount) for p in payments if p.amount)
    expected = bill_total - total_payments

    stored_late_fee = await get_stored_late_fee_amount(latest_bill.id)
    if stored_late_fee is not None:
        expected += stored_late_fee

    return (expected, latest_bill.id)


async def validate_and_record_balance(scraped_balance: str) -> Dict[str, Any]:
    """
    Validate scraped balance against expected balance before recording.

    Logic: expected_balance = latest_bill_amount - payments_for_that_bill
    If scraped balance doesn't match expected, don't update.

    Returns: {"recorded": True} if recorded; {"recorded": False, "recheck_needed": True, ...}
    if rejected and scraped > expected (possible late fee - caller should re-scrape).
    """
    scraped_numeric = parse_amount(scraped_balance)
    result = await _calculate_expected_balance_with_bill()

    if result is None:
        await record_account_balance(scraped_balance)
        logger.info(f"Recorded balance ${scraped_numeric:.2f} (no bill data to validate against)")
        return {"recorded": True}

    expected, bill_id = result
    tolerance = 1.0
    diff = scraped_numeric - expected
    diff_abs = abs(diff)

    if diff_abs <= tolerance:
        await record_account_balance(scraped_balance)
        logger.info(f"Recorded balance ${scraped_numeric:.2f} (matches expected ${expected:.2f})")
        return {"recorded": True}

    # Rejected - log and maybe signal recheck (only when scraped > expected = possible late fee)
    logger.warning(
        f"Rejected scraped balance ${scraped_numeric:.2f}: "
        f"expected ${expected:.2f} (latest bill - payments). Keeping previous balance."
    )
    await add_log(
        "warning",
        f"Balance validation failed: scraped ${scraped_numeric:.2f} != expected ${expected:.2f}. "
        f"Keeping previous balance."
    )
    if diff > 0:
        return {
            "recorded": False,
            "recheck_needed": True,
            "scraped": scraped_numeric,
            "expected": expected,
            "bill_id": bill_id,
        }
    return {"recorded": False}


async def late_fee_already_reported(bill_id: int) -> bool:
    """Check if we already reported a late fee for this bill cycle."""
    stored = await get_app_setting("late_fee_reported")
    if stored and isinstance(stored, dict):
        return stored.get("bill_id") == bill_id
    # Legacy: old format stored bill_id only
    legacy = await get_app_setting("late_fee_reported_bill_id")
    if legacy is None:
        return False
    try:
        return int(legacy) == bill_id
    except (TypeError, ValueError):
        return False


async def get_stored_late_fee_amount(bill_id: int) -> Optional[float]:
    """Return stored late fee amount if we reported for this bill; else None."""
    stored = await get_app_setting("late_fee_reported")
    if not stored or not isinstance(stored, dict):
        return None
    if stored.get("bill_id") != bill_id:
        return None
    try:
        return float(stored.get("amount", 0))
    except (TypeError, ValueError):
        return None


async def record_late_fee_reported(bill_id: int, late_fee_amount: float) -> None:
    """Record that we reported a late fee for this bill cycle, with the amount for expected-balance adjustment."""
    await set_app_setting("late_fee_reported", {"bill_id": bill_id, "amount": late_fee_amount})


async def process_balance_recheck(
    rescraped_balance: Optional[str],
    original_scraped: float,
    expected: float,
    bill_id: int,
) -> None:
    """
    Process recheck result after validation failed with scraped > expected.
    If recheck matches original: record balance, trigger TTS+notification (or skip if already reported).
    If recheck differs: reject, log inconclusive.
    """
    if not rescraped_balance:
        logger.warning("Balance recheck: no balance found on rescrape, inconclusive.")
        await add_log("warning", "Balance recheck returned no balance. Keeping previous balance.")
        return

    rescraped_numeric = parse_amount(rescraped_balance)
    if abs(rescraped_numeric - original_scraped) > 0.01:
        logger.warning(
            f"Recheck returned different balance: ${rescraped_numeric:.2f} != ${original_scraped:.2f}. Inconclusive."
        )
        await add_log(
            "warning",
            f"Recheck returned different balance: ${rescraped_numeric:.2f} vs ${original_scraped:.2f}. Keeping previous balance.",
        )
        return

    # Same balance - treat as late fee
    if await late_fee_already_reported(bill_id):
        await record_account_balance(rescraped_balance)
        logger.info("Late fee already added for this bill cycle. Will reset at next bill cycle.")
        await add_log("info", "Late fee already added. Will reset at next bill cycle.")
        return

    await record_account_balance(rescraped_balance)
    late_fee_amount = original_scraped - expected
    late_fee_str = f"${late_fee_amount:.2f}"

    await record_late_fee_reported(bill_id, late_fee_amount)

    try:
        from tts_scheduler import trigger_late_fee_tts
        await trigger_late_fee_tts(late_fee_str)
    except Exception as e:
        logger.warning(f"Late fee TTS failed: {e}")
        await add_log("warning", f"Late fee TTS failed: {e}")

    try:
        from notifications import notify_late_fee
        await notify_late_fee(late_fee_str)
    except Exception as e:
        logger.warning(f"Late fee notification failed: {e}")
        await add_log("warning", f"Late fee notification failed: {e}")

    logger.info(f"Recorded balance ${rescraped_numeric:.2f} (late fee {late_fee_str} added)")
    await add_log("info", f"Late fee detected: {late_fee_str} added. Balance recorded.")


async def sync_from_scrape(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Sync scraped data to normalized tables"""
    try:
        scraped_balance = data.get("account_balance")
        
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
        
        # AFTER all bills and payments are processed, validate and record balance
        # This ensures we have complete payment data before checking if balance makes sense
        if scraped_balance:
            validation_result = await validate_and_record_balance(scraped_balance)
            return validation_result
    except Exception as e:
        logger.warning(f"Failed to sync scraped data: {e}")
    return None

# =============================================================================
# Ledger Data
# =============================================================================

def _parse_iso_forecast_date(iso_str: Optional[str]):
    """Parse forecast start_date/end_date (ISO) to date for cycle comparison."""
    if not iso_str or not str(iso_str).strip():
        return None
    s = str(iso_str).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        return dt.date()
    except (ValueError, TypeError):
        pass
    # Date-only strings (some caches / serializers)
    try:
        return date.fromisoformat(s[:10] if len(s) >= 10 and s[4] == "-" else s)
    except (ValueError, TypeError):
        return None


# Trailing label in month_range strings from ConEd (e.g. "JAN - FEB" -> February).
_MONTH_ABBREV_TO_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_FULL_TO_NUM = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def _month_num_from_label(label: str) -> Optional[int]:
    s = (label or "").strip().lower()
    if not s:
        return None
    if s in _MONTH_FULL_TO_NUM:
        return _MONTH_FULL_TO_NUM[s]
    return _MONTH_ABBREV_TO_NUM.get(s[:3])


def _month_range_trailing_month(month_range: Optional[str]) -> Optional[int]:
    if not month_range or not str(month_range).strip():
        return None
    # Normalize "JAN / FEB", extra spaces, slashes → hyphen-separated labels
    normalized = re.sub(r"\s+", " ", str(month_range).strip().replace("/", "-"))
    parts = re.split(r"\s*[-–—]\s*", normalized)
    if len(parts) < 2:
        return None
    return _month_num_from_label(parts[-1])


def _month_range_leading_month(month_range: Optional[str]) -> Optional[int]:
    """First month in a ConEd-style range (e.g. 'JAN - FEB' -> January)."""
    if not month_range or not str(month_range).strip():
        return None
    normalized = re.sub(r"\s+", " ", str(month_range).strip().replace("/", "-"))
    parts = re.split(r"\s*[-–—]\s*", normalized)
    if len(parts) < 2:
        return None
    return _month_num_from_label(parts[0])


def _year_month_sort_key(ym: Tuple[int, int]) -> int:
    return ym[0] * 12 + ym[1]


# 1..12 -> short label for UI strings
_MONTH_NUM_TO_ABBREV = (
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _forecast_cycle_months_label(window_start: date, window_end: date) -> str:
    """e.g. Mar 19–Apr 18 forecast -> 'Mar – Apr'."""
    a = _MONTH_NUM_TO_ABBREV[window_start.month]
    b = _MONTH_NUM_TO_ABBREV[window_end.month]
    if window_start.year == window_end.year and window_start.month == window_end.month:
        return a
    return f"{a} – {b}"


def _missing_period_hint(
    period_end_ym: Tuple[int, int], cycle_start_ym: Tuple[int, int]
) -> Optional[str]:
    """
    Human hint for the bridge bill (e.g. last posted JAN–FEB, current Mar–Apr -> 'Feb – Mar').
    None when gap spans more than one month (UI shows generic copy).
    """
    pe_key = _year_month_sort_key(period_end_ym)
    cs_key = _year_month_sort_key(cycle_start_ym)
    if cs_key <= pe_key:
        return None
    diff = cs_key - pe_key
    ta = _MONTH_NUM_TO_ABBREV[period_end_ym[1]]
    tb = _MONTH_NUM_TO_ABBREV[cycle_start_ym[1]]
    if diff == 1:
        return f"{ta} – {tb}"
    return None


def _select_reference_bill_for_pending_gap(bills_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Select the bill to use for gap detection. Priority:
    1) First bill (by billCycleDate desc) with month_range AND has_statement_pdf
    2) First bill with month_range AND pdf_exists
    3) First bill with month_range (even without PDF)
    4) First bill (legacy fallback)
    """
    if not bills_data:
        return None
    
    # Priority 1: has month_range AND BillDocument row
    for b in bills_data:
        if b.get("month_range") and b.get("has_statement_pdf"):
            return b
    
    # Priority 2: has month_range AND PDF file on disk
    for b in bills_data:
        if b.get("month_range") and b.get("pdf_exists"):
            return b
    
    # Priority 3: has month_range (no PDF required)
    for b in bills_data:
        if b.get("month_range"):
            return b
    
    # Fallback: first bill
    return bills_data[0]


async def _calculate_implied_new_charges(
    reference_bill: Dict[str, Any],
    account_balance_str: str,
) -> Optional[float]:
    """Calculate implied new charges: balance - (bill_total - payments + late_fee)."""
    bill_total = reference_bill.get("amount_numeric")
    if bill_total is None:
        bill_total = parse_amount(str(reference_bill.get("bill_total") or ""))
    bill_total_f = float(bill_total or 0.0)

    payments_sum = 0.0
    for p in reference_bill.get("payments") or []:
        amt = p.get("amount_numeric")
        if amt is None:
            amt = parse_amount(str(p.get("amount") or ""))
        payments_sum += float(amt or 0.0)

    bill_id = reference_bill.get("id")
    late_fee = await get_stored_late_fee_amount(int(bill_id)) if bill_id else 0
    late_fee_f = float(late_fee or 0.0)

    residual = bill_total_f - payments_sum + late_fee_f
    balance = parse_amount(str(account_balance_str or ""))
    delta = balance - residual

    return round(delta, 2) if delta > 0 else None


async def compute_pending_new_bill_state(
    reference_bill: Optional[Dict[str, Any]],
    account_balance_str: str,
) -> Dict[str, Any]:
    """
    SIMPLE GAP DETECTION for pending new bill.
    
    Logic:
    1. Get last posted bill's month_range (e.g., "JAN - FEB")
    2. Extract trailing month (February = 2)
    3. Get current meter forecast start month (March = 3)
    4. If forecast_month > bill_end_month -> GAP DETECTED -> pending bill
    
    Runs on every GET /api/ledger call (Account Ledger polls every 30s).
    Uses meter_forecast_cache from database - no MeterService required.
    """
    default: Dict[str, Any] = {
        "active": False,
        "implied_new_charges": None,
        "posted_month_range": None,
        "current_cycle_months": None,
        "missing_period_hint": None,
        "debug_info": None,
    }
    
    # Step 1: Must have a reference bill
    if not reference_bill:
        logger.info("pending_new_bill: NO reference bill found")
        return {**default, "debug_info": "no_reference_bill"}
    
    # Step 2: Must have month_range on the bill
    month_range = reference_bill.get("month_range")
    if not month_range:
        logger.info(f"pending_new_bill: reference bill id={reference_bill.get('id')} has NO month_range")
        return {**default, "debug_info": f"no_month_range_on_bill_{reference_bill.get('id')}"}
    
    # Step 3: Extract trailing month from month_range (e.g., "JAN - FEB" -> 2)
    bill_end_month = _month_range_trailing_month(month_range)
    if bill_end_month is None:
        logger.info(f"pending_new_bill: could not parse month_range '{month_range}'")
        return {**default, "debug_info": f"parse_failed_month_range_{month_range}"}
    
    # Step 4: Get forecast from database
    forecast = await get_meter_forecast_db()
    if not forecast:
        logger.info("pending_new_bill: NO meter_forecast_cache in database")
        return {**default, "debug_info": "no_forecast_in_db"}
    
    # Step 5: Parse forecast start date
    start_date_str = forecast.get("start_date")
    forecast_start = _parse_iso_forecast_date(start_date_str)
    if not forecast_start:
        logger.info(f"pending_new_bill: could not parse forecast start_date '{start_date_str}'")
        return {**default, "debug_info": f"parse_failed_forecast_start_{start_date_str}"}
    
    forecast_month = forecast_start.month
    
    # Step 6: Determine year for the bill's trailing month
    # Use bill_date (actual statement date) for accurate year
    bill_date = parse_date(reference_bill.get("bill_date") or "")
    if bill_date:
        bill_year = bill_date.year
    else:
        # Fallback: if bill end month > forecast month, probably previous year
        # e.g., bill=DEC(12), forecast=JAN(1) -> bill is previous year
        if bill_end_month > forecast_month:
            bill_year = forecast_start.year - 1
        else:
            bill_year = forecast_start.year
    
    # Step 7: Compare months (with year consideration)
    bill_end_ym = (bill_year, bill_end_month)
    forecast_ym = (forecast_start.year, forecast_month)
    
    bill_sort_key = _year_month_sort_key(bill_end_ym)
    forecast_sort_key = _year_month_sort_key(forecast_ym)
    gap_detected = forecast_sort_key > bill_sort_key
    
    # Log the calculation for debugging
    logger.info(
        f"pending_new_bill: month_range='{month_range}' -> bill_end={_MONTH_NUM_TO_ABBREV[bill_end_month]}({bill_end_month}) year={bill_year}, "
        f"forecast_start={forecast_start} -> {_MONTH_NUM_TO_ABBREV[forecast_month]}({forecast_month}), "
        f"bill_key={bill_sort_key} forecast_key={forecast_sort_key} GAP={gap_detected}"
    )
    
    if not gap_detected:
        return {
            **default,
            "debug_info": f"no_gap: bill={bill_year}-{bill_end_month:02d} forecast={forecast_start.year}-{forecast_month:02d}"
        }
    
    # GAP DETECTED - bill is generating!
    forecast_end = _parse_iso_forecast_date(forecast.get("end_date"))
    implied_charges = await _calculate_implied_new_charges(reference_bill, account_balance_str)
    
    cycle_label = _forecast_cycle_months_label(forecast_start, forecast_end) if forecast_end else _MONTH_NUM_TO_ABBREV[forecast_month]
    missing_hint = _missing_period_hint(bill_end_ym, forecast_ym)
    
    logger.info(
        f"pending_new_bill: GAP DETECTED! Bill ends {_MONTH_NUM_TO_ABBREV[bill_end_month]}, "
        f"forecast starts {_MONTH_NUM_TO_ABBREV[forecast_month]}. Missing period: {missing_hint}"
    )
    
    return {
        "active": True,
        "implied_new_charges": implied_charges,
        "posted_month_range": month_range,
        "current_cycle_months": cycle_label,
        "missing_period_hint": missing_hint,
        "debug_info": f"gap_detected: bill={bill_year}-{bill_end_month:02d} forecast={forecast_start.year}-{forecast_month:02d}",
    }


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
            "has_statement_pdf": bill.document is not None,
            "billing_period_start": (
                bill.details.billingPeriodStart.strftime("%Y-%m-%d")
                if bill.details and bill.details.billingPeriodStart
                else None
            ),
            "billing_period_end": (
                bill.details.billingPeriodEnd.strftime("%Y-%m-%d")
                if bill.details and bill.details.billingPeriodEnd
                else None
            ),
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

    # Latest payment for current bill (for payment received tests/triggers)
    latest_payment = await get_last_payment_for_latest_bill()

    # Latest bill (first in list) - for due reminders and convenience
    latest_bill = bills_data[0] if bills_data else None
    # Gap detection: compare forecast to last real statement, not a newer shell cycle
    reference_bill_for_pending = _select_reference_bill_for_pending_gap(bills_data)

    pending_new_bill = await compute_pending_new_bill_state(reference_bill_for_pending, account_balance)

    return {
        "account_balance": account_balance,
        "bills": bills_data,
        "latest_bill": latest_bill,
        "orphan_payments": [],  # No separate section - merged into bills
        "payee_summaries": payee_summaries,
        "latest_payment": latest_payment,
        "pending_new_bill": pending_new_bill,
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
    
    # Get all bills (include statement period for reminders / streak logic)
    bills = await db.bill.find_many(
        order={"billCycleDate": "desc"},
        include={"payments": True, "details": True},
    )
    
    results = []
    rollover_by_user = {u.id: 0.0 for u in users}
    
    for bill in reversed(bills):  # Process oldest first for rollover
        bill_total = decimal_to_float(bill.billTotal) or 0
        
        det = bill.details
        bill_result = {
            "bill_id": bill.id,
            "month_range": bill.monthRange,
            "bill_cycle_date": bill.billCycleDate.strftime("%m/%d/%Y") if bill.billCycleDate else None,
            "billing_period_start": (
                det.billingPeriodStart.strftime("%Y-%m-%d") if det and det.billingPeriodStart else None
            ),
            "billing_period_end": (
                det.billingPeriodEnd.strftime("%Y-%m-%d") if det and det.billingPeriodEnd else None
            ),
            "bill_total": bill_total,
            "total_paid": 0,
            "bill_balance": bill_total,
            "payees": [],
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


def _parse_iso_date_only(s: Optional[str]) -> Optional[date]:
    if not s or not str(s).strip():
        return None
    try:
        return date.fromisoformat(str(s).strip()[:10])
    except (ValueError, TypeError):
        return None


PAYEE_BALANCE_REMINDER_DEDUP_KEY = "payee_balance_reminder_dedup"
UNDERPAYMENT_STREAK_TTS_DEDUP_KEY = "underpayment_streak_tts_dedup"


def _dedup_payee_bill_key(payee_id: int, bill_id: int) -> str:
    return f"{payee_id}_{bill_id}"


async def _read_string_map_setting(key: str) -> Dict[str, str]:
    raw = await get_app_setting(key)
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    return {}


async def _write_string_map_setting(key: str, m: Dict[str, str]) -> None:
    await set_app_setting(key, m)


async def payee_balance_reminder_already_sent_today(payee_id: int, bill_id: int) -> bool:
    """At most one balance reminder per payee per bill per local calendar day."""
    today_s = date.today().isoformat()
    m = await _read_string_map_setting(PAYEE_BALANCE_REMINDER_DEDUP_KEY)
    return m.get(_dedup_payee_bill_key(payee_id, bill_id)) == today_s


async def record_payee_balance_reminder_sent(payee_id: int, bill_id: int) -> None:
    today_s = date.today().isoformat()
    m = await _read_string_map_setting(PAYEE_BALANCE_REMINDER_DEDUP_KEY)
    m[_dedup_payee_bill_key(payee_id, bill_id)] = today_s
    # Drop entries older than 45 days (values are YYYY-MM-DD)
    cutoff = (date.today() - timedelta(days=45)).isoformat()
    m = {k: v for k, v in m.items() if v >= cutoff}
    await _write_string_map_setting(PAYEE_BALANCE_REMINDER_DEDUP_KEY, m)


async def underpayment_streak_tts_already_sent_today(payee_id: int) -> bool:
    today_s = date.today().isoformat()
    m = await _read_string_map_setting(UNDERPAYMENT_STREAK_TTS_DEDUP_KEY)
    return m.get(str(payee_id)) == today_s


async def record_underpayment_streak_tts_sent(payee_id: int) -> None:
    today_s = date.today().isoformat()
    m = await _read_string_map_setting(UNDERPAYMENT_STREAK_TTS_DEDUP_KEY)
    m[str(payee_id)] = today_s
    cutoff = (date.today() - timedelta(days=45)).isoformat()
    m = {k: v for k, v in m.items() if v >= cutoff}
    await _write_string_map_setting(UNDERPAYMENT_STREAK_TTS_DEDUP_KEY, m)


async def compute_days_remaining_in_billing_cycle(latest_bill_summary: Dict[str, Any]) -> Tuple[Optional[int], str]:
    """
    Days until the active billing period ends (local date), and a display string for period end.
    Uses statement billing period when today falls within it; otherwise meter forecast end_date.
    """
    today = date.today()
    ps = _parse_iso_date_only(latest_bill_summary.get("billing_period_start"))
    pe = _parse_iso_date_only(latest_bill_summary.get("billing_period_end"))
    end_display = ""
    if pe:
        try:
            end_display = datetime(pe.year, pe.month, pe.day).strftime("%B %d, %Y").replace(" 0", " ")
        except Exception:
            end_display = pe.isoformat()

    if ps and pe and ps <= today <= pe:
        return max(0, (pe - today).days), end_display or pe.isoformat()

    forecast = await get_meter_forecast_db()
    if forecast:
        fe = _parse_iso_forecast_date(forecast.get("end_date"))
        if fe and today <= fe:
            disp = fe.strftime("%B %d, %Y").replace(" 0", " ")
            return max(0, (fe - today).days), disp
        if fe and today > fe:
            return 0, fe.strftime("%B %d, %Y").replace(" 0", " ")

    if pe:
        if today > pe:
            return 0, end_display
        if today < pe and (not ps or today >= ps):
            return max(0, (pe - today).days), end_display

    return None, end_display or "N/A"


def get_last_two_completed_bill_summaries(
    summaries: List[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Bills whose billing period has fully ended (end date strictly before today).
    Missing period end: skip for streak logic. Sorted by billing_period_end desc, take two.
    """
    today = date.today()
    completed: List[Dict[str, Any]] = []
    for s in summaries:
        pe = _parse_iso_date_only(s.get("billing_period_end"))
        if pe is None:
            continue
        if pe < today:
            completed.append(s)
    if not completed:
        return None, None

    def sort_key(x: Dict[str, Any]) -> date:
        d = _parse_iso_date_only(x.get("billing_period_end"))
        return d or date.min

    completed.sort(key=sort_key, reverse=True)
    if len(completed) < 2:
        return None, None
    return completed[0], completed[1]


def payees_underpaid_on_both_completed_cycles(
    recent_completed: Dict[str, Any], prior_completed: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    recent_completed = completed bill with the latest billing_period_end (most recently ended cycle).
    prior_completed = the next older completed bill.
    Payee underpaid on both per calculate_all_payee_balances status.
    """
    by_recent = {p["user_id"]: p for p in recent_completed.get("payees") or []}
    by_prior = {p["user_id"]: p for p in prior_completed.get("payees") or []}
    out: List[Dict[str, Any]] = []
    for uid, pr in by_recent.items():
        if uid not in by_prior:
            continue
        pp = by_prior[uid]
        if pr.get("status") == "underpaid" and pp.get("status") == "underpaid":
            out.append(
                {
                    "user_id": uid,
                    "name": pr.get("name") or pp.get("name") or "",
                    "month_range_1": prior_completed.get("month_range") or "",
                    "month_range_2": recent_completed.get("month_range") or "",
                    "amount_owed_1": max(
                        0.0, (pp.get("amount_due") or 0) - (pp.get("amount_paid") or 0)
                    ),
                    "amount_owed_2": max(
                        0.0, (pr.get("amount_due") or 0) - (pr.get("amount_paid") or 0)
                    ),
                }
            )
    return out


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
