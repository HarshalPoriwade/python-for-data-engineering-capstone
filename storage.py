"""Save sales lines in a local SQLite database and read them back."""

import sqlite3

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine TEXT NOT NULL,
    item TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    quantity REAL NOT NULL,
    date TEXT NOT NULL,
    UNIQUE (machine, item, date)
)
"""

INSERT_SQL = """
INSERT OR IGNORE INTO sales (machine, item, price_cents, quantity, date)
VALUES (?, ?, ?, ?, ?)
"""


def connect(db_path):
    """Open the database file (SQLite creates it if needed) and make the table."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
    except sqlite3.Error:
        # Close before giving up, or Windows keeps the file locked.
        conn.close()
        raise
    return conn


def insert_sales(conn, records):
    """Insert valid records and return how many rows were really added.

    A record whose (machine, item, date) is already stored is skipped
    by INSERT OR IGNORE, so loading the same file twice adds nothing.
    """
    before = conn.total_changes
    for r in records:
        conn.execute(
            INSERT_SQL,
            (r["machine"], r["item"], r["price_cents"], r["quantity"], r["date"]),
        )
    conn.commit()
    return conn.total_changes - before


def fetch_sales(conn):
    """Return every stored sale as a list of dictionaries."""
    cursor = conn.execute(
        "SELECT machine, item, price_cents, quantity, date FROM sales ORDER BY id"
    )
    rows = []
    for machine, item, price_cents, quantity, date in cursor.fetchall():
        rows.append({
            "machine": machine,
            "item": item,
            "price_cents": price_cents,
            "quantity": quantity,
            "date": date,
        })
    return rows