"""
OMAuth.py — Office Manager (by Aryan)
Login, forced first-change password flow, session cookies, RBAC dependencies.

Zero-trust notes:
- Sessions are opaque server-issued tokens stored in the DB (revocable),
  not self-contained JWTs.
- Access-level checks happen here, in server code, on every request —
  never inferred from what the frontend chooses to show or hide.
- Login is rate-limited per (id, source IP) to slow down password guessing.
"""
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from OMCore import (
    get_db, now_iso, new_id, hash_password, verify_password,
    SESSION_LIFETIME_HOURS, COOKIE_SECURE, log_audit,
)
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/api", tags=["auth"])

COOKIE_NAME = "om_session"

# ---- simple in-memory login rate limiter -----------------------------
_attempts = defaultdict(deque)
MAX_ATTEMPTS = 6
WINDOW_SECONDS = 300


def _rate_limited(key: str) -> bool:
    dq = _attempts[key]
    now = time.time()
    while dq and now - dq[0] > WINDOW_SECONDS:
        dq.popleft()
    return len(dq) >= MAX_ATTEMPTS


def _record_attempt(key: str):
    _attempts[key].append(time.time())


# ---- request/response models ------------------------------------------
class LoginIn(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=6, max_length=200)


# ---- session helpers -----------------------------------------------------
def create_session(conn, user_id: str) -> str:
    token = new_id() + new_id()
    expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_LIFETIME_HOURS)).isoformat()
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
        (token, user_id, now_iso(), expires),
    )
    return token


def set_session_cookie(response: Response, token: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=SESSION_LIFETIME_HOURS * 3600,
        path="/",
    )


def get_current_user(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    with get_db() as conn:
        row = conn.execute(
            "SELECT s.token, s.expires_at, u.* FROM sessions s "
            "JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Session expired, please log in again")
        if row["expires_at"] < now_iso():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            raise HTTPException(status_code=401, detail="Session expired, please log in again")
        if not row["active"]:
            raise HTTPException(status_code=403, detail="Account disabled — see Admin")
        return dict(row)


def require_admin(user=Depends(get_current_user)):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_no_forced_change(user=Depends(get_current_user)):
    if user["must_change_password"]:
        raise HTTPException(status_code=428, detail="Password change required before continuing")
    return user


# ---- routes ---------------------------------------------------------------
@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    key = f"{body.id.upper()}|{request.client.host if request.client else 'unknown'}"
    if _rate_limited(key):
        raise HTTPException(status_code=429, detail="Too many attempts — wait a few minutes")

    uid = body.id.strip().upper()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if not row or not row["active"] or not verify_password(body.password, row["password_hash"]):
            _record_attempt(key)
            log_audit(conn, uid, "login_failed")
            raise HTTPException(status_code=401, detail="Incorrect ID or password")

        token = create_session(conn, row["id"])
        log_audit(conn, row["id"], "login_success")
        set_session_cookie(response, token)
        return {
            "id": row["id"],
            "level": row["level"],
            "role_title": row["role_title"],
            "display_name": row["display_name"],
            "is_admin": bool(row["is_admin"]),
            "must_change_password": bool(row["must_change_password"]),
        }


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        with get_db() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return {
        "id": user["id"],
        "level": user["level"],
        "role_title": user["role_title"],
        "display_name": user["display_name"],
        "is_admin": bool(user["is_admin"]),
        "must_change_password": bool(user["must_change_password"]),
    }


@router.post("/change-password")
def change_password(body: ChangePasswordIn, user=Depends(get_current_user)):
    if body.old_password == body.new_password:
        raise HTTPException(status_code=400, detail="New password must differ from the old one")
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        if not verify_password(body.old_password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        conn.execute(
            "UPDATE users SET password_hash=?, must_change_password=0, updated_at=? WHERE id=?",
            (hash_password(body.new_password), now_iso(), user["id"]),
        )
        log_audit(conn, user["id"], "password_changed", target=user["id"])
    return {"ok": True}
