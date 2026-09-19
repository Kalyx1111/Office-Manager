"""
OMCore.py — Office Manager (by Aryan)
Shared config, database access, password hashing, and constants.
No secrets are hardcoded here — see OM_SESSION_SECRET handling below.
"""
import os
import sqlite3
import string
import uuid
import contextlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import bcrypt

# ---------------------------------------------------------------------------
# Paths — everything lives inside the project folder (single-folder portable)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.environ.get("OM_DB_PATH", str(DATA_DIR / "office_manager.db")))

# Cookies: on a plain-HTTP office LAN (no internal TLS cert), the browser
# silently drops cookies marked Secure. Only flip this on once you've put
# HTTPS in front of the server. Set OM_HTTPS=true in the environment then.
COOKIE_SECURE = os.environ.get("OM_HTTPS", "false").lower() == "true"

SESSION_LIFETIME_HOURS = int(os.environ.get("OM_SESSION_HOURS", "12"))

# ---------------------------------------------------------------------------
# Org structure — counts and default role titles (titles are editable later
# from the Admin panel; this is only the seed default).
# ---------------------------------------------------------------------------
LEVEL_COUNTS = {1: 30, 2: 20, 3: 15, 4: 10, 5: 5, 6: 3, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1}

LEVEL_TITLES = {
    1: "Clerk",
    2: "Junior Manager",
    3: "Senior Manager",
    4: "Supervisor",
    5: "Senior Supervisor",
    6: "Senior Supervisor II",
    7: "Boss",
    8: "Level 8",
    9: "Level 9",
    10: "Level 10",
    11: "Level 11",
}

STATUSES = ["File In", "File Hover", "File Out", "File Discussion", "Dead File"]

# Remark slots on a docket, in fixed order: the clerk's own two remark boxes,
# then one box per level from 2 through 11.
REMARK_SLOTS = ["remark1", "remark2"] + [f"level{n}" for n in range(2, 12)]

CLASSIFICATIONS = ["Unclassified", "Restricted", "Confidential", "Secret", "Top Secret"]

EVENT_CATEGORIES = [
    "short_leave", "long_leave", "health", "birthday", "anniversary",
    "transfer", "temporary_duty", "meeting", "task_today", "task_tomorrow",
    "task_week", "task_month", "task_year", "duty", "visit", "invention",
]

# Categories that also feed the 3-day Red/Green/White flag alert bar.
ALERT_EVENT_CATEGORIES = [
    "short_leave", "long_leave", "health", "birthday", "anniversary",
    "transfer", "temporary_duty", "meeting", "duty", "visit",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def new_id() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Desk ID generation: Level<N><Letter>, letters go A..Z then AA..AZ if a
# level ever needs more than 26 (Level 1's 30 desks needs 4 past Z).
# ---------------------------------------------------------------------------
def letter_sequence(count: int):
    letters = string.ascii_uppercase
    out = []
    i = 0
    while len(out) < count:
        if i < 26:
            out.append(letters[i])
        else:
            first = (i // 26) - 1
            second = i % 26
            out.append(letters[first] + letters[second])
        i += 1
    return out


def desk_ids_for_level(level: int, count: int):
    return [f"L{level}{letter}" for letter in letter_sequence(count)]


def initial_password_for(desk_id: str) -> str:
    """Easy, per-account starting password. Forced change on first login."""
    return f"{desk_id.lower()}123"


# ---------------------------------------------------------------------------
# Password hashing (bcrypt — never MD5/SHA alone)
# ---------------------------------------------------------------------------
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# DB connection / schema
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    level INTEGER NOT NULL,
    role_title TEXT NOT NULL,
    display_name TEXT,
    password_hash TEXT NOT NULL,
    must_change_password INTEGER NOT NULL DEFAULT 1,
    is_admin INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dockets (
    id TEXT PRIMARY KEY,
    serial_no TEXT NOT NULL,
    subject TEXT NOT NULL,
    pages INTEGER,
    classification TEXT,
    marked_to TEXT,
    initiated_by TEXT NOT NULL REFERENCES users(id),
    initiated_at TEXT NOT NULL,
    current_status TEXT NOT NULL DEFAULT 'File In',
    updated_at TEXT NOT NULL,
    deleted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS docket_remarks (
    docket_id TEXT NOT NULL REFERENCES dockets(id) ON DELETE CASCADE,
    remark_slot TEXT NOT NULL,
    remark_text TEXT,
    entered_by TEXT REFERENCES users(id),
    entered_at TEXT,
    PRIMARY KEY (docket_id, remark_slot)
);

CREATE TABLE IF NOT EXISTS docket_status_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    docket_id TEXT NOT NULL REFERENCES dockets(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    changed_by TEXT NOT NULL REFERENCES users(id),
    changed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    desk_id TEXT NOT NULL REFERENCES users(id),
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    detail TEXT,
    event_date TEXT NOT NULL,
    recurring_yearly INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id TEXT,
    action TEXT NOT NULL,
    target TEXT,
    detail TEXT,
    at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);
CREATE INDEX IF NOT EXISTS idx_events_desk ON events(desk_id);
CREATE INDEX IF NOT EXISTS idx_dockets_status ON dockets(current_status);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)


def log_audit(conn, actor_id, action, target=None, detail=None):
    conn.execute(
        "INSERT INTO audit_log (actor_id, action, target, detail, at) VALUES (?,?,?,?,?)",
        (actor_id, action, target, detail, now_iso()),
    )
