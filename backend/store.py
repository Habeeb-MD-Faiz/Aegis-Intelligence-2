"""
Persistence.

Previously every record lived in a module-level list or dict, so a restart —
or Render's free tier putting the dyno to sleep — erased all history. That is
awkward for a demo and fatal for an audit trail, since the ledger is only
meaningful if the decisions it records are still there.

This is deliberately a thin SQLite layer that stores records as JSON blobs.
It keeps the existing dict-shaped API intact (callers did not need rewriting)
and avoids inventing a migration story for a prototype, while delivering the
persistence the roadmap already promised.
"""

import json
import sqlite3
import threading
from typing import Dict, List, Optional

import config


_lock = threading.Lock()
_connection: Optional[sqlite3.Connection] = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    data        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id  TEXT PRIMARY KEY,
    request_id  TEXT,
    created_at  TEXT NOT NULL,
    data        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_requests_created
    ON requests (created_at);

CREATE INDEX IF NOT EXISTS idx_payments_request
    ON payments (request_id);
"""


def connect() -> sqlite3.Connection:
    global _connection

    if _connection is None:
        config.DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

        _connection = sqlite3.connect(
            config.DATABASE_FILE,
            check_same_thread=False,
        )
        _connection.row_factory = sqlite3.Row
        _connection.executescript(SCHEMA)
        _connection.commit()

    return _connection


# ============================================================
# REQUESTS
# ============================================================

def save_request(record: Dict) -> Dict:
    connection = connect()

    with _lock:
        connection.execute(
            "INSERT INTO requests (id, created_at, data) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (
                record["id"],
                record.get("createdAt", ""),
                json.dumps(record),
            ),
        )
        connection.commit()

    return record


def load_requests() -> List[Dict]:
    connection = connect()

    with _lock:
        rows = connection.execute(
            "SELECT data FROM requests ORDER BY created_at ASC"
        ).fetchall()

    return [json.loads(row["data"]) for row in rows]


def load_request(request_id: str) -> Optional[Dict]:
    connection = connect()

    with _lock:
        row = connection.execute(
            "SELECT data FROM requests WHERE id = ?",
            (request_id,),
        ).fetchone()

    return json.loads(row["data"]) if row else None


# ============================================================
# PAYMENTS
# ============================================================

def save_payment(payment: Dict) -> Dict:
    connection = connect()

    with _lock:
        connection.execute(
            "INSERT INTO payments (payment_id, request_id, created_at, data) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(payment_id) DO UPDATE SET data = excluded.data",
            (
                payment["payment_id"],
                payment.get("request_id"),
                payment.get("created_at", ""),
                json.dumps(payment),
            ),
        )
        connection.commit()

    return payment


def load_payments() -> List[Dict]:
    connection = connect()

    with _lock:
        rows = connection.execute(
            "SELECT data FROM payments ORDER BY created_at ASC"
        ).fetchall()

    return [json.loads(row["data"]) for row in rows]


def load_payment(payment_id: str) -> Optional[Dict]:
    connection = connect()

    with _lock:
        row = connection.execute(
            "SELECT data FROM payments WHERE payment_id = ?",
            (payment_id,),
        ).fetchone()

    return json.loads(row["data"]) if row else None


# ============================================================
# MAINTENANCE
# ============================================================

def reset() -> None:
    """
    Wipe all stored state. Used by tests and the demo script.
    """

    connection = connect()

    with _lock:
        connection.execute("DELETE FROM requests")
        connection.execute("DELETE FROM payments")
        connection.commit()
