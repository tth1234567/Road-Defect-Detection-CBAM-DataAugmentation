"""
用户认证与会话（Cookie + SQLite）
"""
from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, TypedDict

import bcrypt

from app.services import history as history_svc

logger = logging.getLogger(__name__)

ROLE_INSPECTOR = "inspector"
ROLE_ADMIN = "admin"
ROLE_CHOICES = (ROLE_INSPECTOR, ROLE_ADMIN)

SESSION_DAYS = 7
SESSION_COOKIE_NAME = "session_id"
BCRYPT_ROUNDS = 12

_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
)


def validate_password_strength(password: str) -> Optional[str]:
    if not password:
        return "密码不能为空"
    if len(password) < 8:
        return "密码至少 8 位"
    if not _PASSWORD_PATTERN.match(password):
        return "密码须同时包含大写字母、小写字母、数字和特殊字符"
    return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(BCRYPT_ROUNDS)
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except Exception:
        return False


class CurrentUser(TypedDict):
    id: int
    username: str
    role: str


def register_user(
    username: str,
    password: str,
    role: str,
    admin_code: Optional[str],
) -> tuple[Optional[int], Optional[str]]:
    username = (username or "").strip()
    if not username:
        return None, "用户名不能为空"
    if role not in ROLE_CHOICES:
        return None, "无效的角色"
    err = validate_password_strength(password)
    if err:
        return None, err
    if role == ROLE_ADMIN:
        if not admin_code or not admin_code.strip():
            return None, "注册管理员需要填写注册码"
        if not history_svc.is_admin_code_valid(admin_code.strip()):
            return None, "管理员注册码无效"
    existing = history_svc.get_user_by_username(username)
    if existing:
        return None, "用户名已存在"
    pwd_hash = hash_password(password)
    try:
        uid = history_svc.insert_user(username, pwd_hash, role)
    except Exception:
        logger.exception("insert_user failed")
        return None, "注册失败，请稍后重试"
    return uid, None


def login_user(
    username: str, password: str
) -> tuple[Optional[str], Optional[str], Optional[CurrentUser]]:
    username = (username or "").strip()
    if not username or not password:
        return None, "用户名或密码不能为空", None
    row = history_svc.get_user_by_username(username)
    if not row or not verify_password(password, row["password_hash"]):
        return None, "用户名或密码错误", None
    history_svc.delete_expired_sessions()
    token = secrets.token_urlsafe(32)
    expires = datetime.now(tz=timezone.utc) + timedelta(days=SESSION_DAYS)
    history_svc.create_session_row(token, row["id"], expires.isoformat())
    user: CurrentUser = {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
    }
    return token, None, user


def logout_user(session_token: Optional[str]) -> None:
    if session_token:
        history_svc.delete_session(session_token)


def resolve_session_user(session_token: Optional[str]) -> Optional[CurrentUser]:
    if not session_token:
        return None
    history_svc.delete_expired_sessions()
    sess = history_svc.get_valid_session(session_token)
    if not sess:
        return None
    user = history_svc.get_user_by_id(sess["user_id"])
    if not user:
        return None
    new_exp = datetime.now(tz=timezone.utc) + timedelta(days=SESSION_DAYS)
    history_svc.update_session_expiry(session_token, new_exp.isoformat())
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
    }
