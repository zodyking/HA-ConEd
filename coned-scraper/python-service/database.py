import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Use /data for persistent storage (mounted volume in Home Assistant)
DB_PATH = Path("./data") / "scraper.db"

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
            error_message TEXT,
            screenshot_path TEXT
        )
    ''')
    
    # Add screenshot_path column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE scraped_data ADD COLUMN screenshot_path TEXT')
    except sqlite3.OperationalError:
        # Column already exists, ignore
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
    
    conn.commit()
    conn.close()

def save_scraped_data(data: Dict[str, Any], status: str = "success", error_message: Optional[str] = None, screenshot_path: Optional[str] = None):
    """Save scraped data to database. Keeps only latest 2 entries."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    
    # Insert new data
    cursor.execute('''
        INSERT INTO scraped_data (timestamp, data, status, error_message, screenshot_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (timestamp, json.dumps(data), status, error_message, screenshot_path))
    
    # Keep only latest 2 entries - delete older ones
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
    
    # Publish sensors to MQTT if status is success
    if status == "success":
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
        # Get screenshot_path safely - check if column exists
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
        # Get screenshot_path safely - check if column exists
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

def clear_logs():
    """Clear all log entries"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM logs')
    
    conn.commit()
    conn.close()

# Initialize database on import
init_database()
