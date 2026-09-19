OFFICE MANAGER — READ ME
By Aryan
============================================================

WHAT THIS IS
------------
A LAN-hosted file-docket and office command board:
- 11 levels + Admin, one account per desk (89 accounts total)
- Serial No / Subject / Pages / Classification / Marked-To docket,
  with Remark 1, Remark 2, and Level 2-11 remark boxes
- File status: File In / File Hover / File Out / File Discussion /
  Dead File, every change timestamped and kept in full history
- Daily desk updates: short/long leave, health, birthday, anniversary,
  transfer, temporary duty, meetings, tasks (today/tomorrow/week/
  month/year), duties, visits, inventions
- Top alert bar: Red = today, Green = tomorrow, White = day after —
  pulled automatically from everyone's entries
- Birthdays & Anniversaries widget: this month + next 3 months
- Flashing motivational-quote ribbon
- Admin panel: reset/set any password, activate/deactivate accounts,
  rename role titles, add/remove quotes, full audit log

Runs entirely on your own network. No internet needed once the
one-time package install is done. No data leaves this PC.


HOW TO START IT (on the PC that will act as the server)
---------------------------------------------------------
1. Copy this whole folder onto the PC that will host it.
2. Double-click OMRun.bat.
   - First run installs a few small Python packages (needs internet
     just this once), then sets up 89 accounts (~20-30 seconds).
   - It opens your browser automatically. If it opens before the
     server is ready, just refresh after a few seconds.
3. Leave that window open. It IS the server — closing it logs
   everyone out and stops the system.
4. Every other desk opens a browser and goes to:
       http://<server PC's IP address>:8000
   The server console prints this address on startup. If other
   desks can't reach it, allow "python.exe" / port 8000 through
   Windows Firewall on the server PC (Windows Firewall -> Allow an
   app -> add python.exe, or add an inbound rule for TCP 8000).

Requires Python 3.10+ on the server PC only. Other desks need
nothing installed — just a browser.


LOGGING IN THE FIRST TIME
---------------------------
Open OM_Login_Credentials.csv (created next to OMRun.bat on first
launch). It lists every ID and starting password, e.g.:

    ID      Starting Password
    L1A     l1a123
    L6C     l6c123
    ADMIN   admin123

Hand each desk their own ID + starting password. Everyone is
forced to set their own new password the first time they log in.
Move or lock away this CSV once logins are distributed — it is
sensitive.

ID scheme: Level<n><letter> — L1A, L1B, ... L1AD (Level 1 has 30
desks, so it runs past Z into AA-AD), L2A...L2T, and so on, matching
the counts you gave: L1=30, L2=20, L3=15, L4=10, L5=5, L6=3,
L7-L11=1 each. Admin's ID is simply ADMIN.

Default role titles are Clerk / Junior Manager / Senior Manager /
Supervisor / Senior Supervisor (L5) / Senior Supervisor II (L6) /
Boss (L7) / "Level 8".."Level 11". Rename any of these from
Admin -> Roster -> Rename — useful for L8-L11 and for fixing the
L5/L6 title overlap from the original spec.


HOW ACCESS WORKS
-----------------
- Every logged-in desk can VIEW every docket and every daily
  update — this is a shared board, not silced by department.
- Only the desk at a given level (or Admin) can WRITE that level's
  remark box on a docket. This is enforced on the server, not just
  hidden in the screen — so it can't be bypassed by editing the page.
- Anyone logged in can change a docket's File In/Hover/Out/
  Discussion/Dead status (with their name and time recorded).
- A desk can delete their own daily-update entries. A docket can
  only be deleted by its initiator (and only before any other
  level has written a remark) or by Admin.
- "Delete" removes it from every view immediately. The row stays in
  the database with a deleted flag, purely so Admin's audit log
  keeps a forensic trail — nobody else can see or restore it from
  the app. If you want true permanent erasure on request, tell me
  and I'll add an Admin "purge" action.
- Only Admin can reset/change a password, or activate/deactivate
  an account. Resetting a password immediately kills that user's
  active session, too.


WHAT'S BEEN TESTED
--------------------
Real server, real HTTP requests, not a mock-up:
- Login, forced first-password-change, logout, session expiry
- Level-gated remark writes (confirmed a Level 1 desk is blocked
  from writing a Level 2 box, and vice versa)
- Docket status changes and full timestamped history
- Daily-update creation and the Red/Green/White alert math,
  including recurring yearly birthdays/anniversaries rolling into
  next year correctly
- Admin: password reset/set (with session kill), role-title edits,
  activate/deactivate, audit log
- Login rate-limiting (6 tries, then a short lockout)
- A SQL-injection-style login attempt (rejected cleanly)
- Data survives a full server restart (SQLite file on disk)
- Restart-after-first-run is fast (seeding is skipped once accounts
  already exist)

Not yet click-tested in an actual browser from this side (this
build environment has no browser) — the HTML/JS has been checked
for syntax errors and every screen calls the same endpoints that
were just verified above, but give the real interface a run-through
on your machine and tell me anything that looks off.

The OMRun.bat double-click flow is written using standard, common
Windows batch patterns, but wasn't run on an actual Windows machine
from here (this build environment is Linux). Test it first on one
PC before rolling out to all 90 desks.


FILES IN THIS FOLDER
----------------------
OMCore.py       - config, database schema, password hashing
OMSeed.py       - creates Admin + all desk accounts (safe to re-run)
OMAuth.py       - login, sessions, forced password change
OMDocket.py     - the file-docket engine
OMEvents.py     - daily updates, alerts, birthdays widget, quotes
OMAdmin.py      - admin-only user/quote/audit endpoints
OMServer.py     - main app; run this (or OMRun.bat) to start
OMFrontend.html - the single-screen interface
OMRequirements.txt
OMRun.bat       - one-click setup + launch
data/office_manager.db - your live data (BACK THIS FILE UP)


BACKING UP
-----------
Everything — every docket, remark, status change, and daily update
— lives in one file: data\office_manager.db. Copy it elsewhere on
a schedule (a nightly scheduled task copying it to a shared drive
is enough). As long as that file is safe, nothing is lost.


IF SOMETHING BREAKS
----------------------
- Server errors are written to data\app.log with a short reference
  code; the same code is what the user sees on screen, so you can
  match a complaint to the exact log line.
- Nothing here relies on outside servers or an internet connection,
  so a break is almost always local: Python missing, the window
  got closed, or the firewall is blocking other desks.
