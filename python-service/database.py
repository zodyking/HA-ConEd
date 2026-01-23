import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_PATH = Path(__file__).parent / "data" / "scraper.db"

def init_database():
    """Initialize SQLite database"""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create scraped_data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraped_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            data TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT
        )
    ''')
    
    # Create logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def save_scraped_data(data: Dict[str, Any], status: str = "success", error_message: Optional[str] = None):
    """Save scraped data to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO scraped_data (timestamp, data, status, error_message)
        VALUES (?, ?, ?, ?)
    ''', (datetime.now().isoformat(), json.dumps(data), status, error_message))
    
    conn.commit()
    conn.close()

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
        result.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "data": json.loads(row["data"]),
            "status": row["status"],
            "error_message": row["error_message"]
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
        result.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "data": json.loads(row["data"]),
            "status": row["status"],
            "error_message": row["error_message"]
        })
    
    return result

def add_log(level: str, message: str):
    """Add log entry"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO logs (timestamp, level, message)
        VALUES (?, ?, ?)
    ''', (datetime.now().isoformat(), level, message))
    
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
    
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "level": row["level"],
            "message": row["message"]
        })
    
    return result

# Initialize database on import
init_database()
