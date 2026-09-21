"""Postgres schema and CRUD helpers for posts, leads, and outreach drafts.

Uses a hosted Postgres (e.g. Supabase or Neon's free tier) via DATABASE_URL rather than local
SQLite, so data persists identically whether the app runs locally or on Streamlit Community
Cloud — Cloud wipes local disk writes on every reboot/redeploy, so a networked DB is required for
Leads/Calendar/Outreach history to survive there at all.
"""

import os
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS posts (
        id SERIAL PRIMARY KEY,
        category TEXT NOT NULL,
        topic TEXT NOT NULL,
        body_text TEXT NOT NULL,
        infographic_path TEXT,
        infographic_type TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TEXT NOT NULL,
        scheduled_for TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS leads (
        id SERIAL PRIMARY KEY,
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
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS outreach_drafts (
        id SERIAL PRIMARY KEY,
        lead_id INTEGER NOT NULL REFERENCES leads(id),
        post_id_ref INTEGER REFERENCES posts(id),
        message_text TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at TEXT NOT NULL
    )
    """,
]


@contextmanager
def get_conn():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and add a Postgres connection "
            "string (a free one from Supabase or Neon works fine)."
        )
    conn = psycopg.connect(database_url, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- posts -------------------------------------------------------------

def create_post(category: str, topic: str, body_text: str, scheduled_for: str | None = None) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO posts (category, topic, body_text, status, created_at, scheduled_for) "
            "VALUES (%s, %s, %s, 'draft', %s, %s) RETURNING id",
            (category, topic, body_text, _now(), scheduled_for),
        ).fetchone()
        return row["id"]


def set_post_infographic(post_id: int, infographic_path: str, infographic_type: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE posts SET infographic_path = %s, infographic_type = %s WHERE id = %s",
            (infographic_path, infographic_type, post_id),
        )


def update_post_status(post_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE posts SET status = %s WHERE id = %s", (status, post_id))


def list_posts(status: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if status:
            return conn.execute(
                "SELECT * FROM posts WHERE status = %s ORDER BY created_at DESC", (status,)
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
    placeholders = ", ".join(["%s"] * len(fields))
    with get_conn() as conn:
        row = conn.execute(
            f"INSERT INTO leads ({columns}) VALUES ({placeholders}) RETURNING id",
            tuple(fields.values()),
        ).fetchone()
        return row["id"]


def update_lead_score(lead_id: int, fit_score: int):
    with get_conn() as conn:
        conn.execute("UPDATE leads SET fit_score = %s WHERE id = %s", (fit_score, lead_id))


def update_lead_status(lead_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE leads SET status = %s WHERE id = %s", (status, lead_id))


def list_leads(order_by: str = "fit_score DESC") -> list[dict]:
    if order_by not in {"fit_score DESC", "fit_score ASC", "imported_at DESC", "imported_at ASC"}:
        raise ValueError(f"Unsupported order_by: {order_by}")
    with get_conn() as conn:
        return conn.execute(f"SELECT * FROM leads ORDER BY {order_by}").fetchall()


# --- outreach drafts -------------------------------------------------------

def create_outreach_draft(lead_id: int, message_text: str, post_id_ref: int | None = None) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO outreach_drafts (lead_id, post_id_ref, message_text, status, created_at) "
            "VALUES (%s, %s, %s, 'draft', %s) RETURNING id",
            (lead_id, post_id_ref, message_text, _now()),
        ).fetchone()
        return row["id"]


def update_outreach_status(draft_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE outreach_drafts SET status = %s WHERE id = %s", (status, draft_id))


def list_outreach_drafts(lead_id: int | None = None) -> list[dict]:
    with get_conn() as conn:
        if lead_id:
            return conn.execute(
                "SELECT * FROM outreach_drafts WHERE lead_id = %s ORDER BY created_at DESC",
                (lead_id,),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM outreach_drafts ORDER BY created_at DESC"
        ).fetchall()
