"""SQLite helpers for EscrowEase."""
import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("ESCROWEASE_DB", os.path.join(BASE_DIR, "escrowease.db"))
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with open(SCHEMA_PATH) as f:
        schema = f.read()
    conn = get_db()
    conn.executescript(schema)
    conn.commit()
    conn.close()


# ---- deals ----
def create_deal(title, brief, amount, currency, client_email, freelancer_email):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO deals (title, brief, amount, currency, client_email, freelancer_email)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (title, brief, amount, currency, client_email, freelancer_email),
    )
    deal_id = cur.lastrowid
    conn.commit()
    conn.close()
    return deal_id


def get_deal(deal_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
    conn.close()
    return row


def list_deals():
    conn = get_db()
    rows = conn.execute("SELECT * FROM deals ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def update_deal(deal_id, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn = get_db()
    conn.execute(f"UPDATE deals SET {cols} WHERE id = ?", (*fields.values(), deal_id))
    conn.commit()
    conn.close()


# ---- deliverables ----
def add_deliverable(deal_id, description, link):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO deliverables (deal_id, description, link) VALUES (?, ?, ?)",
        (deal_id, description, link or None),
    )
    did = cur.lastrowid
    conn.commit()
    conn.close()
    return did


def latest_deliverable(deal_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM deliverables WHERE deal_id = ? ORDER BY id DESC LIMIT 1",
        (deal_id,),
    ).fetchone()
    conn.close()
    return row


def list_deliverables(deal_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM deliverables WHERE deal_id = ? ORDER BY id DESC", (deal_id,)
    ).fetchall()
    conn.close()
    return rows


# ---- verdicts ----
def add_verdict(deal_id, decision, confidence, reasons, source="pollinations"):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO verdicts (deal_id, decision, confidence, reasons, source) VALUES (?, ?, ?, ?, ?)",
        (deal_id, decision, confidence, json.dumps(reasons), source),
    )
    vid = cur.lastrowid
    conn.commit()
    conn.close()
    return vid


def latest_verdict(deal_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM verdicts WHERE deal_id = ? ORDER BY id DESC LIMIT 1", (deal_id,)
    ).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["reasons"] = json.loads(d["reasons"])
        return d
    return None
