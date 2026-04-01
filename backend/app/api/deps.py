"""
依赖注入：当前登录用户
"""
from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.services.auth import SESSION_COOKIE_NAME, CurrentUser, resolve_session_user


def require_user(request: Request) -> CurrentUser:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = resolve_session_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或会话已过期，请重新登录",
        )
    return user
