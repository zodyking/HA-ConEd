import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
import hashlib

def utc_now_iso() -> str:
    """Get current UTC time as ISO string"""
    return datetime.now(timezone.utc).isoformat()

# Use /data for persistent storage (mounted volume in Home Assistant)
DB_PATH = Path("./data") / "scraper.db"

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
            FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE SET NULL,
            FOREIGN KEY (payee_user_id) REFERENCES payee_users(id) ON DELETE SET NULL
        )
    ''')
    
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
            created_at TEXT NOT NULL
        )
    ''')
    
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

def get_all_bills(limit: int = 100) -> List[Dict[str, Any]]:
    """Get all bills ordered by first_scraped_at (newest first)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM bills
        ORDER BY bill_cycle_date DESC, first_scraped_at DESC
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

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
        # Insert new payment
        cursor.execute('''
            INSERT INTO payments (bill_id, payment_date, description, amount, amount_numeric, 
                                  first_scraped_at, last_scraped_at, scrape_order, payment_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (bill_id, payment_date, description, amount, amount_numeric, now, now, scrape_order, payment_hash))
        payment_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return payment_id

def get_all_payments(limit: int = 100, bill_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all payments ordered by first_scraped_at (newest first)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if bill_id:
        cursor.execute('''
            SELECT p.*, u.name as payee_name FROM payments p
            LEFT JOIN payee_users u ON p.payee_user_id = u.id
            WHERE p.bill_id = ?
            ORDER BY p.payment_date DESC, p.first_scraped_at ASC
            LIMIT ?
        ''', (bill_id, limit))
    else:
        cursor.execute('''
            SELECT p.*, u.name as payee_name FROM payments p
            LEFT JOIN payee_users u ON p.payee_user_id = u.id
            ORDER BY p.payment_date DESC, p.first_scraped_at ASC
            LIMIT ?
        ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_latest_payment() -> Optional[Dict[str, Any]]:
    """Get the most recent payment by payment_date (then first_scraped_at for same-day)"""
    payments = get_all_payments(limit=1)
    return payments[0] if payments else None

def get_payments_for_bill(bill_id: int) -> List[Dict[str, Any]]:
    """Get all payments for a specific bill"""
    return get_all_payments(limit=100, bill_id=bill_id)

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
    
    # First pass: collect all bills and their positions
    bills_in_order = []
    for idx, item in enumerate(ledger):
        if item.get('type') == 'bill':
            bill_id = upsert_bill(item)
            bills_in_order.append({
                'bill_id': bill_id,
                'bill_cycle_date': item.get('bill_cycle_date', ''),
                'ledger_index': idx
            })
    
    # Second pass: process all payments and assign to appropriate bill
    payment_order = 0
    for idx, item in enumerate(ledger):
        if item.get('type') == 'payment':
            payment_order += 1
            payment_date = item.get('bill_cycle_date', '')
            
            # Find the bill this payment belongs to
            # Payments appear BEFORE their associated bill in ConEd's ledger
            # So we find the first bill that comes AFTER this payment in the ledger
            assigned_bill_id = None
            for bill_info in bills_in_order:
                if bill_info['ledger_index'] > idx:
                    assigned_bill_id = bill_info['bill_id']
                    break
            
            # If no bill found after payment, assign to the most recent bill
            if assigned_bill_id is None and bills_in_order:
                assigned_bill_id = bills_in_order[0]['bill_id']
            
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
    
    # Get all bills with their payments (order by bill_cycle_date for proper chronological order)
    cursor.execute('''
        SELECT * FROM bills
        ORDER BY bill_cycle_date DESC, first_scraped_at DESC
        LIMIT 50
    ''')
    bills = [dict(row) for row in cursor.fetchall()]
    
    # Get payments grouped by bill (order by payment_date, then first_scraped_at for same-day payments)
    for bill in bills:
        cursor.execute('''
            SELECT p.*, u.name as payee_name FROM payments p
            LEFT JOIN payee_users u ON p.payee_user_id = u.id
            WHERE p.bill_id = ?
            ORDER BY p.payment_date DESC, p.first_scraped_at ASC
        ''', (bill['id'],))
        bill['payments'] = [dict(row) for row in cursor.fetchall()]
    
    # Get orphan payments (no bill assigned) and add them to a special section
    cursor.execute('''
        SELECT p.*, u.name as payee_name FROM payments p
        LEFT JOIN payee_users u ON p.payee_user_id = u.id
        WHERE p.bill_id IS NULL
        ORDER BY p.payment_date DESC, p.first_scraped_at ASC
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
