"""SQLite schema and CRUD helpers for posts, leads, and outreach drafts."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "linkedin.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    topic TEXT NOT NULL,
    body_text TEXT NOT NULL,
    infographic_path TEXT,
    infographic_type TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    scheduled_for TEXT
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    title TEXT,
    company TEXT,
    company_size INTEGER,
    industry TEXT,
    linkedin_url TEXT,
    email TEXT,
    source TEXT,
    fit_score INTEGER,
    status TEXT NOT NULL DEFAULT 'new',
    notes TEXT,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    post_id_ref INTEGER REFERENCES posts(id),
    message_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);
"""


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- posts -------------------------------------------------------------

def create_post(category: str, topic: str, body_text: str, scheduled_for: str | None = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO posts (category, topic, body_text, status, created_at, scheduled_for) "
            "VALUES (?, ?, ?, 'draft', ?, ?)",
            (category, topic, body_text, _now(), scheduled_for),
        )
        return cur.lastrowid


def set_post_infographic(post_id: int, infographic_path: str, infographic_type: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE posts SET infographic_path = ?, infographic_type = ? WHERE id = ?",
            (infographic_path, infographic_type, post_id),
        )


def update_post_status(post_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE posts SET status = ? WHERE id = ?", (status, post_id))


def list_posts(status: str | None = None) -> list[sqlite3.Row]:
    with get_conn() as conn:
        if status:
            return conn.execute(
                "SELECT * FROM posts WHERE status = ? ORDER BY created_at DESC", (status,)
            ).fetchall()
        return conn.execute("SELECT * FROM posts ORDER BY created_at DESC").fetchall()


def category_counts() -> dict[str, int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) as n FROM posts WHERE status != 'discarded' GROUP BY category"
        ).fetchall()
        return {row["category"]: row["n"] for row in rows}


# --- leads ---------------------------------------------------------------

def insert_lead(**fields) -> int:
    fields.setdefault("status", "new")
    fields["imported_at"] = _now()
    columns = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO leads ({columns}) VALUES ({placeholders})",
            tuple(fields.values()),
        )
        return cur.lastrowid


def update_lead_score(lead_id: int, fit_score: int):
    with get_conn() as conn:
        conn.execute("UPDATE leads SET fit_score = ? WHERE id = ?", (fit_score, lead_id))


def update_lead_status(lead_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))


def list_leads(order_by: str = "fit_score DESC") -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(f"SELECT * FROM leads ORDER BY {order_by}").fetchall()


# --- outreach drafts -------------------------------------------------------

def create_outreach_draft(lead_id: int, message_text: str, post_id_ref: int | None = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO outreach_drafts (lead_id, post_id_ref, message_text, status, created_at) "
            "VALUES (?, ?, ?, 'draft', ?)",
            (lead_id, post_id_ref, message_text, _now()),
        )
        return cur.lastrowid


def update_outreach_status(draft_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE outreach_drafts SET status = ? WHERE id = ?", (status, draft_id))


def list_outreach_drafts(lead_id: int | None = None) -> list[sqlite3.Row]:
    with get_conn() as conn:
        if lead_id:
            return conn.execute(
                "SELECT * FROM outreach_drafts WHERE lead_id = ? ORDER BY created_at DESC",
                (lead_id,),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM outreach_drafts ORDER BY created_at DESC"
        ).fetchall()
