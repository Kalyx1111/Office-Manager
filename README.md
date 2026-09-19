# Office Manager v1.0

***

#### 🏢 OFFICE MANAGER — LAN-BASED OFFICE WORKFLOW & DOCKET SYSTEM

**Office Manager** is a browser-based office management and docket-tracking system designed for a shared local network.

It allows multiple desks/users to connect to **one central server PC** through their browsers while maintaining role-based access, level-specific docket remarks, status tracking, daily updates, alerts, administration and audit records.

**The system is designed around a simple deployment model:**

```text
                 OFFICE LAN
                     │
        ┌────────────┴────────────┐
        │                         │
     SERVER PC                USER DESKS
   Office Manager              Browser
        │                         │
        └────────────┬────────────┘
                     │
                  SQLite
                  Database
```

One PC runs the Office Manager server.

Other authorized computers simply open the Office Manager address in a browser.

***

#### 🔐 ROLE-BASED ACCESS

Office Manager supports **89 pre-seeded accounts** across multiple levels.

The tested account structure includes:

```text
L1A – L1AD
L2A – L2T
...
L11A
```

Each account has its own login credentials and role/level.

The system supports:

- Individual user accounts
- Session management
- Password changes
- Forced password change
- Password reset by Admin
- Account activation/deactivation
- Role-title management
- Session invalidation after administrative password changes

***

#### 🛡️ LOGIN SECURITY

The login system was tested against a live server using real HTTP requests.

Included security controls:

- Login authentication
- Session handling
- Rate-limited login attempts
- Account lockout after repeated failed attempts
- Forced password change
- Administrative password reset
- Session termination after password reset
- Activate/deactivate user accounts

The tested login protection locks access after **6 unsuccessful login attempts**.

***

#### 📋 DOCKET ENGINE

The central feature of Office Manager is the **Docket Engine**.

Each docket contains **12 level-specific remark boxes**.

The server enforces which level can write to which remark box.

For example:

```text
Level 1 → Level 1 Remark Box
Level 2 → Level 2 Remark Box
Level 3 → Level 3 Remark Box
...
Level 12 → Level 12 Remark Box
```

A user cannot simply change the browser interface to gain permission to write into another level's remark field because the restriction is enforced by the server.

This was specifically tested:

```text
L1 → L1 box     ✅ Allowed
L1 → L2 box     ❌ Blocked

L2 → L2 box     ✅ Allowed
L2 → L1 box     ❌ Blocked
```

Blank remark boxes are rendered as **solid black**, according to the specified interface requirement.

***

#### 📊 STATUS TRACKING

Office Manager provides a five-status workflow:

| Status | Purpose |
|---|---|
| **In** | Matter/person currently active |
| **Hover** | Temporarily being monitored/held |
| **Out** | Moved outside the current workflow |
| **Discussion** | Under discussion |
| **Dead** | No longer active |

The system maintains status history and provides a live **Time in Status** indication.

This allows users to see not only the current status but also how long an item has remained there.

***

#### 📝 DAILY UPDATES

Office Manager includes the daily-update categories specified for the system.

The dashboard provides a centralized location for monitoring current office activity and updates.

The objective is to keep important daily information visible from one common system rather than relying on disconnected manual records.

***

#### 🚦 THREE-DAY ALERT SYSTEM

The dashboard includes a three-day alert bar using three visual categories:

```text
🟥 RED
🟩 GREEN
⬜ WHITE
```

The system also handles recurring dates correctly.

Birthdays and anniversaries are calculated as recurring annual events, meaning dates automatically roll forward into the next year rather than becoming permanently outdated.

***

#### 🎂 BIRTHDAYS & ANNIVERSARIES

The dashboard includes a dedicated **Birthdays & Anniversaries** widget.

It displays:

- Current month's events
- The following three months
- Recurring annual dates

This provides a quick overview of upcoming personnel/family occasions.

***

#### 🛠️ ADMINISTRATION PANEL

Administrators have centralized control over user accounts and system administration.

Admin capabilities include:

- Reset user password
- Set a new user password
- Activate account
- Deactivate account
- Rename role titles
- Review audit information
- Manage user access

When an administrator changes a user's password, the user's existing session is terminated.

***

#### 🧾 AUDIT LOG

Administrative activity is recorded through an audit-log mechanism.

This provides a record of important administrative actions rather than leaving account changes completely invisible.

The audit system is intended to support accountability and troubleshooting within the office environment.

***

#### 💾 SQLITE DATABASE

Office Manager uses a **single SQLite database** for persistent application data.

The database stores the system's operational information so that data survives a complete server restart.

```text
Office Manager
      │
      ↓
SQLite Database
      │
      ├── Users
      ├── Sessions
      ├── Dockets
      ├── Remarks
      ├── Status History
      ├── Alerts
      ├── Events
      └── Audit Records
```

One SQLite file therefore provides a straightforward backup point for the application data.

***

#### 🔄 DATA PERSISTENCE

A complete server restart was performed during testing.

Result:

**Data survived the restart successfully.**

This makes the SQLite database the primary backup and recovery asset for the deployment.

For operational use, regular copies of the database should be included in the organization's backup procedure.

***

#### 🖥️ DEPLOYMENT MODEL

Office Manager is designed for a **single-server / multiple-browser** deployment.

Only one PC needs to run the application server.

Every authorized desk connects through a browser.

```text
                 SERVER PC
             Office Manager
                    │
          ┌─────────┼─────────┐
          │         │         │
        Desk 1    Desk 2    Desk 3
        Browser   Browser   Browser
          │         │         │
          └─────────┼─────────┘
                    │
                 LAN/Wi-Fi
```

The same build can therefore be used whether the organization has:

- One workstation
- Several desks
- Dozens of desks
- Up to the tested 89-account environment

The main difference is simply the server address used by each browser.

***

#### 🚀 STARTING THE SYSTEM

The primary Windows launcher is:

```text
OMRun.bat
```

Run this on the designated **server PC** first.

After the server starts, users connect through their browser using the local network address provided by the application.

***

#### 🔑 INITIAL LOGIN

The system automatically creates:

```text
OM_Login_Credentials.csv
```

next to:

```text
OMRun.bat
```

on the first launch.

The file contains:

- Account IDs
- Starting passwords

The credentials file should be securely distributed to the appropriate users and then secured or deleted according to the organization's password-handling policy.

***

#### 👤 ADMIN ACCOUNT

The initial administrative account is:

```text
ADMIN
```

The recommended first deployment sequence is:

```text
1. Run OMRun.bat
2. Login as ADMIN
3. Verify the dashboard
4. Test one Level 1 account
5. Test one Level 2 account
6. Verify their respective remark permissions
7. Verify the alert bar
8. Confirm status tracking
9. Confirm data persistence
10. Only then distribute production credentials
```

***

#### 🧪 TESTING & VERIFICATION

The system was tested against a **live server using real HTTP requests**, rather than being evaluated only as a static code mock-up.

The following areas were tested:

| Feature | Result |
|---|---|
| Login | ✅ Tested |
| Forced password change | ✅ Tested |
| Sessions | ✅ Tested |
| Rate-limited login | ✅ Tested |
| Six-attempt lockout | ✅ Tested |
| 89 accounts | ✅ Auto-seeded |
| Docket engine | ✅ Tested |
| Level-specific permissions | ✅ Server-enforced |
| Blank remark appearance | ✅ Tested |
| Five-status history | ✅ Tested |
| Time in status | ✅ Tested |
| Daily-update categories | ✅ Tested |
| Three-day alerts | ✅ Tested |
| Recurring birthdays | ✅ Tested |
| Recurring anniversaries | ✅ Tested |
| Birthday/Anniversary widget | ✅ Tested |
| Admin password management | ✅ Tested |
| Account activation/deactivation | ✅ Tested |
| Role-title changes | ✅ Tested |
| Audit logging | ✅ Tested |
| SQLite persistence | ✅ Tested |
| Server restart persistence | ✅ Tested |

***

#### ⚠️ CURRENT TESTING LIMITATIONS

The underlying server/API was extensively tested, but two deployment-specific areas still require testing on an actual Windows office machine.

##### Browser Interface

The build environment did not provide a normal graphical browser for full click-by-click interface testing.

Therefore:

**API/server functionality was extensively tested, but the complete production browser workflow should still be smoke-tested on the deployment PC.**

##### Windows Launcher

`OMRun.bat` uses standard Windows batch syntax, but it was not executed on a physical Windows machine during the build verification.

Before organization-wide deployment:

```text
Run OMRun.bat
        ↓
Confirm server starts
        ↓
Open browser
        ↓
Login as ADMIN
        ↓
Test L1
        ↓
Test L2
        ↓
Verify permissions
```

***

#### 🏷️ ROLE TITLES

The system supports administrator-controlled role-title changes.

At the current v1.0 stage:

```text
L8
L9
L10
L11
```

still use placeholder titles such as:

```text
Level 8
Level 9
Level 10
Level 11
```

These can be renamed through the Admin/Roster functionality.

***

#### 📂 PROJECT DOCUMENTATION

The deployment package includes:

```text
OM_READ_ME.txt
```

This contains the detailed setup, firewall and backup instructions.

It should be reviewed before deploying Office Manager across the LAN.

***

#### 🔥 FIREWALL & LAN DEPLOYMENT

Because one PC acts as the central server, the Windows firewall and local network configuration must permit authorized computers to reach the Office Manager service.

Only the required application port should be exposed on the trusted LAN.

The system should **not** be unnecessarily exposed directly to the public Internet.

For operational deployment, network access should be limited according to the organization's IT/security policy.

***

#### 💾 BACKUP RECOMMENDATION

The SQLite database represents the core persistent data store.

A practical backup approach is:

```text
Office Manager
      ↓
SQLite Database
      ↓
Scheduled Backup
      ↓
Separate Backup Location
```

Backups should be performed regularly and tested by restoring a copy rather than assuming that a backup is usable.

The generated login-credentials file should be handled separately and securely.

***

#### 🔮 FUTURE EXPANSION

Office Manager is designed so that the current LAN architecture can be expanded without replacing the core database/backend.

##### WebSocket-Based Live Updates

The current dashboard uses periodic polling.

A future version can replace the approximately **20-second dashboard polling cycle** with WebSockets.

Current:

```text
Browser
   ↓
Poll
   ↓
Server
   ↓
Response
```

Possible future architecture:

```text
Browser
   ↕
WebSocket
   ↕
Server
   ↕
Database
```

This would allow near-instant updates between desks while retaining the same underlying backend architecture.

***

#### 🚀 POSSIBLE FUTURE FEATURES

Potential future additions include:

- WebSocket real-time updates
- Advanced dashboard analytics
- Printable docket reports
- PDF export
- Excel/CSV reporting
- Advanced search
- Docket filtering
- User activity reports
- Expanded audit reports
- Backup/restore interface
- Automated database backups
- Role-based dashboard customization
- Notification system
- Configurable alert periods
- Additional administrative controls
- LAN-wide real-time status synchronization

These are **future expansion possibilities and are not claims of current v1.0 functionality**.

***

#### 🏗️ DESIGN PHILOSOPHY

Office Manager is built around five principles:

**1. Centralized**

One server provides one common operational database.

**2. Role-Based**

Users receive access according to their assigned level.

**3. Server-Enforced**

Important permissions are enforced by the backend rather than relying only on interface controls.

**4. Persistent**

Operational data survives a complete server restart.

**5. Expandable**

The architecture leaves room for real-time synchronization and additional office-management features.

***

#### 📌 VERSION

**Project:** Office Manager  
**Version:** v1.0  
**Architecture:** Local Server + Browser Clients  
**Database:** SQLite  
**Deployment:** LAN  
**Accounts:** 89 pre-seeded accounts  
**Primary Launcher:** `OMRun.bat`

***

#### ⚠️ IMPORTANT DEPLOYMENT NOTE

Office Manager should be treated as an **internal office/LAN application**.

Before production deployment, administrators should:

- Change/default-secure administrative credentials
- Secure the generated credentials file
- Test the application on the actual Windows server PC
- Test the browser interface from representative client PCs
- Configure the Windows firewall appropriately
- Establish a regular SQLite backup procedure
- Confirm user permissions
- Rename placeholder role titles
- Test recovery from a database backup

***

#### 👤 OFFICE MANAGER — BY ARYAN

A centralized browser-based office workflow system designed to bring **docket management, role-based remarks, status tracking, alerts, personnel occasions, administration and auditability** into one local platform.

***
