"""
Lightweight SQLite-backed history log. Using a real DB file (instead of only
st.session_state, which resets on every restart) means readings survive a
restart and every page reads the same shared history.
"""

import sqlite3
from contextlib import contextmanager

import pandas as pd

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process TEXT NOT NULL,
    source TEXT NOT NULL,
    batch INTEGER NOT NULL,
    day REAL NOT NULL,
    recorded_at TEXT NOT NULL,
    pH REAL, conductivity REAL,
    temperature_C REAL, pressure_bar REAL
);
"""

COLUMNS = [
    "process", "source", "batch", "day", "recorded_at",
    "pH", "conductivity",
    "temperature_C", "pressure_bar",
]


@contextmanager
def get_conn(db_path=config.DB_PATH):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_reading(row, db_path=config.DB_PATH):
    """row: dict with any subset of COLUMNS (missing keys -> NULL)."""
    values = [row.get(c) for c in COLUMNS]
    placeholders = ",".join("?" * len(COLUMNS))
    with get_conn(db_path) as conn:
        conn.execute(
            f"INSERT INTO readings ({','.join(COLUMNS)}) VALUES ({placeholders})", values
        )


def load_history(process=None, batch=None, source=None, db_path=config.DB_PATH):
    query = "SELECT * FROM readings WHERE 1=1"
    params = []
    if process:
        query += " AND process = ?"
        params.append(process)
    if batch is not None:
        query += " AND batch = ?"
        params.append(batch)
    if source:
        query += " AND source = ?"
        params.append(source)
    query += " ORDER BY day ASC"
    with get_conn(db_path) as conn:
        return pd.read_sql_query(query, conn, params=params)


def next_batch_number(process, db_path=config.DB_PATH):
    with get_conn(db_path) as conn:
        cur = conn.execute("SELECT MAX(batch) FROM readings WHERE process = ?", (process,))
        result = cur.fetchone()[0]
    return (result or 0) + 1