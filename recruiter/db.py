import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import paths

DB_PATH = paths.db_path()

SCHEMA = """
CREATE TABLE IF NOT EXISTS lobbies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recruits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    profile_url TEXT,
    group_tier TEXT,
    status TEXT,
    substatus TEXT,
    lobby_id INTEGER,
    scraped_at TEXT NOT NULL,
    sent_at TEXT,
    send_result TEXT,
    send_error TEXT,
    selected INTEGER DEFAULT 1,
    FOREIGN KEY(lobby_id) REFERENCES lobbies(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_recruits_username ON recruits(username);
CREATE INDEX IF NOT EXISTS idx_recruits_group ON recruits(group_tier);
CREATE INDEX IF NOT EXISTS idx_recruits_status ON recruits(status);
CREATE INDEX IF NOT EXISTS idx_recruits_sent ON recruits(sent_at);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    body TEXT NOT NULL,
    is_active INTEGER DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init() -> None:
    # paths.data_dir() already ensures the directory exists.
    paths.data_dir()
    with connect() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------- lobbies ----------

def add_lobby(name: str, url: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO lobbies (name, url, added_at) VALUES (?, ?, ?)",
            (name, url, now_iso()),
        )
        if cur.lastrowid:
            return cur.lastrowid
        row = conn.execute("SELECT id FROM lobbies WHERE url = ?", (url,)).fetchone()
        return row["id"]


def list_lobbies() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute("SELECT * FROM lobbies ORDER BY added_at DESC").fetchall()


def get_lobby(lobby_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM lobbies WHERE id = ?", (lobby_id,)).fetchone()


def delete_lobby(lobby_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM lobbies WHERE id = ?", (lobby_id,))


# ---------- recruits ----------

def upsert_recruit(
    username: str,
    profile_url: str | None,
    group_tier: str | None,
    status: str | None,
    substatus: str | None,
    lobby_id: int | None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO recruits (username, profile_url, group_tier, status, substatus, lobby_id, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                profile_url = excluded.profile_url,
                group_tier = excluded.group_tier,
                status = excluded.status,
                substatus = excluded.substatus,
                lobby_id = excluded.lobby_id,
                scraped_at = excluded.scraped_at
            """,
            (username, profile_url, group_tier, status, substatus, lobby_id, now_iso()),
        )


def list_recruits(
    groups: list[str] | None = None,
    only_online: bool = False,
    exclude_substatus: list[str] | None = None,
    only_unsent: bool = True,
    search: str | None = None,
) -> list[sqlite3.Row]:
    q = "SELECT r.*, l.name AS lobby_name FROM recruits r LEFT JOIN lobbies l ON l.id = r.lobby_id WHERE 1=1"
    params: list = []
    if groups:
        placeholders = ",".join("?" for _ in groups)
        q += f" AND r.group_tier IN ({placeholders})"
        params.extend(groups)
    if only_online:
        q += " AND r.status IN ('online', 'playing', 'do_not_disturb')"
    if exclude_substatus:
        for sub in exclude_substatus:
            q += " AND (r.substatus IS NULL OR r.substatus != ?)"
            params.append(sub)
    if only_unsent:
        q += " AND r.sent_at IS NULL"
    if search:
        q += " AND r.username LIKE ?"
        params.append(f"%{search}%")
    q += " ORDER BY r.group_tier, r.username"
    with connect() as conn:
        return conn.execute(q, params).fetchall()


def get_recruit(recruit_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM recruits WHERE id = ?", (recruit_id,)).fetchone()


def set_recruit_selected(recruit_id: int, selected: bool) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE recruits SET selected = ? WHERE id = ?",
            (1 if selected else 0, recruit_id),
        )


def delete_recruit(recruit_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM recruits WHERE id = ?", (recruit_id,))


def mark_sent(recruit_id: int, result: str, error: str | None = None) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE recruits SET sent_at = ?, send_result = ?, send_error = ? WHERE id = ?",
            (now_iso(), result, error, recruit_id),
        )


# ---------- templates ----------

def save_template(name: str, body: str, make_active: bool = True) -> int:
    with connect() as conn:
        if make_active:
            conn.execute("UPDATE templates SET is_active = 0")
        cur = conn.execute(
            "INSERT INTO templates (name, body, is_active, updated_at) VALUES (?, ?, ?, ?)",
            (name, body, 1 if make_active else 0, now_iso()),
        )
        return cur.lastrowid


def get_active_template() -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM templates WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()


def list_templates() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute("SELECT * FROM templates ORDER BY is_active DESC, name").fetchall()


def get_template(template_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()


def delete_template(template_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))


def set_active_template(template_id: int) -> None:
    with connect() as conn:
        conn.execute("UPDATE templates SET is_active = 0")
        conn.execute("UPDATE templates SET is_active = 1 WHERE id = ?", (template_id,))


# ---------- settings ----------

def get_setting(key: str, default: str | None = None) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
