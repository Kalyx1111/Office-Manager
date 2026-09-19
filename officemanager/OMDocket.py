"""
OMDocket.py — Office Manager (by Aryan)
The file-docket engine: Serial No / Subject / Pages / Classification /
Marked-to, an 11-level remarks trail, and File In/Hover/Out/Discussion/
Dead status with a full timestamped history.

RBAC rule enforced here (server-side, not just hidden in the UI):
a remark slot can only be written by a user at the matching level, or
by Admin. Everyone who is logged in can read every docket — this is a
transparency tool, not a departmental silo.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from OMCore import (
    get_db, now_iso, new_id, log_audit, STATUSES, REMARK_SLOTS, CLASSIFICATIONS,
)
from OMAuth import get_current_user, require_no_forced_change

router = APIRouter(prefix="/api/dockets", tags=["dockets"])


def slot_required_level(slot: str) -> int:
    if slot in ("remark1", "remark2"):
        return 1
    return int(slot.replace("level", ""))


class DocketCreate(BaseModel):
    serial_no: str = Field(min_length=1, max_length=64)
    subject: str = Field(min_length=1, max_length=300)
    pages: Optional[int] = None
    classification: Optional[str] = None
    marked_to: Optional[str] = None


class RemarkIn(BaseModel):
    text: str = Field(default="", max_length=2000)


class StatusIn(BaseModel):
    status: str


def _docket_out(conn, docket_row) -> dict:
    remarks = {
        r["remark_slot"]: dict(r)
        for r in conn.execute(
            "SELECT * FROM docket_remarks WHERE docket_id = ?", (docket_row["id"],)
        )
    }
    remark_list = []
    for slot in REMARK_SLOTS:
        r = remarks.get(slot)
        filled = bool(r and r["remark_text"])
        remark_list.append({
            "slot": slot,
            "level": slot_required_level(slot),
            "text": r["remark_text"] if r else None,
            "filled": filled,
            "entered_by": r["entered_by"] if r else None,
            "entered_at": r["entered_at"] if r else None,
        })

    history = [
        dict(h) for h in conn.execute(
            "SELECT * FROM docket_status_log WHERE docket_id = ? ORDER BY changed_at ASC",
            (docket_row["id"],),
        )
    ]
    d = dict(docket_row)
    d["remarks"] = remark_list
    d["status_history"] = history
    d["status_since"] = history[-1]["changed_at"] if history else docket_row["initiated_at"]
    return d


@router.get("")
def list_dockets(status: Optional[str] = None, mine: bool = False,
                  user=Depends(get_current_user)):
    with get_db() as conn:
        q = "SELECT * FROM dockets WHERE deleted = 0"
        params = []
        if status:
            q += " AND current_status = ?"
            params.append(status)
        if mine:
            q += " AND initiated_by = ?"
            params.append(user["id"])
        q += " ORDER BY updated_at DESC"
        rows = conn.execute(q, params).fetchall()
        return [_docket_out(conn, r) for r in rows]


@router.post("")
def create_docket(body: DocketCreate, user=Depends(require_no_forced_change)):
    if body.classification and body.classification not in CLASSIFICATIONS:
        raise HTTPException(status_code=400, detail=f"classification must be one of {CLASSIFICATIONS}")
    with get_db() as conn:
        docket_id = new_id()
        ts = now_iso()
        conn.execute(
            "INSERT INTO dockets (id, serial_no, subject, pages, classification, marked_to, "
            "initiated_by, initiated_at, current_status, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (docket_id, body.serial_no, body.subject, body.pages, body.classification,
             body.marked_to, user["id"], ts, "File In", ts),
        )
        conn.execute(
            "INSERT INTO docket_status_log (docket_id, status, changed_by, changed_at) "
            "VALUES (?,?,?,?)",
            (docket_id, "File In", user["id"], ts),
        )
        log_audit(conn, user["id"], "docket_created", target=docket_id, detail=body.serial_no)
        row = conn.execute("SELECT * FROM dockets WHERE id = ?", (docket_id,)).fetchone()
        return _docket_out(conn, row)


@router.get("/{docket_id}")
def get_docket(docket_id: str, user=Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM dockets WHERE id = ? AND deleted = 0", (docket_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Docket not found")
        return _docket_out(conn, row)


@router.put("/{docket_id}/remarks/{slot}")
def set_remark(docket_id: str, slot: str, body: RemarkIn,
                user=Depends(require_no_forced_change)):
    if slot not in REMARK_SLOTS:
        raise HTTPException(status_code=400, detail="Unknown remark slot")
    needed_level = slot_required_level(slot)
    if not user["is_admin"] and user["level"] != needed_level:
        raise HTTPException(
            status_code=403,
            detail=f"Only Level {needed_level} (or Admin) can write this remark box",
        )
    with get_db() as conn:
        docket = conn.execute(
            "SELECT * FROM dockets WHERE id = ? AND deleted = 0", (docket_id,)
        ).fetchone()
        if not docket:
            raise HTTPException(status_code=404, detail="Docket not found")
        ts = now_iso()
        conn.execute(
            "INSERT INTO docket_remarks (docket_id, remark_slot, remark_text, entered_by, entered_at) "
            "VALUES (?,?,?,?,?) "
            "ON CONFLICT(docket_id, remark_slot) DO UPDATE SET "
            "remark_text=excluded.remark_text, entered_by=excluded.entered_by, entered_at=excluded.entered_at",
            (docket_id, slot, body.text, user["id"], ts),
        )
        conn.execute("UPDATE dockets SET updated_at=? WHERE id=?", (ts, docket_id))
        log_audit(conn, user["id"], "remark_set", target=docket_id, detail=slot)
        row = conn.execute("SELECT * FROM dockets WHERE id = ?", (docket_id,)).fetchone()
        return _docket_out(conn, row)


@router.post("/{docket_id}/status")
def set_status(docket_id: str, body: StatusIn, user=Depends(require_no_forced_change)):
    if body.status not in STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {STATUSES}")
    with get_db() as conn:
        docket = conn.execute(
            "SELECT * FROM dockets WHERE id = ? AND deleted = 0", (docket_id,)
        ).fetchone()
        if not docket:
            raise HTTPException(status_code=404, detail="Docket not found")
        ts = now_iso()
        conn.execute("UPDATE dockets SET current_status=?, updated_at=? WHERE id=?",
                      (body.status, ts, docket_id))
        conn.execute(
            "INSERT INTO docket_status_log (docket_id, status, changed_by, changed_at) "
            "VALUES (?,?,?,?)",
            (docket_id, body.status, user["id"], ts),
        )
        log_audit(conn, user["id"], "status_changed", target=docket_id, detail=body.status)
        row = conn.execute("SELECT * FROM dockets WHERE id = ?", (docket_id,)).fetchone()
        return _docket_out(conn, row)


@router.delete("/{docket_id}")
def delete_docket(docket_id: str, user=Depends(get_current_user)):
    with get_db() as conn:
        docket = conn.execute("SELECT * FROM dockets WHERE id = ?", (docket_id,)).fetchone()
        if not docket:
            raise HTTPException(status_code=404, detail="Docket not found")
        is_owner = docket["initiated_by"] == user["id"]
        untouched = docket["current_status"] == "File In" and not any(
            r["remark_text"] for r in conn.execute(
                "SELECT remark_text FROM docket_remarks WHERE docket_id=?", (docket_id,)
            )
        )
        if not (user["is_admin"] or (is_owner and untouched)):
            raise HTTPException(
                status_code=403,
                detail="Only Admin can delete a docket once other levels have acted on it",
            )
        conn.execute("UPDATE dockets SET deleted=1, updated_at=? WHERE id=?", (now_iso(), docket_id))
        log_audit(conn, user["id"], "docket_deleted", target=docket_id)
    return {"ok": True}
