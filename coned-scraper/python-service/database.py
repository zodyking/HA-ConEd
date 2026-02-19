import sqlite3
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import hashlib

def utc_now_iso() -> str:
    """Get current UTC time as ISO string"""
    return datetime.now(timezone.utc).isoformat()

# Use configurable data dir (DATA_DIR env for addon)
from data_config import DATA_DIR
DB_PATH = DATA_DIR / "scraper.db"

def get_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize SQLite database with normalized schema"""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # ==========================================
    # LEGACY TABLES (keep for backward compat)
    # ==========================================
    
    # Create scraped_data table (raw scrape storage)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraped_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            data TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            screenshot_path TEXT
        )
    ''')
    
    # Add screenshot_path column if it doesn't exist
    try:
        cursor.execute('ALTER TABLE scraped_data ADD COLUMN screenshot_path TEXT')
    except sqlite3.OperationalError:
        pass
    
    # Create logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL
        )
    ''')
    
    # Create scrape_history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scrape_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            success INTEGER NOT NULL,
            error_message TEXT,
            failure_step TEXT,
            duration_seconds REAL
        )
    ''')
    
    # ==========================================
    # NEW NORMALIZED TABLES
    # ==========================================
    
    # Bills table - each unique bill gets one record
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_cycle_date TEXT NOT NULL,
            bill_date TEXT,
            month_range TEXT,
            bill_total TEXT,
            amount_numeric REAL,
            first_scraped_at TEXT NOT NULL,
            last_scraped_at TEXT NOT NULL,
            scrape_count INTEGER DEFAULT 1,
            UNIQUE(bill_cycle_date, month_range)
        )
    ''')
    
    # Payments table - each unique payment gets one record
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER,
            payment_date TEXT NOT NULL,
            description TEXT,
            amount TEXT,
            amount_numeric REAL,
            first_scraped_at TEXT NOT NULL,
            last_scraped_at TEXT NOT NULL,
            scrape_count INTEGER DEFAULT 1,
            scrape_order INTEGER,
            payment_hash TEXT UNIQUE,
            payee_status TEXT DEFAULT 'unverified',
            payee_user_id INTEGER,
            card_last_four TEXT,
            verification_method TEXT,
            bill_manually_set INTEGER DEFAULT 0,
            manual_order INTEGER,
            FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE SET NULL,
            FOREIGN KEY (payee_user_id) REFERENCES payee_users(id) ON DELETE SET NULL
        )
    ''')
    
    # Add bill_manually_set column if it doesn't exist (migration)
    try:
        cursor.execute('ALTER TABLE payments ADD COLUMN bill_manually_set INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    
    # Add manual_order column if it doesn't exist (migration)
    try:
        cursor.execute('ALTER TABLE payments ADD COLUMN manual_order INTEGER')
    except sqlite3.OperationalError:
        pass
    
    # Add payee_pending_until column (2hr window for auto-assignment)
    try:
        cursor.execute('ALTER TABLE payments ADD COLUMN payee_pending_until TEXT')
    except sqlite3.OperationalError:
        pass
    
    # Account balance history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_balance_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            balance TEXT NOT NULL,
            balance_numeric REAL,
            scraped_at TEXT NOT NULL,
            changed_from_previous INTEGER DEFAULT 0
        )
    ''')
    
    # Payee users - people who can make payments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payee_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            is_default INTEGER DEFAULT 0,
            responsibility_percent REAL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Add responsibility_percent column if it doesn't exist (migration)
    try:
        cursor.execute('ALTER TABLE payee_users ADD COLUMN responsibility_percent REAL DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    
    # User cards - card endings linked to users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            card_last_four TEXT NOT NULL,
            card_label TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES payee_users(id) ON DELETE CASCADE,
            UNIQUE(card_last_four)
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bills_cycle_date ON bills(bill_cycle_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_bill_id ON payments(bill_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_first_scraped ON payments(first_scraped_at)')
    
    conn.commit()
    conn.close()

def parse_amount(amount_str: str) -> Optional[float]:
    """Parse amount string to float"""
    if not amount_str:
        return None
    try:
        # Remove $, commas, and whitespace
        cleaned = amount_str.replace('$', '').replace(',', '').strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None

def generate_payment_hash(payment_date: str, amount: str, description: str, bill_cycle_date: str) -> str:
    """Generate unique hash for a payment to detect duplicates"""
    content = f"{payment_date}|{amount}|{description}|{bill_cycle_date}"
    return hashlib.md5(content.encode()).hexdigest()

# ==========================================
# BILL FUNCTIONS
# ==========================================

def upsert_bill(bill_data: Dict[str, Any]) -> int:
    """Insert or update a bill, returns bill ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    bill_cycle_date = bill_data.get('bill_cycle_date', '')
    month_range = bill_data.get('month_range', '')
    bill_date = bill_data.get('bill_date', '')
    bill_total = bill_data.get('bill_total', '')
    amount_numeric = parse_amount(bill_total)
    now = utc_now_iso()
    
    # Try to find existing bill
    cursor.execute('''
        SELECT id, scrape_count FROM bills 
        WHERE bill_cycle_date = ? AND month_range = ?
    ''', (bill_cycle_date, month_range))
    
    existing = cursor.fetchone()
    
    if existing:
        # Update existing bill
        cursor.execute('''
            UPDATE bills SET 
                last_scraped_at = ?,
                scrape_count = scrape_count + 1,
                bill_date = COALESCE(?, bill_date),
                bill_total = COALESCE(?, bill_total),
                amount_numeric = COALESCE(?, amount_numeric)
            WHERE id = ?
        ''', (now, bill_date, bill_total, amount_numeric, existing['id']))
        bill_id = existing['id']
    else:
        # Insert new bill
        cursor.execute('''
            INSERT INTO bills (bill_cycle_date, bill_date, month_range, bill_total, amount_numeric, first_scraped_at, last_scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (bill_cycle_date, bill_date, month_range, bill_total, amount_numeric, now, now))
        bill_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return bill_id

def parse_us_date_to_sortable(date_str: str) -> str:
    """
    Convert M/D/YYYY or MM/DD/YYYY to YYYY-MM-DD for proper sorting.
    Handles variable-length month/day formats.
    Returns empty string if parsing fails.
    """
    if not date_str:
        return ''
    try:
        # Try parsing M/D/YYYY format (variable length)
        parts = date_str.split('/')
        if len(parts) == 3:
            month, day, year = parts
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except:
        pass
    return date_str  # Return original if parsing fails

def sort_bills_by_date(bills: List[Dict[str, Any]], desc: bool = True) -> List[Dict[str, Any]]:
    """Sort bills by bill_cycle_date chronologically"""
    def get_sort_key(bill):
        date_str = bill.get('bill_cycle_date', '')
        sortable = parse_us_date_to_sortable(date_str)
        # Secondary sort by first_scraped_at
        scraped = bill.get('first_scraped_at', '')
        return (sortable, scraped)
    
    return sorted(bills, key=get_sort_key, reverse=desc)

def get_all_bills(limit: int = 100) -> List[Dict[str, Any]]:
    """Get all bills ordered by bill_cycle_date (newest first)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM bills LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    bills = [dict(row) for row in rows]
    # Sort in Python to handle variable date formats (M/D/YYYY, MM/DD/YYYY, etc.)
    return sort_bills_by_date(bills, desc=True)

def get_bill_by_id(bill_id: int) -> Optional[Dict[str, Any]]:
    """Get a single bill by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM bills WHERE id = ?', (bill_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

# ==========================================
# PAYMENT FUNCTIONS
# ==========================================

def upsert_payment(payment_data: Dict[str, Any], bill_id: Optional[int] = None, scrape_order: int = 0) -> int:
    """Insert or update a payment, returns payment ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    payment_date = payment_data.get('bill_cycle_date', '')  # ConEd uses bill_cycle_date for payment date
    description = payment_data.get('description', 'Payment Received')
    amount = payment_data.get('amount', '')
    amount_numeric = parse_amount(amount)
    now = utc_now_iso()
    
    # Generate unique hash for this payment
    bill_cycle = ''
    if bill_id:
        bill = get_bill_by_id(bill_id)
        if bill:
            bill_cycle = bill.get('bill_cycle_date', '')
    
    payment_hash = generate_payment_hash(payment_date, amount, description, bill_cycle)
    
    # Try to find existing payment by hash
    cursor.execute('SELECT id, scrape_count FROM payments WHERE payment_hash = ?', (payment_hash,))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing payment
        cursor.execute('''
            UPDATE payments SET 
                last_scraped_at = ?,
                scrape_count = scrape_count + 1
            WHERE id = ?
        ''', (now, existing['id']))
        payment_id = existing['id']
    else:
        # Insert new payment with 2-hour pending window for payee auto-assignment
        pending_until = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        cursor.execute('''
            INSERT INTO payments (bill_id, payment_date, description, amount, amount_numeric, 
                                  first_scraped_at, last_scraped_at, scrape_order, payment_hash,
                                  payee_status, payee_pending_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        ''', (bill_id, payment_date, description, amount, amount_numeric, now, now, scrape_order, payment_hash, pending_until))
        payment_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return payment_id

def get_all_payments(limit: int = 100, bill_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all payments ordered by payment_date (then first_scraped_at for same-day)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if bill_id:
        cursor.execute('''
            SELECT p.*, u.name as payee_name, b.month_range as bill_month, b.bill_cycle_date as bill_cycle
            FROM payments p
            LEFT JOIN payee_users u ON p.payee_user_id = u.id
            LEFT JOIN bills b ON p.bill_id = b.id
            WHERE p.bill_id = ?
            ORDER BY p.payment_date DESC, p.first_scraped_at ASC
            LIMIT ?
        ''', (bill_id, limit))
    else:
        cursor.execute('''
            SELECT p.*, u.name as payee_name, b.month_range as bill_month, b.bill_cycle_date as bill_cycle
            FROM payments p
            LEFT JOIN payee_users u ON p.payee_user_id = u.id
            LEFT JOIN bills b ON p.bill_id = b.id
            ORDER BY p.payment_date DESC, p.first_scraped_at ASC
            LIMIT ?
        ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_latest_payment() -> Optional[Dict[str, Any]]:
    """
    Get the most recent payment from the most recent billing cycle.
    Respects manual_order if set, otherwise uses payment_date + first_scraped_at.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all bills to find the most recent one
    cursor.execute('SELECT * FROM bills')
    bills = [dict(row) for row in cursor.fetchall()]
    
    if not bills:
        # No bills, fall back to any payment
        conn.close()
        payments = get_all_payments(limit=1)
        return payments[0] if payments else None
    
    # Sort bills by date (most recent first)
    bills = sort_bills_by_date(bills, desc=True)
    most_recent_bill = bills[0]
    bill_id = most_recent_bill['id']
    
    # Get the "first" payment for this bill
    # New unlocked payments first, then locked payments in their manual order
    cursor.execute('''
        SELECT p.*, u.name as payee_name, b.month_range as bill_month, b.bill_cycle_date as bill_cycle
        FROM payments p
        LEFT JOIN payee_users u ON p.payee_user_id = u.id
        LEFT JOIN bills b ON p.bill_id = b.id
        WHERE p.bill_id = ?
        ORDER BY 
            CASE WHEN p.manual_order IS NOT NULL THEN 1 ELSE 0 END,
            p.payment_date DESC,
            p.first_scraped_at DESC,
            p.manual_order ASC
        LIMIT 1
    ''', (bill_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    
    # No payments for this bill, try to get any payment
    payments = get_all_payments(limit=1)
    return payments[0] if payments else None

def get_payments_for_bill(bill_id: int) -> List[Dict[str, Any]]:
    """Get all payments for a specific bill"""
    return get_all_payments(limit=100, bill_id=bill_id)

def get_payment_by_id(payment_id: int) -> Optional[Dict[str, Any]]:
    """Get a single payment by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, u.name as payee_name, b.month_range as bill_month, b.bill_cycle_date as bill_cycle
        FROM payments p
        LEFT JOIN payee_users u ON p.payee_user_id = u.id
        LEFT JOIN bills b ON p.bill_id = b.id
        WHERE p.id = ?
    ''', (payment_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

def update_payment_bill(payment_id: int, bill_id: Optional[int], manual: bool = True) -> bool:
    """Update which bill a payment belongs to. If manual=True, marks as manually set."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE payments SET 
            bill_id = ?,
            bill_manually_set = ?
        WHERE id = ?
    ''', (bill_id, 1 if manual else 0, payment_id))
    
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def update_payment_order(payment_id: int, bill_id: Optional[int], order: int) -> bool:
    """Update payment's bill and manual order position"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE payments SET 
            bill_id = ?,
            bill_manually_set = 1,
            manual_order = ?
        WHERE id = ?
    ''', (bill_id, order, payment_id))
    
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def clear_payment_manual_audit(payment_id: int) -> bool:
    """Clear/release the manual audit on a payment, allowing auto-logic to take over again"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE payments SET 
            bill_manually_set = 0,
            manual_order = NULL
        WHERE id = ?
    ''', (payment_id,))
    
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def get_most_recent_bill_payment_count() -> Dict[str, Any]:
    """Get payment count for the most recent billing cycle"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all bills
    cursor.execute('SELECT * FROM bills')
    bills = [dict(row) for row in cursor.fetchall()]
    
    if not bills:
        conn.close()
        return {"bill_id": None, "payment_count": 0, "last_payment": None}
    
    # Sort bills by date (most recent first)
    bills = sort_bills_by_date(bills, desc=True)
    most_recent_bill = bills[0]
    bill_id = most_recent_bill['id']
    
    # Count payments for this bill
    cursor.execute('''
        SELECT COUNT(*) as count FROM payments WHERE bill_id = ?
    ''', (bill_id,))
    count = cursor.fetchone()['count']
    
    # Get the "last" payment (first in order - most recent payment)
    cursor.execute('''
        SELECT p.*, u.name as payee_name
        FROM payments p
        LEFT JOIN payee_users u ON p.payee_user_id = u.id
        WHERE p.bill_id = ?
        ORDER BY 
            CASE WHEN p.manual_order IS NOT NULL THEN 1 ELSE 0 END,
            p.payment_date DESC,
            p.first_scraped_at DESC,
            p.manual_order ASC
        LIMIT 1
    ''', (bill_id,))
    
    last_payment_row = cursor.fetchone()
    last_payment = dict(last_payment_row) if last_payment_row else None
    
    conn.close()
    
    return {
        "bill_id": bill_id,
        "bill_cycle_date": most_recent_bill.get('bill_cycle_date', ''),
        "payment_count": count,
        "last_payment": last_payment
    }

def get_payments_by_user(user_id: int) -> List[Dict[str, Any]]:
    """Get all payments assigned to a specific user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, b.month_range as bill_month, b.bill_cycle_date as bill_cycle
        FROM payments p
        LEFT JOIN bills b ON p.bill_id = b.id
        WHERE p.payee_user_id = ?
        ORDER BY p.payment_date DESC
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_all_bills_with_payments() -> List[Dict[str, Any]]:
    """Get all bills with their payments for the Payments audit tab"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all bills (will be sorted in Python)
    cursor.execute('SELECT * FROM bills')
    bills = [dict(row) for row in cursor.fetchall()]
    
    # Get payments for each bill
    for bill in bills:
        cursor.execute('''
            SELECT p.*, u.name as payee_name FROM payments p
            LEFT JOIN payee_users u ON p.payee_user_id = u.id
            WHERE p.bill_id = ?
            ORDER BY 
                CASE WHEN p.manual_order IS NOT NULL THEN 1 ELSE 0 END,
                p.payment_date DESC, 
                p.first_scraped_at DESC,
                p.manual_order ASC
        ''', (bill['id'],))
        bill['payments'] = [dict(row) for row in cursor.fetchall()]
    
    # Get orphan payments
    cursor.execute('''
        SELECT p.*, u.name as payee_name FROM payments p
        LEFT JOIN payee_users u ON p.payee_user_id = u.id
        WHERE p.bill_id IS NULL
        ORDER BY p.payment_date DESC
    ''')
    orphan_payments = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Sort bills by date (newest first) using Python to handle variable date formats
    sorted_bills = sort_bills_by_date(bills, desc=True)
    
    return {'bills': sorted_bills, 'orphan_payments': orphan_payments}

def auto_assign_expired_pending_payments() -> Dict[str, Any]:
    """
    Find payments that are past their 2-hour pending window and still unassigned.
    Auto-assign them to the default payee.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Find payments that are pending and past their window
    cursor.execute('''
        SELECT id, amount, payment_date FROM payments 
        WHERE payee_status = 'pending' 
        AND payee_user_id IS NULL
        AND payee_pending_until IS NOT NULL
        AND payee_pending_until < ?
    ''', (now,))
    
    expired = cursor.fetchall()
    conn.close()
    
    if not expired:
        return {'assigned': 0, 'message': 'No expired pending payments'}
    
    # Get default payee
    default_payee = get_default_payee()
    if not default_payee:
        return {'assigned': 0, 'message': 'No default payee configured'}
    
    # Assign expired payments to default payee
    assigned = 0
    for payment in expired:
        try:
            attribute_payment(
                payment['id'],
                default_payee['id'],
                method='auto_timeout',
                card_last_four=None
            )
            assigned += 1
        except Exception as e:
            logging.warning(f"Failed to auto-assign payment {payment['id']}: {e}")
    
    return {
        'assigned': assigned,
        'default_payee': default_payee['name'],
        'message': f'Assigned {assigned} expired pending payments to {default_payee["name"]}'
    }

def wipe_bills_and_payments() -> Dict[str, int]:
    """Delete all bills and payments from the database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get counts before deletion
    cursor.execute('SELECT COUNT(*) FROM payments')
    payment_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM bills')
    bill_count = cursor.fetchone()[0]
    
    # Delete all payments first (foreign key constraint)
    cursor.execute('DELETE FROM payments')
    
    # Delete all bills
    cursor.execute('DELETE FROM bills')
    
    conn.commit()
    conn.close()
    
    return {'payments_deleted': payment_count, 'bills_deleted': bill_count}

# ==========================================
# ACCOUNT BALANCE FUNCTIONS
# ==========================================

def record_account_balance(balance: str) -> bool:
    """Record account balance, returns True if it changed"""
    conn = get_connection()
    cursor = conn.cursor()
    
    balance_numeric = parse_amount(balance)
    now = utc_now_iso()
    
    # Get previous balance
    cursor.execute('''
        SELECT balance FROM account_balance_history
        ORDER BY scraped_at DESC LIMIT 1
    ''')
    previous = cursor.fetchone()
    
    changed = False
    if previous is None or previous['balance'] != balance:
        changed = True
    
    # Always record if changed, or first entry
    if changed or previous is None:
        cursor.execute('''
            INSERT INTO account_balance_history (balance, balance_numeric, scraped_at, changed_from_previous)
            VALUES (?, ?, ?, ?)
        ''', (balance, balance_numeric, now, 1 if (previous and changed) else 0))
        conn.commit()
    
    conn.close()
    return changed

def get_current_balance() -> Optional[Dict[str, Any]]:
    """Get the current account balance"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM account_balance_history
        ORDER BY scraped_at DESC LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

# ==========================================
# PAYEE USER FUNCTIONS
# ==========================================

def create_payee_user(name: str, is_default: bool = False) -> int:
    """Create a new payee user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # If setting as default, clear other defaults
    if is_default:
        cursor.execute('UPDATE payee_users SET is_default = 0')
    
    cursor.execute('''
        INSERT INTO payee_users (name, is_default, created_at)
        VALUES (?, ?, ?)
    ''', (name, 1 if is_default else 0, utc_now_iso()))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def get_payee_users() -> List[Dict[str, Any]]:
    """Get all payee users with their cards"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.*, GROUP_CONCAT(c.card_last_four) as cards
        FROM payee_users u
        LEFT JOIN user_cards c ON u.id = c.user_id
        GROUP BY u.id
        ORDER BY u.name
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        user = dict(row)
        user['cards'] = row['cards'].split(',') if row['cards'] else []
        result.append(user)
    
    return result

def get_default_payee() -> Optional[Dict[str, Any]]:
    """Get the default payee user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM payee_users WHERE is_default = 1 LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

def delete_payee_user(user_id: int) -> bool:
    """Delete a payee user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM payee_users WHERE id = ?', (user_id,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    return deleted

def update_payee_user(user_id: int, name: Optional[str] = None, is_default: Optional[bool] = None) -> bool:
    """Update a payee user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if is_default:
        cursor.execute('UPDATE payee_users SET is_default = 0')
    
    updates = []
    params = []
    
    if name is not None:
        updates.append('name = ?')
        params.append(name)
    if is_default is not None:
        updates.append('is_default = ?')
        params.append(1 if is_default else 0)
    
    if updates:
        params.append(user_id)
        cursor.execute(f'UPDATE payee_users SET {", ".join(updates)} WHERE id = ?', params)
    
    conn.commit()
    conn.close()
    return True

def update_payee_responsibilities(responsibilities: Dict[int, float]) -> Dict[str, Any]:
    """
    Update responsibility percentages for multiple payees.
    responsibilities: {user_id: percent}
    Total must equal 100% (or all 0 if not configured)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    total = sum(responsibilities.values())
    
    # Validate: must be 100% or 0%
    if total > 0 and abs(total - 100.0) > 0.01:
        conn.close()
        return {'success': False, 'error': f'Total must equal 100%, got {total:.1f}%'}
    
    # Update all users
    for user_id, percent in responsibilities.items():
        cursor.execute('''
            UPDATE payee_users SET responsibility_percent = ? WHERE id = ?
        ''', (percent, user_id))
    
    conn.commit()
    conn.close()
    
    return {'success': True, 'total': total}

def calculate_all_payee_balances() -> Dict[int, Dict[str, Any]]:
    """
    Calculate payee balances for ALL bills at once, in chronological order.
    This is efficient (single pass) and ensures correct rollover calculation.
    
    Returns: {bill_id: {payee_summaries, bill_total, total_paid, etc}}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all bills
    cursor.execute('SELECT * FROM bills')
    bills = [dict(row) for row in cursor.fetchall()]
    
    if not bills:
        conn.close()
        return {}
    
    # Sort bills by date in chronological order (oldest first for correct rollover)
    bills = sort_bills_by_date(bills, desc=False)  # desc=False means oldest first
    
    # Get all payees
    cursor.execute('SELECT * FROM payee_users ORDER BY name')
    payees = [dict(row) for row in cursor.fetchall()]
    
    # Get ALL payments grouped by bill and payee (single query)
    cursor.execute('''
        SELECT bill_id, payee_user_id, SUM(amount_numeric) as total_paid
        FROM payments
        WHERE bill_id IS NOT NULL AND payee_user_id IS NOT NULL
        GROUP BY bill_id, payee_user_id
    ''')
    payments_map = {}
    for row in cursor.fetchall():
        bill_id = row['bill_id']
        payee_id = row['payee_user_id']
        if bill_id not in payments_map:
            payments_map[bill_id] = {}
        payments_map[bill_id][payee_id] = row['total_paid'] or 0
    
    # Get total payments per bill (for bill balance)
    cursor.execute('''
        SELECT bill_id, SUM(amount_numeric) as total_paid
        FROM payments
        WHERE bill_id IS NOT NULL
        GROUP BY bill_id
    ''')
    bill_totals_paid = {row['bill_id']: row['total_paid'] or 0 for row in cursor.fetchall()}
    
    conn.close()
    
    # Initialize running rollover for each payee (starts at 0)
    payee_rollover = {payee['id']: 0.0 for payee in payees}
    
    # Result storage
    results = {}
    
    # Process bills in chronological order (oldest to newest)
    for bill in bills:
        bill_id = bill['id']
        bill_total = parse_amount(bill.get('bill_total', '$0'))
        payments_for_bill = payments_map.get(bill_id, {})
        total_paid = bill_totals_paid.get(bill_id, 0)
        
        payee_summaries = []
        
        for payee in payees:
            payee_id = payee['id']
            responsibility = payee.get('responsibility_percent', 0) or 0
            
            # Their share of THIS bill
            share = bill_total * (responsibility / 100.0) if responsibility > 0 else 0
            
            # What they paid toward THIS bill
            paid = payments_for_bill.get(payee_id, 0)
            
            # Their rollover FROM previous bills (captured before we update it)
            rollover_in = payee_rollover[payee_id]
            
            # This period's result: positive = overpaid, negative = underpaid
            period_balance = paid - share
            
            # Total balance including rollover (positive = credit, negative = owes)
            total_balance = rollover_in + period_balance
            
            payee_summaries.append({
                'user_id': payee_id,
                'name': payee['name'],
                'responsibility_percent': responsibility,
                'share_of_bill': round(share, 2),
                'amount_paid': round(paid, 2),
                'rollover_in': round(rollover_in, 2),
                'period_balance': round(period_balance, 2),
                'total_balance': round(total_balance, 2),
                'status': 'credit' if total_balance > 0.01 else ('settled' if abs(total_balance) <= 0.01 else 'owes')
            })
            
            # Update rollover for next bill
            payee_rollover[payee_id] = total_balance
        
        bill_balance = bill_total - total_paid
        
        results[bill_id] = {
            'bill_id': bill_id,
            'bill_total': round(bill_total, 2),
            'total_paid': round(total_paid, 2),
            'bill_balance': round(bill_balance, 2),
            'bill_status': 'paid' if bill_balance <= 0.01 else ('partial' if total_paid > 0 else 'unpaid'),
            'payee_summaries': payee_summaries
        }
    
    return results


def get_bill_payee_summary(bill_id: int) -> Dict[str, Any]:
    """
    Get payee breakdown for a specific bill.
    Uses the efficient all-at-once calculation.
    """
    all_summaries = calculate_all_payee_balances()
    return all_summaries.get(bill_id, {})

def get_all_bill_summaries() -> List[Dict[str, Any]]:
    """Get summaries for all bills"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM bills')
    bill_ids = [row['id'] for row in cursor.fetchall()]
    conn.close()
    
    summaries = []
    for bill_id in bill_ids:
        summary = get_bill_payee_summary(bill_id)
        if summary:
            summaries.append(summary)
    
    return summaries

# ==========================================
# USER CARD FUNCTIONS
# ==========================================

def add_user_card(user_id: int, card_last_four: str, label: Optional[str] = None) -> int:
    """Add a card to a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Validate 4 digits
    card_last_four = card_last_four.strip()[-4:]
    
    cursor.execute('''
        INSERT INTO user_cards (user_id, card_last_four, card_label, created_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, card_last_four, label, utc_now_iso()))
    
    card_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return card_id

def get_user_by_card(card_last_four: str) -> Optional[Dict[str, Any]]:
    """Find user by card last four digits"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.* FROM payee_users u
        JOIN user_cards c ON u.id = c.user_id
        WHERE c.card_last_four = ?
    ''', (card_last_four,))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

def delete_user_card(card_id: int) -> bool:
    """Delete a card"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM user_cards WHERE id = ?', (card_id,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    return deleted

# ==========================================
# PAYMENT ATTRIBUTION FUNCTIONS
# ==========================================

def attribute_payment(payment_id: int, user_id: int, method: str = 'manual', card_last_four: Optional[str] = None) -> bool:
    """Attribute a payment to a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE payments SET 
            payee_user_id = ?,
            payee_status = 'confirmed',
            verification_method = ?,
            card_last_four = ?
        WHERE id = ?
    ''', (user_id, method, card_last_four, payment_id))
    
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def clear_payment_attribution(payment_id: int) -> bool:
    """Clear payment attribution (unassign from user)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE payments SET 
            payee_user_id = NULL,
            payee_status = 'unverified',
            verification_method = NULL,
            card_last_four = NULL
        WHERE id = ?
    ''', (payment_id,))
    
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated

def get_unverified_payments(limit: int = 50) -> List[Dict[str, Any]]:
    """Get payments that need verification"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, b.month_range as bill_month FROM payments p
        LEFT JOIN bills b ON p.bill_id = b.id
        WHERE p.payee_status = 'unverified'
        ORDER BY p.payment_date DESC, p.first_scraped_at ASC
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

# ==========================================
# DATA SYNC FROM SCRAPE
# ==========================================

def parse_date_for_comparison(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime for comparison. Handles M/D/YYYY format."""
    if not date_str:
        return None
    try:
        # ConEd uses M/D/YYYY format
        return datetime.strptime(date_str, '%m/%d/%Y')
    except ValueError:
        try:
            # Try alternate format
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return None

def find_bill_for_payment(payment_date_str: str, bills: List[Dict[str, Any]]) -> Optional[int]:
    """
    Find the appropriate bill for a payment based on payment date.
    
    bill_cycle_date = END of billing cycle (date bill was issued)
    A payment belongs to a bill if:
      - payment_date >= this_bill.cycle_date (can't be before the bill was issued)
      - payment_date < next_bill.cycle_date (must be before the next bill)
    """
    payment_date = parse_date_for_comparison(payment_date_str)
    if not payment_date:
        return None
    
    # Sort bills by cycle date ascending (oldest first)
    sorted_bills = []
    for bill in bills:
        cycle_date = parse_date_for_comparison(bill['bill_cycle_date'])
        if cycle_date:
            sorted_bills.append({
                'bill_id': bill['bill_id'],
                'cycle_date': cycle_date
            })
    
    sorted_bills.sort(key=lambda x: x['cycle_date'])  # Ascending (oldest first)
    
    if not sorted_bills:
        return None
    
    # Find the bill where: bill.cycle_date <= payment_date < next_bill.cycle_date
    for i, bill in enumerate(sorted_bills):
        is_after_bill = payment_date >= bill['cycle_date']
        
        # Check if before next bill (or no next bill)
        if i + 1 < len(sorted_bills):
            is_before_next = payment_date < sorted_bills[i + 1]['cycle_date']
        else:
            is_before_next = True  # No next bill, so this is the latest
        
        if is_after_bill and is_before_next:
            return bill['bill_id']
    
    # If payment is before all bills, assign to the oldest bill
    return sorted_bills[0]['bill_id']

def sync_from_scrape(scrape_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sync scraped data to normalized tables, returns stats"""
    stats = {
        'bills_added': 0,
        'bills_updated': 0,
        'payments_added': 0,
        'payments_updated': 0,
        'balance_changed': False
    }
    
    # Sync account balance
    if 'account_balance' in scrape_data:
        stats['balance_changed'] = record_account_balance(scrape_data['account_balance'])
    
    # Sync bill history
    bill_history = scrape_data.get('bill_history', {})
    ledger = bill_history.get('ledger', [])
    
    # First pass: collect all bills
    bills_info = []
    for item in ledger:
        if item.get('type') == 'bill':
            bill_id = upsert_bill(item)
            bills_info.append({
                'bill_id': bill_id,
                'bill_cycle_date': item.get('bill_cycle_date', '')
            })
    
    # Second pass: process all payments
    payment_order = 0
    for item in ledger:
        if item.get('type') == 'payment':
            payment_order += 1
            payment_date = item.get('bill_cycle_date', '')  # ConEd uses bill_cycle_date for payment date too
            
            # Check if this payment already exists and is manually set
            description = item.get('description', 'Payment Received')
            amount = item.get('amount', '')
            payment_hash = generate_payment_hash(payment_date, amount, description, '')
            
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, bill_manually_set FROM payments WHERE payment_hash = ?', (payment_hash,))
            existing = cursor.fetchone()
            conn.close()
            
            if existing and existing['bill_manually_set'] == 1:
                # Payment has manually set bill, just update scrape timestamp
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE payments SET last_scraped_at = ?, scrape_count = scrape_count + 1
                    WHERE id = ?
                ''', (utc_now_iso(), existing['id']))
                conn.commit()
                conn.close()
            else:
                # Find appropriate bill based on payment date
                assigned_bill_id = find_bill_for_payment(payment_date, bills_info)
                upsert_payment(item, bill_id=assigned_bill_id, scrape_order=payment_order)
    
    return stats

# ==========================================
# LEDGER VIEW (for AccountLedger component)
# ==========================================

def get_ledger_data() -> Dict[str, Any]:
    """Get complete ledger data for the frontend"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get current balance
    balance = get_current_balance()
    
    # Get all bills (will sort in Python to handle variable date formats like M/D/YYYY)
    cursor.execute('SELECT * FROM bills LIMIT 50')
    bills = [dict(row) for row in cursor.fetchall()]
    
    # Sort bills by date (newest first)
    bills = sort_bills_by_date(bills, desc=True)
    
    # Get payments grouped by bill
    # Order: manual_order first (if set), then payment_date DESC, then first_scraped_at ASC
    for bill in bills:
        cursor.execute('''
            SELECT p.*, u.name as payee_name FROM payments p
            LEFT JOIN payee_users u ON p.payee_user_id = u.id
            WHERE p.bill_id = ?
            ORDER BY 
                CASE WHEN p.manual_order IS NOT NULL THEN 1 ELSE 0 END,
                p.payment_date DESC, 
                p.first_scraped_at DESC,
                p.manual_order ASC
        ''', (bill['id'],))
        bill['payments'] = [dict(row) for row in cursor.fetchall()]
    
    # Get orphan payments (no bill assigned) and add them to a special section
    cursor.execute('''
        SELECT p.*, u.name as payee_name FROM payments p
        LEFT JOIN payee_users u ON p.payee_user_id = u.id
        WHERE p.bill_id IS NULL
        ORDER BY 
            CASE WHEN p.manual_order IS NOT NULL THEN 0 ELSE 1 END,
            p.manual_order ASC,
            p.payment_date DESC, 
            p.first_scraped_at ASC
    ''')
    orphan_payments = [dict(row) for row in cursor.fetchall()]
    
    # Get latest payment overall
    latest_payment = get_latest_payment()
    
    # Get latest bill
    latest_bill = bills[0] if bills else None
    
    conn.close()
    
    return {
        'account_balance': balance['balance'] if balance else None,
        'balance_updated_at': balance['scraped_at'] if balance else None,
        'latest_payment': latest_payment,
        'latest_bill': latest_bill,
        'bills': bills,
        'orphan_payments': orphan_payments
    }

# ==========================================
# LEGACY FUNCTIONS (keep for backward compat)
# ==========================================

def save_scraped_data(data: Dict[str, Any], status: str = "success", error_message: Optional[str] = None, screenshot_path: Optional[str] = None):
    """Save scraped data to database. Also syncs to normalized tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = utc_now_iso()
    
    # Insert new data
    cursor.execute('''
        INSERT INTO scraped_data (timestamp, data, status, error_message, screenshot_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (timestamp, json.dumps(data), status, error_message, screenshot_path))
    
    # Keep only latest 2 entries
    cursor.execute('''
        DELETE FROM scraped_data
        WHERE id NOT IN (
            SELECT id FROM scraped_data
            ORDER BY timestamp DESC
            LIMIT 2
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Sync to normalized tables
    if status == "success":
        try:
            sync_from_scrape(data)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync to normalized tables: {e}")
        
        # Publish sensors to MQTT
        try:
            from sensor_publisher import publish_sensors
            publish_sensors(data, timestamp)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to publish sensors: {e}")

def get_latest_scraped_data(limit: int = 1) -> List[Dict[str, Any]]:
    """Get latest scraped data"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM scraped_data
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        screenshot_path = None
        try:
            if "screenshot_path" in row.keys():
                screenshot_path = row["screenshot_path"]
        except (KeyError, AttributeError):
            pass
        
        result.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "data": json.loads(row["data"]),
            "status": row["status"],
            "error_message": row["error_message"],
            "screenshot_path": screenshot_path
        })
    
    return result

def get_all_scraped_data(limit: int = 100) -> List[Dict[str, Any]]:
    """Get all scraped data"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM scraped_data
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        screenshot_path = None
        try:
            if "screenshot_path" in row.keys():
                screenshot_path = row["screenshot_path"]
        except (KeyError, AttributeError):
            pass
        
        result.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "data": json.loads(row["data"]),
            "status": row["status"],
            "error_message": row["error_message"],
            "screenshot_path": screenshot_path
        })
    
    return result

def add_log(level: str, message: str):
    """Add log entry"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO logs (timestamp, level, message)
        VALUES (?, ?, ?)
    ''', (utc_now_iso(), level, message))
    
    conn.commit()
    conn.close()

def get_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Get log entries"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM logs
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [{"id": row["id"], "timestamp": row["timestamp"], "level": row["level"], "message": row["message"]} for row in rows]

def clear_logs():
    """Clear all log entries"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM logs')
    conn.commit()
    conn.close()

def add_scrape_history(success: bool, error_message: Optional[str] = None, failure_step: Optional[str] = None, duration_seconds: Optional[float] = None):
    """Add scrape history entry"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO scrape_history (timestamp, success, error_message, failure_step, duration_seconds)
        VALUES (?, ?, ?, ?, ?)
    ''', (utc_now_iso(), 1 if success else 0, error_message, failure_step, duration_seconds))
    
    cursor.execute('''
        DELETE FROM scrape_history
        WHERE id NOT IN (
            SELECT id FROM scrape_history
            ORDER BY timestamp DESC
            LIMIT 100
        )
    ''')
    
    conn.commit()
    conn.close()

def get_scrape_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Get scrape history entries"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM scrape_history
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        "id": row["id"],
        "timestamp": row["timestamp"],
        "success": bool(row["success"]),
        "error_message": row["error_message"],
        "failure_step": row["failure_step"],
        "duration_seconds": row["duration_seconds"]
    } for row in rows]

# Initialize database on import
init_database()
