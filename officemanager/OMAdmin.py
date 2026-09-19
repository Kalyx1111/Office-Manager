"""
OMAdmin.py — Office Manager (by Aryan)
Everything here requires require_admin. Only Admin resets passwords,
activates/deactivates accounts, edits role titles, or reads the audit log.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from OMCore import get_db, now_iso, hash_password, initial_password_for, log_audit
from OMAuth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


class SetPasswordIn(BaseModel):
    new_password: str = Field(min_length=4, max_length=200)
    force_change: bool = True


class RoleTitleIn(BaseModel):
    role_title: str = Field(min_length=1, max_length=100)


class DisplayNameIn(BaseModel):
    display_name: str = Field(default="", max_length=100)


class QuoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class NewUserIn(BaseModel):
    id: str = Field(min_length=1, max_length=32)
    level: int = Field(ge=0, le=11)
    role_title: str = Field(min_length=1, max_length=100)
    display_name: str = Field(default="", max_length=100)


@router.get("/users")
def list_users(admin=Depends(require_admin)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, level, role_title, display_name, must_change_password, "
            "is_admin, active, created_at, updated_at FROM users ORDER BY level, id"
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/users")
def create_user(body: NewUserIn, admin=Depends(require_admin)):
    uid = body.id.strip().upper()
    with get_db() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE id = ?", (uid,)).fetchone()
        if exists:
            raise HTTPException(status_code=409, detail="That ID already exists")
        pw = initial_password_for(uid)
        conn.execute(
            "INSERT INTO users (id, level, role_title, display_name, password_hash, "
            "must_change_password, is_admin, active, created_at, updated_at) "
            "VALUES (?,?,?,?,?,1,0,1,?,?)",
            (uid, body.level, body.role_title, body.display_name, hash_password(pw),
             now_iso(), now_iso()),
        )
        log_audit(conn, admin["id"], "user_created", target=uid)
    return {"id": uid, "starting_password": pw}


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: str, admin=Depends(require_admin)):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        pw = initial_password_for(user_id)
        conn.execute(
            "UPDATE users SET password_hash=?, must_change_password=1, updated_at=? WHERE id=?",
            (hash_password(pw), now_iso(), user_id),
        )
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))  # kill any live sessions
        log_audit(conn, admin["id"], "password_reset", target=user_id)
    return {"id": user_id, "new_password": pw}


@router.post("/users/{user_id}/set-password")
def set_password(user_id: str, body: SetPasswordIn, admin=Depends(require_admin)):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        conn.execute(
            "UPDATE users SET password_hash=?, must_change_password=?, updated_at=? WHERE id=?",
            (hash_password(body.new_password), int(body.force_change), now_iso(), user_id),
        )
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))  # kill any live sessions
        log_audit(conn, admin["id"], "password_set", target=user_id)
    return {"ok": True}


@router.post("/users/{user_id}/deactivate")
def deactivate(user_id: str, admin=Depends(require_admin)):
    with get_db() as conn:
        conn.execute("UPDATE users SET active=0, updated_at=? WHERE id=?", (now_iso(), user_id))
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        log_audit(conn, admin["id"], "user_deactivated", target=user_id)
    return {"ok": True}


@router.post("/users/{user_id}/activate")
def activate(user_id: str, admin=Depends(require_admin)):
    with get_db() as conn:
        conn.execute("UPDATE users SET active=1, updated_at=? WHERE id=?", (now_iso(), user_id))
        log_audit(conn, admin["id"], "user_activated", target=user_id)
    return {"ok": True}


@router.put("/users/{user_id}/role-title")
def set_role_title(user_id: str, body: RoleTitleIn, admin=Depends(require_admin)):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        conn.execute("UPDATE users SET role_title=?, updated_at=? WHERE id=?",
                      (body.role_title, now_iso(), user_id))
        log_audit(conn, admin["id"], "role_title_changed", target=user_id, detail=body.role_title)
    return {"ok": True}


@router.put("/users/{user_id}/display-name")
def set_display_name(user_id: str, body: DisplayNameIn, admin=Depends(require_admin)):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        conn.execute("UPDATE users SET display_name=?, updated_at=? WHERE id=?",
                      (body.display_name, now_iso(), user_id))
        log_audit(conn, admin["id"], "display_name_changed", target=user_id)
    return {"ok": True}


@router.post("/quotes")
def add_quote(body: QuoteIn, admin=Depends(require_admin)):
    with get_db() as conn:
        conn.execute("INSERT INTO quotes (text, active) VALUES (?,1)", (body.text,))
        log_audit(conn, admin["id"], "quote_added")
    return {"ok": True}


@router.delete("/quotes/{quote_id}")
def remove_quote(quote_id: int, admin=Depends(require_admin)):
    with get_db() as conn:
        conn.execute("UPDATE quotes SET active=0 WHERE id=?", (quote_id,))
        log_audit(conn, admin["id"], "quote_removed", target=str(quote_id))
    return {"ok": True}


@router.get("/audit-log")
def audit_log(limit: int = 200, admin=Depends(require_admin)):
    limit = max(1, min(limit, 1000))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
