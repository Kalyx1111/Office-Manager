"""
OMSeed.py — Office Manager (by Aryan)
Run once to create the database and seed every desk account.
Safe to re-run: skips any ID that already exists.

Usage: python OMSeed.py
Writes OM_Login_Credentials.csv with every ID + starting password —
hand these out, then each person changes their password on first login.
"""
import csv
from OMCore import (
    init_db, get_db, now_iso, hash_password, initial_password_for,
    desk_ids_for_level, LEVEL_COUNTS, LEVEL_TITLES, BASE_DIR,
)

ADMIN_ID = "ADMIN"


def seed():
    init_db()
    created = []

    with get_db() as conn:
        existing = {r["id"] for r in conn.execute("SELECT id FROM users")}

        # Admin account
        if ADMIN_ID not in existing:
            pw = initial_password_for(ADMIN_ID)
            conn.execute(
                "INSERT INTO users (id, level, role_title, display_name, password_hash, "
                "must_change_password, is_admin, active, created_at, updated_at) "
                "VALUES (?,0,?,?,?,1,1,1,?,?)",
                (ADMIN_ID, "Administrator", "Administrator", hash_password(pw), now_iso(), now_iso()),
            )
            created.append((ADMIN_ID, "Administrator", pw))

        # Desk accounts, level by level
        for level, count in LEVEL_COUNTS.items():
            title = LEVEL_TITLES.get(level, f"Level {level}")
            for desk_id in desk_ids_for_level(level, count):
                if desk_id in existing:
                    continue
                pw = initial_password_for(desk_id)
                conn.execute(
                    "INSERT INTO users (id, level, role_title, display_name, password_hash, "
                    "must_change_password, is_admin, active, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,1,0,1,?,?)",
                    (desk_id, level, title, "", hash_password(pw), now_iso(), now_iso()),
                )
                created.append((desk_id, title, pw))

        # A handful of starter quotes for the flashing banner
        quote_count = conn.execute("SELECT COUNT(*) c FROM quotes").fetchone()["c"]
        if quote_count == 0:
            starter_quotes = [
                "Discipline in small files builds trust in big decisions.",
                "A file delayed is a decision denied.",
                "Every stamp on this docket is someone's word on the record.",
                "Clarity today saves an escalation tomorrow.",
                "The desk that updates on time is the desk that is trusted.",
            ]
            for q in starter_quotes:
                conn.execute("INSERT INTO quotes (text, active) VALUES (?,1)", (q,))

    if created:
        out_path = BASE_DIR / "OM_Login_Credentials.csv"
        with open(out_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ID", "Role", "Starting Password", "Note"])
            for desk_id, title, pw in created:
                w.writerow([desk_id, title, pw, "Must be changed on first login"])
        print(f"Created {len(created)} accounts. Credentials written to {out_path}")
    else:
        print("All accounts already exist — nothing new to seed.")


if __name__ == "__main__":
    seed()
