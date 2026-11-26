# Employee Attendance Management System

FastAPI + SQLAlchemy + PostgreSQL backend with a built-in web frontend.

## What it does

| Area | Details |
|---|---|
| Auth & roles | JWT login; `SUPER_ADMIN`, `MANAGER`, `EMPLOYEE`; change password |
| Attendance | Multi-session check-in/out, late/overtime, WFH mode, personal history, team view |
| Daily results | Nightly job turns raw punches into `PRESENT / HALF_DAY / ABSENT / ON_LEAVE / INCOMPLETE / FLAGGED` using the company thresholds |
| Leave | Apply, edit, withdraw, half-day, cancel after approval, manager approve/reject, balances, auto-approve policy |
| Leave accrual | Monthly job credits paid leave (capped at the annual limit) and records a carry-forward ledger |
| WFH | Requests with notice period, monthly limit, overlap checks, approval or auto-approval |
| Conflicts | Missing check-outs and attendance-during-leave are flagged; managers resolve them |
| Admin | Employees (create/list/update/reset password/change email/delete), shifts, holidays, company settings, leave allocations, attendance corrections, audit log, manual job triggers |

## Setup

1. `python -m venv venv` then activate it (`venv\Scripts\activate` on Windows, `source venv/bin/activate` elsewhere).
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in `DATABASE_URL` and `SECRET_KEY`.
4. Create the PostgreSQL database named in `DATABASE_URL`.
5. Create the tables:
   - **New database:** `alembic upgrade head`
   - **Database you already created with the old app:** `alembic stamp head` (it already has the tables)
6. Create the first admin: `python create_super_admin.py`
7. Run: `uvicorn main:app --reload`
8. Open the app at http://127.0.0.1:8000/app/ (API docs at /docs).

After changing `models.py`: `alembic revision --autogenerate -m "describe change"` then `alembic upgrade head`.

## First-time configuration (Super Admin)

1. Company Settings: create the settings.
2. Shifts: create "Morning Shift" and "Evening Shift" (employee creation currently accepts these two names).
3. Employees: create a manager, then employees assigned to that manager.
4. Leave Balances: allocate leave days (or run the monthly accrual from the Automation page).

## Automation

Background jobs run inside the app (APScheduler, company timezone):

- **00:30 daily** finalizes the previous working days (last 7, idempotent).
- **00:10 on the 1st** credits that month's paid leave.
- On startup the app also catches up on missed runs.

Both can be run by hand from the Automation page (or `POST /admin/jobs/finalize-day`, `/admin/jobs/accrue-month`).
If you run several server workers, set `ENABLE_SCHEDULER=false` on all but one.

### How a day is finalized

Weekends and holidays are skipped. For every active non-admin employee:

- Approved full-day leave -> `ON_LEAVE` (attendance on that day -> `FLAGGED` plus a conflict).
- Worked >= full-day minutes -> `PRESENT`; >= short-hours minutes -> `PRESENT` (noted "Short hours");
  >= half-day minutes -> `HALF_DAY`; otherwise `ABSENT`. No punches -> `ABSENT`.
- Half-day leave -> `HALF_DAY` if the employee worked at least the half-day minutes, else `ABSENT`.
- No check-out (when "require check-out" is on): the session is closed at shift end, the day is `INCOMPLETE`, and a `MISSING_CHECK_OUT` conflict is raised for the manager. An admin can fix the times with an attendance correction.

## Tests

`pytest` (uses a temporary SQLite database; no PostgreSQL needed).

## Project layout

```
main.py  database.py  models.py  create_super_admin.py
routers/    auth, admin, admin_extra, admin_ops, password, attendance, attendance_history,
            holidays, shifts, company_settings, leaves, leave_cancel, balances, wfh, conflicts
services/   jobs.py (finalize + accrual), scheduler.py
alembic/    migrations
frontend/   index.html (single-page app served at /app/)
tests/
```

## Security notes

- Never commit `.env`. Use a long random `SECRET_KEY`.
- Tokens expire after 30 minutes; the app signs you out when one expires.
- Deleting an employee is permanent. Prefer deactivating (Employees -> Manage -> Account status).
- Email addresses must end in `@gmail.com` (existing rule in `routers/admin.py`).
