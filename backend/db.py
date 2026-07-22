# backend/db.py
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Read DB configuration from environment variables
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

def get_connection():
    """Establishes and returns a MySQL database connection."""
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        if connection.is_connected():
            print("✅ Connected to MySQL database")
        return connection
    except Error as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return None

def close_connection(connection):
    """Closes the given database connection."""
    if connection and connection.is_connected():
        connection.close()
        print("✅ MySQL connection closed")

# ================== ACADEMIC YEAR HELPERS ==================
import datetime
import re

CURRENT_ACADEMIC_YEAR = None

def calculate_current_academic_year():
    """Calculate the default active academic year based on current date"""
    now = datetime.datetime.now()
    year = now.year
    month = now.month
    if month < 7:
        return f"{year-1}-{str(year)[2:]}"
    else:
        return f"{year}-{str(year+1)[2:]}"

def _load_academic_year_from_db():
    """Load the persisted academic year from the system_settings DB table.
    Returns None if unavailable (table missing, no row, or connection failed)."""
    try:
        connection = mysql.connector.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = connection.cursor()
        cursor.execute(
            "SELECT setting_value FROM system_settings WHERE setting_key = 'active_academic_year'"
        )
        row = cursor.fetchone()
        connection.close()
        if row:
            return row[0]
    except Exception:
        pass
    return None

def _save_academic_year_to_db(year: str):
    """Persist the academic year in the system_settings DB table."""
    try:
        connection = mysql.connector.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = connection.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS system_settings (
                setting_key VARCHAR(100) PRIMARY KEY,
                setting_value VARCHAR(255) NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
        )
        cursor.execute(
            """INSERT INTO system_settings (setting_key, setting_value)
               VALUES ('active_academic_year', %s)
               ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)""",
            (year,)
        )
        connection.commit()
        connection.close()
    except Exception as e:
        print(f"Warning: Could not persist academic year to DB: {e}")

def get_academic_year():
    """Get the current active academic year.
    Loads from DB on first call so the value survives server restarts."""
    global CURRENT_ACADEMIC_YEAR
    if CURRENT_ACADEMIC_YEAR is None:
        # Try DB first, then fall back to date-based calculation
        db_year = _load_academic_year_from_db()
        CURRENT_ACADEMIC_YEAR = db_year if db_year else calculate_current_academic_year()
        print(f"📅 Active academic year loaded: {CURRENT_ACADEMIC_YEAR}")
    return CURRENT_ACADEMIC_YEAR

def set_academic_year(year: str):
    """Set the active academic year server-wide AND persist it to the DB."""
    global CURRENT_ACADEMIC_YEAR
    CURRENT_ACADEMIC_YEAR = year
    _save_academic_year_to_db(year)
    print(f"📅 Academic year updated to: {year}")

def add_year_prefix(val, year=None):
    """Prepend the current academic year prefix to a value if not already present"""
    if not val:
        return val
    if year is None:
        year = get_academic_year()
    prefix = f"{year}_"
    if str(val).startswith(prefix):
        return val
    return f"{prefix}{val}"

def strip_year_prefix(val):
    """Remove any academic year prefix from a value"""
    if not val:
        return val
    # Remove any pattern matching 'YYYY-YY_' (e.g. 2025-26_)
    cleaned = re.sub(r'^\d{4}-\d{2}_', '', str(val))
    return cleaned

