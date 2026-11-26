# Automated Employee Attendance & Workforce Management System

## Project overview

A web-based employee attendance and workforce management application built with **FastAPI, PostgreSQL, SQLAlchemy and APScheduler**. It centralizes attendance tracking, shifts, leave, work-from-home requests, overtime, automated notifications and administrative reporting in a role-based web interface.

## Table of contents

- [Features](#features)
- [User roles](#user-roles)
- [Technology stack](#technology-stack)
- [System architecture](#system-architecture)
- [Overtime and email workflows](#overtime-and-email-workflows)
- [Installation and setup](#installation-and-setup)
- [Email configuration](#email-configuration)
- [First-time configuration](#first-time-configuration)
- [Background automation](#background-automation)
- [Attendance finalization](#attendance-finalization)
- [API documentation](#api-documentation)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Security and deployment](#security-and-deployment)
- [Validation and known limitations](#validation-and-known-limitations)

## Features

### Authentication and access control

- JWT-based authentication and role-based authorization.
- Super Admin, Manager and Employee accounts.
- Password changes, administrative password resets and account activation/deactivation.
- Protected API endpoints and role-specific frontend views.

### Employee management

- Create, view and update employee profiles, employee codes, email addresses, departments and job titles.
- Assign employees to managers and shifts; maintain reporting relationships.
- Manage account status, joining dates and employee records.
- Administrative attendance corrections and audit history.

### Attendance management

- Employee check-in and check-out with multiple working sessions per day.
- Track worked minutes, required working hours, late arrivals and overtime.
- Support office and WFH attendance modes.
- Personal attendance history and manager team attendance views.
- Identify missing check-outs, incomplete attendance and attendance conflicts.
- Apply company-defined attendance thresholds when calculating daily results.

### Shift and holiday management

- Configure shift start/end times, required working duration and overnight shifts.
- Assign employees to shifts and calculate attendance relative to their schedules.
- Maintain holidays and company working-day policies.
- Finalize employee-days according to their individual shift completion times.

### Leave management

- Submit, edit and withdraw leave requests, including half-day leave.
- Manager approval/rejection and configurable automatic approval policies.
- Cancellation of approved leave through the applicable workflow.
- Track leave balances and administrative allocations.
- Monthly paid-leave accrual with annual caps and an accrual/carry-forward ledger.
- Detect conflicts between attendance and approved leave.

### Work-from-home management

- Submit WFH requests and view request status.
- Enforce configured notice periods, monthly limits and overlapping-request checks.
- Manager approval/rejection or policy-based auto-approval.
- Track WFH usage and distinguish WFH attendance from office attendance.

### Overtime and forgotten check-out management

- Detect when an employee completes the required working duration while a session remains open.
- Ask the employee to confirm overtime or check out.
- Send configurable follow-up reminders when the employee does not respond.
- Keep attendance open when overtime is confirmed and issue periodic overtime reminders.
- Provisionally close unattended sessions after the configured reminder cycle.
- Notify the employee, assigned manager and Super Admin as applicable.
- Allow Super Admin review and correction of automatically closed attendance.

### In-app notifications

- Attendance, overtime, leave and WFH event notifications.
- Action-required notifications for relevant attendance workflows.
- Individual and bulk mark-as-read operations.
- Resolve obsolete attendance actions when the associated session ends.

### Automated email notifications

- Send enabled notification categories to registered email addresses using SMTP.
- Configure a global email switch and individual notification categories from Email Management.
- Store outgoing messages in a database-backed email outbox.
- Process queued emails through a background job instead of sending directly inside attendance requests.
- Track pending, sent, failed and cancelled messages, delivery attempts and timestamps.
- Retry transient delivery failures and allow Super Admin to requeue failed messages.
- Revalidate live overtime reminders before sending to avoid sending obsolete reminders after checkout or state changes.
- Send a test email to the signed-in Super Admin to validate SMTP configuration.

### Dashboards and analytics

| Employee dashboard | Manager dashboard | Super Admin dashboard |
|---|---|---|
| Personal attendance and working hours | Team attendance and current work status | Company-wide attendance and headcount |
| Monthly summary and trends | Shift-wise team breakdown | Department and shift breakdowns |
| Attendance calendar and recent days | Late arrivals and overtime | Monthly comparisons and trends |
| Leave balances and WFH usage | Pending requests and conflicts | Pending approvals and auto-closure reviews |
| Upcoming requests and holidays | Upcoming team leave | Attendance rate, punctuality, worked/required hours and overtime |

Dashboard figures are calculated from attendance records and configured working-day policies. Metric denominators, incomplete records and future-date handling require validation before using these reports for payroll or formal HR reporting.

### Administration and automation

- Company settings, shifts, holidays and employee administration.
- Leave allocations, attendance corrections and audit logs.
- Configurable overtime reminder intervals and maximum reminder count.
- Review automatically closed attendance and manage email delivery.
- Manual execution of supported attendance, leave-accrual and overtime jobs.

## User roles

| Role | Responsibilities |
|---|---|
| `SUPER_ADMIN` | Company configuration, employee management, shifts, holidays, attendance corrections, leave allocations, company analytics, automation, overtime review and email management |
| `MANAGER` | Team attendance monitoring, leave/WFH decisions, attendance conflict resolution and team analytics |
| `EMPLOYEE` | Check-in/out, personal attendance, overtime confirmation, leave/WFH requests, balances, notifications and personal dashboard |

## Technology stack

| Technology | Purpose |
|---|---|
| Python | Backend implementation |
| FastAPI / Uvicorn | REST API and ASGI application server |
| SQLAlchemy | ORM and database sessions |
| PostgreSQL | Persistent application data |
| Alembic | Database schema migrations |
| APScheduler | Background and scheduled jobs |
| JWT / python-jose | Authentication tokens |
| Passlib / bcrypt | Password hashing |
| SMTP / Python smtplib | Email delivery |
| HTML, CSS, JavaScript | Built-in single-page web frontend |
| python-dotenv | Environment configuration |
| pytest / HTTPX | Automated API testing |
| Git / GitHub | Source control |

## System architecture

```mermaid
flowchart TD
    U[Employee / Manager / Super Admin] --> UI[Web frontend]
    UI --> API[FastAPI routers and authentication]
    API --> S[Attendance and business services]
    S --> DB[(PostgreSQL)]
    J[APScheduler] --> S
    S --> N[Notification service]
    N --> DB
    N --> O[Email outbox in PostgreSQL]
    J --> E[Email delivery service]
    O --> E
    E --> SMTP[SMTP server]
    SMTP --> R[Registered recipient email]
```

The frontend is served by FastAPI at `/app/`. API routers enforce access rules and delegate business operations to database-backed services. Scheduled jobs process attendance, leave accrual, overtime and outgoing email independently of the browser.

## Overtime and email workflows

### Overtime example

Assume eight required working hours, a 15-minute reminder interval and three maximum reminders. An employee checks in at 09:00 and works continuously:

| Approximate time | Action |
|---|---|
| 09:00 | Check-in |
| 17:00 | Required hours completed; initial overtime prompt |
| 17:15 | First reminder if no response |
| 17:30 | Second reminder if no response |
| 17:45 | Third reminder if no response |
| 18:00 | Next due cycle may provisionally close the session if still unanswered |

In the reviewed implementation, closure is recorded at the time the required duration was reached, not at the time the closure job runs. The day is marked `INCOMPLETE` pending review. If the employee confirms overtime, the session remains open and periodic confirmed-overtime reminders are scheduled (default example: 120 minutes). Checkout ends the active workflow. Actual times depend on scheduler execution, shift rules, worked duration and email processing.

### Email categories

| Category | Purpose |
|---|---|
| `OVERTIME_PROMPT` | Required working hours completed |
| `OVERTIME_REMINDER` | Unanswered overtime/check-out prompt |
| `OVERTIME_CHECK` | Confirmed overtime reminder |
| `OVERTIME_CONFIRMED` | Overtime confirmation |
| `FORGOT_CHECKOUT` | Forgotten checkout alert to manager |
| `AUTO_CLOSED` | Provisional attendance closure |
| `AUTO_CLOSED_REVIEW` | Super Admin review required |
| `AUTO_CLOSE_REVIEWED` | Review completed |
| `ATTENDANCE_CORRECTED` | Attendance correction |
| `LEAVE_REQUEST`, `LEAVE_DECISION` | Leave request and decision |
| `WFH_REQUEST`, `WFH_DECISION` | WFH request and decision |

Leave/WFH emails and overtime confirmation are optional categories disabled by default in the reviewed email service.

### Email delivery lifecycle

```mermaid
flowchart TD
    A[Attendance or request event] --> B[Create notification]
    B --> C{Email category enabled?}
    C -- No --> D[In-app notification only]
    C -- Yes --> E[Queue eligible recipient email]
    E --> F[Scheduled outbox processing]
    F --> G{Still eligible?}
    G -- No --> H[Cancelled]
    G -- Yes --> I[SMTP delivery attempt]
    I -- Accepted --> J[Sent]
    I -- Error --> K{Attempts exhausted?}
    K -- No --> L[Pending with backoff]
    L --> F
    K -- Yes --> M[Failed]
    M --> N[Admin retry]
    N --> F
```

The reviewed service attempts up to five deliveries before marking an email failed, using exponential retry delays. `SENT` means the SMTP server accepted the message, not that inbox delivery or reading is guaranteed. Email delivery is not guaranteed exactly once if a process fails after SMTP acceptance but before the database update.

## Installation and setup

### Prerequisites

- Python 3 (the development environment uses Python 3.12).
- PostgreSQL running locally or on an accessible database server.
- Git, and optionally PyCharm.
- SMTP account and credentials if email delivery is required.

### 1. Clone the repository

```powershell
git clone https://github.com/SujanMikkili/employee-attendance-system.git
cd employee-attendance-system
```

For a private repository, authenticate with an account that has access.

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS: `python3 -m venv .venv` followed by `source .venv/bin/activate`.

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

Use the PostgreSQL driver matching `DATABASE_URL`. The reviewed requirements include `psycopg2-binary`; if using `postgresql+psycopg://`, install `psycopg[binary]` and declare it in requirements.

### 4. Configure the environment

```powershell
Copy-Item .env.example .env
```

Example `.env` (replace placeholders locally):

```dotenv
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/attendance_system
SECRET_KEY=REPLACE_WITH_RANDOM_SECRET
ENABLE_SCHEDULER=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
APP_URL=http://127.0.0.1:8000/app/
```

Generate a random secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Never commit the populated `.env` file.

### 5. Create the PostgreSQL database and apply migrations

Create the database named in `DATABASE_URL` using pgAdmin or PostgreSQL tools. For a new empty database:

```powershell
alembic upgrade head
```

For an existing database, back it up and inspect `alembic current`, `alembic history` and the actual schema before applying migrations. Do not blindly stamp `head`: stamping records a revision without creating missing tables or columns. Only stamp a revision when its schema is verified to exist.

For future model changes, review the generated migration before applying it:

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

### 6. Create the first Super Admin

```powershell
python create_super_admin.py
```

Use secure initial credentials. Review local helper scripts for hardcoded credentials before sharing the repository.

### 7. Start the application

```powershell
uvicorn main:app --reload
```

| Resource | Local URL |
|---|---|
| Web application | http://127.0.0.1:8000/app/ |
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |

## Email configuration

For Gmail SMTP, enable two-step verification on an eligible Google account and create an App Password. Configure the following in the local `.env` file:

| Variable | Example / purpose |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_SECURITY` | `starttls` (or `ssl` with the provider's appropriate port) |
| `SMTP_USER` | Sender's email address |
| `SMTP_PASSWORD` | App Password or provider-specific SMTP credential |
| `SMTP_FROM` | Authorized sender address |
| `APP_URL` | Application link included in notification emails |
| `ENABLE_SCHEDULER` | `true` for automatic queue processing |

Restart the backend after changing environment settings. Sign in as Super Admin, open Email Management, send a test email, enable desired categories and save. Monitor delivery history and retry failed messages when appropriate.

A localhost `APP_URL` works only on the machine hosting the app. Use a reachable HTTPS application URL for recipients in a deployed environment. A compatible corporate SMTP provider may be substituted for Gmail.

## First-time configuration

1. Sign in as Super Admin and configure company settings, timezone, working-day rules and attendance thresholds.
2. Create shifts with appropriate start/end times and required working minutes, including overnight shifts if needed.
3. Create managers and employees; assign reporting managers, departments and shifts.
4. Configure holidays, leave balances, accrual and WFH policies.
5. Configure overtime reminder intervals and maximum reminders.
6. Configure email categories and test SMTP delivery.
7. Test an employee check-in/out and a complete approval and overtime workflow.

Older employee creation forms restrict shift names to Morning Shift and Evening Shift. A dynamic shift selection correction was developed separately; verify it is present in the deployed version before using additional shift names.

## Background automation

| Job | Schedule in reviewed scheduler | Purpose |
|---|---|---|
| Attendance finalization | Every 15 minutes | Finalize eligible employee-days based on shift completion and grace periods |
| Monthly leave accrual | First day of each month, 00:10 | Credit paid leave according to company policy |
| Overtime cycle | Every minute | Detect required-hours completion, send reminders and process provisional closure |
| Email outbox | Every minute | Process pending eligible emails and retries |
| Startup catch-up | Once at startup | Recheck attendance finalization and current-month accrual |

The scheduler uses the company timezone. The reviewed finalization service looks back seven days and defines a three-hour shift-end grace period and a separate twelve-hour abandoned-session threshold. Exact eligibility depends on the employee's shift and attendance state.

Run only one scheduler instance when deploying multiple application processes. Background jobs require the backend to be running; closing the browser does not stop them. Startup catch-up is not a guarantee that every historical missed job will be replayed.

## Attendance finalization

Daily results include `PRESENT`, `HALF_DAY`, `ABSENT`, `ON_LEAVE`, `INCOMPLETE` and `FLAGGED`.

- Weekends and holidays are handled according to working-day policy.
- Approved full-day leave is recorded as `ON_LEAVE`; conflicting attendance may be flagged for review.
- Worked duration is evaluated against full-day, short-hours and half-day thresholds.
- Half-day leave is evaluated together with worked duration.
- Missing check-outs can result in incomplete attendance and a manager conflict.
- Overtime-related provisional closures follow their own Super Admin review workflow.
- Authorized administrators can correct attendance and maintain audit records.

## API documentation

Swagger UI at `/docs` provides the complete endpoint list, request schemas and authentication requirements. Selected endpoints from the reviewed implementation:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/dashboard/me` | Personal dashboard |
| GET | `/dashboard/team` | Team or company dashboard |
| GET | `/notifications/` | List notifications |
| POST | `/notifications/read-all` | Mark notifications read |
| POST | `/notifications/{notification_id}/read` | Mark one notification read |
| GET | `/overtime/status` | Employee overtime status |
| POST | `/overtime/confirm` | Confirm overtime |
| GET / PUT | `/overtime/settings` | Read/update overtime settings (update restricted to Super Admin) |
| POST | `/admin/jobs/overtime-cycle` | Trigger overtime processing |
| POST | `/admin/jobs/finalize-day` | Trigger attendance finalization |
| POST | `/admin/jobs/accrue-month` | Trigger leave accrual |
| GET | `/admin/auto-closed` | List provisional closures |
| POST | `/admin/auto-closed/{prompt_id}/confirm` | Review a provisional closure |
| GET / PUT | `/admin/email/settings` | Read/update email settings |
| POST | `/admin/email/test` | Send test email |
| GET | `/admin/email/history` | Email delivery history |
| POST | `/admin/email/retry` | Requeue failed emails |

## Project structure

The following describes the reviewed email-enabled source layout; the latest GitHub working copy may consolidate models or use different module names.

```text
employee-attendance-system/
├── main.py                  # FastAPI entry point and scheduler lifecycle
├── database.py              # Database connection and sessions
├── models.py                # Core ORM models
├── models_extra.py          # Notification, overtime and email models in reviewed archive
├── create_super_admin.py    # Initial administrator setup
├── routers/                 # Authentication, attendance, admin, shifts, holidays,
│                            # leave, WFH, conflicts, dashboard, notifications,
│                            # overtime and email endpoints
├── services/
│   ├── approvals.py         # Approval helpers
│   ├── jobs.py              # Attendance finalization and leave accrual
│   ├── scheduler.py         # Background job scheduling
│   ├── stats.py             # Attendance statistics
│   ├── notifications.py     # Notification generation
│   ├── overtime.py          # Overtime workflow
│   └── email_service.py     # SMTP delivery and outbox processing
├── alembic/                 # Database migrations
├── alembic.ini              # Alembic configuration
├── frontend/index.html      # Single-page web interface
├── tests/                   # API tests
├── requirements.txt         # Python dependencies
├── .env.example             # Environment configuration template
├── .gitignore               # Git exclusion rules
└── README.md                # Project documentation
```

## Testing

```powershell
pytest
```

The original API test setup uses temporary SQLite. Use a dedicated PostgreSQL test database for PostgreSQL-specific migrations, locking and outbox concurrency behavior. Never run destructive tests against production data.

Recommended integration scenarios: role restrictions, multiple attendance sessions, overnight shifts, leave/WFH approvals, missed checkout, overtime confirmation, all reminder stages, auto-closure review, SMTP failure/retry, stale reminder cancellation, monthly accrual and dashboard metric reconciliation.

## Security and deployment

- Keep `.env`, private keys, database dumps, employee exports and local virtual environments out of Git.
- Use a strong secret key, hashed passwords and authorized role checks.
- Do not hardcode SMTP credentials, database passwords or initial admin passwords in scripts or configuration templates.
- Restrict access to email history and employee data; use appropriate retention and backup policies.
- Use HTTPS, restricted CORS origins and a production-appropriate server configuration. Do not use `--reload` in production.
- Run a single scheduler instance or a separately coordinated background worker.
- Review migration history and back up PostgreSQL before deployment.
- GitHub hosts the source code; pushing to GitHub does not deploy the application or upload the live PostgreSQL database.

## Validation and known limitations

- SMTP test delivery and the initial overtime email were observed successfully during development. Full reminder lifecycle and failure/retry scenarios still require end-to-end testing.
- Dashboard calculations are under review, including person-day denominators and reconciliation of late, absent and present counts.
- Existing reminder deadlines may retain the interval used when they were created; verify the interval-change correction before relying on immediate rescheduling.
- The latest working copy must use consistent email module names and model imports. Verify whether email/notification models are consolidated into `models.py`.
- Verify the active Alembic revision chain against the actual database schema before upgrading an existing installation.
- Older employee creation code may enforce Gmail-only employee addresses; verify the current validation policy before onboarding corporate email accounts.

