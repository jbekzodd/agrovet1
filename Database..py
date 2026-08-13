"""
AgroVet AI — SQLite ma'lumotlar bazasi
"""
import sqlite3
from datetime import datetime

DB_PATH = "agrovet.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            animal_name TEXT NOT NULL,
            reminder_type TEXT NOT NULL,
            reminder_date TEXT NOT NULL,
            note TEXT,
            sent INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_reminder(chat_id: int, animal_name: str, reminder_type: str, reminder_date: str, note: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reminders (chat_id, animal_name, reminder_type, reminder_date, note, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (chat_id, animal_name, reminder_type, reminder_date, note, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_reminders_for_date(date_str: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, chat_id, animal_name, reminder_type, note FROM reminders "
        "WHERE reminder_date = ? AND sent = 0",
        (date_str,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_as_sent(reminder_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


def get_user_reminders(chat_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT animal_name, reminder_type, reminder_date, note FROM reminders "
