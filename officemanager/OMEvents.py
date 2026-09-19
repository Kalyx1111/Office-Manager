"""
OMEvents.py — Office Manager (by Aryan)
Daily desk updates (leave, health, birthdays, TD, meetings, tasks, duties,
visits, inventions) and the derived views: the 3-day Red/Green/White flag
alert bar, the birthdays-and-anniversaries widget (this month + next 3),
and the motivational quote rotation.

Visibility rule: every logged-in desk can read every event (this is a
shared office board), but only the desk that created an entry — or
Admin — can edit or remove it.
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from OMCore import (
    get_db, now_iso, new_id, log_audit, EVENT_CATEGORIES, ALERT_EVENT_CATEGORIES,
)
from OMAuth import get_current_user, require_no_forced_change

router = APIRouter(prefix="/api/events", tags=["events"])


class EventCreate(BaseModel):
    category: str
    title: str = Field(min_length=1, max_length=200)
    detail: Optional[str] = Field(default=None, max_length=1000)
    event_date: str  # ISO date, e.g. 2026-08-20
    recurring_yearly: bool = False


def next_occurrence(event_date_str: str, recurring: bool, today: Optional[date] = None) -> date:
    d = date.fromisoformat(event_date_str)
    if not recurring:
        return d
    t = today or date.today()
    try:
        candidate = d.replace(year=t.year)
    except ValueError:  # Feb 29 on a non-leap year
        candidate = d.replace(year=t.year, day=28)
    if candidate < t:
        try:
            candidate = d.replace(year=t.year + 1)
        except ValueError:
            candidate = d.replace(year=t.year + 1, day=28)
    return candidate


@router.get("")
def list_events(category: Optional[str] = None, user=Depends(get_current_user)):
    with get_db() as conn:
        q = "SELECT * FROM events WHERE active = 1"
        params = []
        if category:
            q += " AND category = ?"
            params.append(category)
        q += " ORDER BY event_date DESC"
        rows = [dict(r) for r in conn.execute(q, params).fetchall()]
        return rows


@router.post("")
def create_event(body: EventCreate, user=Depends(require_no_forced_change)):
    if body.category not in EVENT_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category must be one of {EVENT_CATEGORIES}")
    try:
        date.fromisoformat(body.event_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="event_date must be YYYY-MM-DD")
    with get_db() as conn:
        eid = new_id()
        conn.execute(
            "INSERT INTO events (id, desk_id, category, title, detail, event_date, "
            "recurring_yearly, created_at, active) VALUES (?,?,?,?,?,?,?,?,1)",
            (eid, user["id"], body.category, body.title, body.detail, body.event_date,
             int(body.recurring_yearly), now_iso()),
        )
        log_audit(conn, user["id"], "event_created", target=eid, detail=body.category)
        row = conn.execute("SELECT * FROM events WHERE id = ?", (eid,)).fetchone()
        return dict(row)


@router.delete("/{event_id}")
def delete_event(event_id: str, user=Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        if not (user["is_admin"] or row["desk_id"] == user["id"]):
            raise HTTPException(status_code=403, detail="You can only remove your own entries")
        conn.execute("UPDATE events SET active = 0 WHERE id = ?", (event_id,))
        log_audit(conn, user["id"], "event_deleted", target=event_id)
    return {"ok": True}


@router.get("/alerts")
def alerts(user=Depends(get_current_user)):
    """Red = today, Green = tomorrow, White = day after tomorrow."""
    today = date.today()
    window = {
        "red": today,
        "green": today + timedelta(days=1),
        "white": today + timedelta(days=2),
    }
    out = {"red": [], "green": [], "white": []}
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM events WHERE active = 1 AND category IN ({})".format(
                ",".join("?" for _ in ALERT_EVENT_CATEGORIES)
            ),
            ALERT_EVENT_CATEGORIES,
        ).fetchall()
        for r in rows:
            occ = next_occurrence(r["event_date"], bool(r["recurring_yearly"]), today)
            for flag, day in window.items():
                if occ == day:
                    out[flag].append({**dict(r), "occurs_on": occ.isoformat()})
    return out


@router.get("/birthdays-anniversaries")
def birthdays_anniversaries(user=Depends(get_current_user)):
    """This month plus the next 3 months, sorted by upcoming date."""
    today = date.today()
    horizon = today + timedelta(days=122)  # ~ this month + next 3
    out = []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM events WHERE active = 1 AND category IN ('birthday','anniversary')"
        ).fetchall()
        for r in rows:
            occ = next_occurrence(r["event_date"], bool(r["recurring_yearly"]), today)
            if today <= occ <= horizon:
                out.append({**dict(r), "occurs_on": occ.isoformat()})
    out.sort(key=lambda x: x["occurs_on"])
    return out


@router.get("/quotes")
def quotes(user=Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute("SELECT id, text FROM quotes WHERE active = 1").fetchall()
        return [dict(r) for r in rows]
