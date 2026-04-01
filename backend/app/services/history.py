"""
历史任务持久化 + 用户/会话/注册码（SQLite）
"""
from __future__ import annotations

import json
import logging
import sqlite3
import bcrypt
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "history.db"

_CREATE_INSPECTION_SQL = """
CREATE TABLE IF NOT EXISTS inspection_tasks (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at        TEXT    NOT NULL,
    filename          TEXT    NOT NULL,
    confidence        REAL    NOT NULL,
    ab_test           INTEGER NOT NULL DEFAULT 0,
    has_defect        INTEGER NOT NULL DEFAULT 0,
    defect_count      INTEGER NOT NULL DEFAULT 0,
    high_danger_count INTEGER NOT NULL DEFAULT 0,
    total_cost        INTEGER NOT NULL DEFAULT 0,
    inference_time_ms INTEGER NOT NULL DEFAULT 0,
    detections_json   TEXT    NOT NULL DEFAULT '[]'
)
"""

_CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

_CREATE_SESSIONS_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
"""

_CREATE_ADMIN_CODES_SQL = """
CREATE TABLE IF NOT EXISTS admin_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
)
"""

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD_PLAIN = "Admin@123"
SEED_ADMIN_CODE = "ADMIN-INIT-2025"

_CLASS_CN_KEYS = ("坑洼", "横向裂缝", "纵向裂缝", "网状裂缝")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> set:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def init_db() -> None:
    """创建表、迁移列、种子数据（幂等）"""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _get_conn() as conn:
        conn.execute(_CREATE_INSPECTION_SQL)
        conn.execute(_CREATE_USERS_SQL)
        conn.execute(_CREATE_SESSIONS_SQL)
        conn.execute(_CREATE_ADMIN_CODES_SQL)

        cols = _table_columns(conn, "inspection_tasks")
        if "user_id" not in cols:
            conn.execute(
                "ALTER TABLE inspection_tasks ADD COLUMN user_id INTEGER"
            )
        if "task_type" not in cols:
            conn.execute(
                "ALTER TABLE inspection_tasks ADD COLUMN task_type TEXT NOT NULL DEFAULT 'image'"
            )

        conn.commit()

    _seed_users_and_codes()
    _migrate_legacy_tasks_user()

    logger.info("历史与用户数据库初始化完成：%s", _DB_PATH)


def _seed_users_and_codes() -> None:
    now = datetime.now(tz=timezone.utc).isoformat()
    admin_hash = bcrypt.hashpw(
        DEFAULT_ADMIN_PASSWORD_PLAIN.encode("utf-8"),
        bcrypt.gensalt(12),
    ).decode("utf-8")
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?", (DEFAULT_ADMIN_USERNAME,)
        ).fetchone()
        if not row:
            conn.execute(
                """
                INSERT INTO users (username, password_hash, role, created_at)
                VALUES (?, ?, 'admin', ?)
                """,
                (DEFAULT_ADMIN_USERNAME, admin_hash, now),
            )
            logger.info("已创建默认管理员：%s", DEFAULT_ADMIN_USERNAME)

        existing_code = conn.execute(
            "SELECT id FROM admin_codes WHERE code = ?", (SEED_ADMIN_CODE,)
        ).fetchone()
        if not existing_code:
            conn.execute(
                """
                INSERT INTO admin_codes (code, is_active, created_at)
                VALUES (?, 1, ?)
                """,
                (SEED_ADMIN_CODE, now),
            )
            logger.info("已写入默认管理员注册码")
        conn.commit()


def _migrate_legacy_tasks_user() -> None:
    with _get_conn() as conn:
        admin = conn.execute(
            "SELECT id FROM users WHERE username = ?", (DEFAULT_ADMIN_USERNAME,)
        ).fetchone()
        if not admin:
            return
        admin_id = admin[0]
        conn.execute(
            "UPDATE inspection_tasks SET user_id = ? WHERE user_id IS NULL",
            (admin_id,),
        )
        conn.commit()


def insert_user(username: str, password_hash: str, role: str) -> int:
    now = datetime.now(tz=timezone.utc).isoformat()
    with _get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO users (username, password_hash, role, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (username, password_hash, role, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_user_by_username(username: str) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def is_admin_code_valid(code: str) -> bool:
    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM admin_codes
            WHERE code = ? AND is_active = 1
            """,
            (code,),
        ).fetchone()
    return row is not None


def create_session_row(token: str, user_id: int, expires_iso: str) -> None:
    now = datetime.now(tz=timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO sessions (session_token, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, expires_iso, now),
        )
        conn.commit()


def get_valid_session(token: str) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_token = ?", (token,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        exp = datetime.fromisoformat(d["expires_at"].replace("Z", "+00:00"))
        if exp < datetime.now(tz=timezone.utc):
            delete_session(token)
            return None
    except Exception:
        return None
    return d


def update_session_expiry(token: str, expires_iso: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET expires_at = ? WHERE session_token = ?",
            (expires_iso, token),
        )
        conn.commit()


def delete_session(token: str) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE session_token = ?", (token,))
        conn.commit()


def delete_expired_sessions() -> None:
    now = datetime.now(tz=timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        conn.commit()


def _detections_to_json(detections: list) -> str:
    if not detections:
        return "[]"
    if hasattr(detections[0], "dict"):
        return json.dumps([d.dict() for d in detections], ensure_ascii=False)
    return json.dumps(detections, ensure_ascii=False)


def save_task(
    user_id: int,
    filename: str,
    confidence: float,
    ab_test: bool,
    has_defect: bool,
    detections: list,
    inference_time_ms: int,
    task_type: str = "image",
) -> int:
    high_danger_count = sum(
        1 for d in detections
        if (getattr(d, "danger_level", None) or d.get("danger_level")) == "高"
    )
    total = 0
    for d in detections:
        if hasattr(d, "estimated_cost"):
            total += d.estimated_cost
        else:
            total += int(d.get("estimated_cost", 0))
    detections_json = _detections_to_json(detections)
    created_at = datetime.now(tz=timezone.utc).isoformat()

    with _get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO inspection_tasks
              (created_at, filename, confidence, ab_test, has_defect,
               defect_count, high_danger_count, total_cost,
               inference_time_ms, detections_json, user_id, task_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                filename,
                confidence,
                int(ab_test),
                int(has_defect),
                len(detections),
                high_danger_count,
                total,
                inference_time_ms,
                detections_json,
                user_id,
                task_type,
            ),
        )
        conn.commit()
        task_id = cursor.lastrowid
    logger.info("历史任务已保存，id=%d，文件=%s，user_id=%s", task_id, filename, user_id)
    return int(task_id)


def get_tasks(
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[int] = None,
    is_admin: bool = False,
) -> List[dict]:
    with _get_conn() as conn:
        base = """
            SELECT id, created_at, filename, confidence, ab_test,
                   has_defect, defect_count, high_danger_count,
                   total_cost, inference_time_ms, user_id, task_type
            FROM inspection_tasks
        """
        if is_admin:
            rows = conn.execute(
                base + " ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                base + " WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset),
            ).fetchall()
    return [dict(r) for r in rows]


def get_task(task_id: int) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM inspection_tasks WHERE id = ?", (task_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_task(task_id: int) -> bool:
    with _get_conn() as conn:
        cursor = conn.execute(
            "DELETE FROM inspection_tasks WHERE id = ?", (task_id,)
        )
        conn.commit()
    return cursor.rowcount > 0


def get_total_count(user_id: Optional[int] = None, is_admin: bool = False) -> int:
    with _get_conn() as conn:
        if is_admin:
            row = conn.execute("SELECT COUNT(*) FROM inspection_tasks").fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM inspection_tasks WHERE user_id = ?",
                (user_id,),
            ).fetchone()
    return int(row[0])


def get_summary_stats() -> dict:
    try:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS task_count, "
                "COALESCE(SUM(defect_count), 0) AS total_defects "
                "FROM inspection_tasks"
            ).fetchone()
        return {
            "task_count": row["task_count"] or 0,
            "total_defects": row["total_defects"] or 0,
        }
    except Exception:
        logger.warning("get_summary_stats 查询失败，返回零值", exc_info=True)
        return {"task_count": 0, "total_defects": 0}


def _parse_task_created_at(created_at_str: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    except Exception:
        return None


def get_defect_type_counts_for_pie(
    user_id: Optional[int],
    is_admin: bool,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    按缺陷实例数统计四类中文名；可选日期为 YYYY-MM-DD，含端点。
    """
    counts: Dict[str, int] = {k: 0 for k in _CLASS_CN_KEYS}
    with _get_conn() as conn:
        if is_admin:
            rows = conn.execute(
                "SELECT created_at, detections_json FROM inspection_tasks"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT created_at, detections_json FROM inspection_tasks WHERE user_id = ?",
                (user_id,),
            ).fetchall()

    start_d: Optional[datetime] = None
    end_d: Optional[datetime] = None
    if start_date:
        try:
            start_d = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    if end_date:
        try:
            end_d = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        except ValueError:
            pass

    for row in rows:
        ts = _parse_task_created_at(row["created_at"])
        if ts is None:
            continue
        if start_d and ts < start_d:
            continue
        if end_d and ts > end_d:
            continue
        try:
            dets = json.loads(row["detections_json"] or "[]")
        except json.JSONDecodeError:
            continue
        for d in dets:
            cn = d.get("class_cn") if isinstance(d, dict) else None
            if cn in counts:
                counts[cn] += 1

    total = sum(counts.values())
    series = [{"name": k, "value": counts[k]} for k in _CLASS_CN_KEYS]
    return {"counts": counts, "total_detections": total, "series": series}
