import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "tickets.db"


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                created_at TEXT NOT NULL
            )
            """
        )


def create_ticket(
    name: str,
    description: str,
    priority: str,
    confidence: float,
) -> int:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tickets (name, description, priority, confidence, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, description, priority, confidence, created_at),
        )
        return int(cursor.lastrowid)


def get_open_tickets() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM tickets WHERE status = 'OPEN' ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def get_ticket_by_id(ticket_id: int) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return dict(row) if row is not None else None


def clear_ticket(ticket_id: int) -> bool:
    with _connect() as connection:
        cursor = connection.execute(
            "UPDATE tickets SET status = 'CLEARED' WHERE id = ?", (ticket_id,)
        )
        return cursor.rowcount > 0


initialize_database()