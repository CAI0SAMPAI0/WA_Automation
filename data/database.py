import sqlite3
import os
from datetime import datetime
from core.paths import get_user_data_dir

DATA_DIR = get_user_data_dir()
DB_PATH = os.path.join(DATA_DIR, "agendamentos.db")

# =========================================================
# INIT / BOOTSTRAP
# =========================================================

def init_db(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL,
            mode TEXT NOT NULL CHECK (mode IN ('text', 'file', 'file_text')),
            message TEXT,
            file_path TEXT,
            scheduled_time TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING'
                CHECK (status IN ('PENDING','RUNNING','COMPLETED','FAILED')),
            executed_at TEXT,
            attempts INTEGER DEFAULT 0,
            last_error TEXT
        )
    """)
    conn.commit()


# =========================================================
# CONEXÃO
# =========================================================

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    return conn


# =========================================================
# CREATE
# =========================================================

def create_task(target, mode, message, file_path, scheduled_time):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO agendamentos (
            target, mode, message, file_path,
            scheduled_time, created_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
    """, (
        target,
        mode,
        message,
        file_path,
        scheduled_time,
        datetime.now().isoformat()
    ))

    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return task_id



# =========================================================
# READ
# =========================================================

def get_task_by_id(task_id):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM agendamentos WHERE id = ?",
        (task_id,)
    )

    row = cur.fetchone()
    conn.close()

    return dict(row) if row else None


def get_pending_tasks(now_iso):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM agendamentos
        WHERE status = 'PENDING'
        AND scheduled_time <= ?
    """, (now_iso,))

    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]


# =========================================================
# UPDATE
# =========================================================

def update_status(task_id, status):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE agendamentos
        SET status = ?
        WHERE id = ?
    """, (status, task_id))

    conn.commit()
    conn.close()


def mark_running(task_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE agendamentos
        SET status = 'RUNNING'
        WHERE id = ?
    """, (task_id,))

    conn.commit()
    conn.close()


def mark_completed(task_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE agendamentos
        SET status = 'COMPLETED',
            executed_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), task_id))

    conn.commit()
    conn.close()


def mark_failed(task_id, error):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE agendamentos
        SET status = 'FAILED',
            executed_at = ?,
            attempts = attempts + 1,
            last_error = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), error, task_id))

    conn.commit()
    conn.close()


def increment_attempts(task_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE agendamentos
        SET attempts = attempts + 1
        WHERE id = ?
    """, (task_id,))

    conn.commit()
    conn.close()


def update_last_error(task_id, error):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE agendamentos
        SET last_error = ?
        WHERE id = ?
    """, (error, task_id))

    conn.commit()
    conn.close()
