"""第6章：SQLite 简单存储。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / "pages.db"
conn = sqlite3.connect(db_path)
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS pages (
        url TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        scraped_at TEXT NOT NULL
    )
    """
)
conn.execute(
    "INSERT OR REPLACE INTO pages VALUES (?,?,?)",
    ("https://example.com", "Example", "2026-01-01T00:00:00Z"),
)
conn.commit()
for row in conn.execute("SELECT * FROM pages"):
    print(row)
conn.close()
print("db:", db_path)
