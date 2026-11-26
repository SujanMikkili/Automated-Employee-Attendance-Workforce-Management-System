from datetime import date, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Employee, Attendance, AttendanceSession
from services.stats import build_days, summarize
from routers.auth import get_current_employee, require_roles
from routers.attendance import get_company_settings, get_company_now, current_work_date

router = APIRouter(prefix="/attendance", tags=["Attendance History"])


def att_out(a: Attendance):
    return {"id": a.id, "work_date": a.work_date, "work_mode": a.work_mode, "status": a.status,
            "check_in_at": a.check_in_at, "check_out_at": a.check_out_at,
            "worked_minutes": a.worked_minutes, "late_minutes": a.late_minutes,
            "overtime_minutes": a.overtime_minutes, "is_finalized": a.is_finalized, "notes": a.notes,
            "sessions": [{"id": s.id, "check_in_at": s.check_in_at, "check_out_at": s.check_out_at,
                          "worked_minutes": s.worked_minutes}
                         for s in sorted(a.sessions, key=lambda s: s.id)]}


@router.get("/today")
def today(db: Session = Depends(get_db), user: Employee = Depends(get_current_employee)):
    d = current_work_date(db, user, get_company_now(get_company_settings(db)))   # a night shift after midnight is still 'yesterday'
    rec = db.query(Attendance).filter(Attendance.employee_id == user.id, Attendance.work_date == d).first()
    # An unfinished session blocks a new check-in, even when it is from a previous day.
    open_row = (db.query(AttendanceSession, Attendance).join(Attendance, AttendanceSession.attendance_id == Attendance.id)
                .filter(Attendance.employee_id == user.id, AttendanceSession.check_out_at.is_(None))
                .order_by(AttendanceSession.id.desc()).first())
    open_session = ({"id": open_row[0].id, "check_in_at": open_row[0].check_in_at, "work_date": open_row[1].work_date}
                    if open_row else None)
    return {"work_date": d, "record": att_out(rec) if rec else None,
            "open_session": open_session, "checked_in": open_session is not None}


@router.get("/my-records")
def my_records(start: date | None = None, end: date | None = None,
               db: Session = Depends(get_db), user: Employee = Depends(get_current_employee)):
    end = end or get_company_now(get_company_settings(db)).date()
    start = start or end - timedelta(days=30)
    rows = (db.query(Attendance).filter(Attendance.employee_id == user.id,
                                        Attendance.work_date >= start, Attendance.work_date <= end)
            .order_by(Attendance.work_date.desc()).all())
    return [att_out(a) for a in rows]


@router.get("/team")
def team(work_date: date | None = None, db: Session = Depends(get_db),
         user: Employee = Depends(require_roles("MANAGER", "SUPER_ADMIN"))):
    d = work_date or get_company_now(get_company_settings(db)).date()
    people = db.query(Employee).filter(Employee.is_active.is_(True), Employee.id != user.id)
    if user.role == "MANAGER":
        people = people.filter(Employee.manager_id == user.id)
    people = people.order_by(Employee.first_name).all()
    ids = [p.id for p in people] or [0]
    recs = {a.employee_id: a for a in db.query(Attendance).filter(
        Attendance.work_date == d, Attendance.employee_id.in_(ids)).all()}
    if work_date is None:      # live view: a night-shift worker is still on yesterday's work date
        for _, open_att in (db.query(AttendanceSession, Attendance)
                            .join(Attendance, AttendanceSession.attendance_id == Attendance.id)
                            .filter(AttendanceSession.check_out_at.is_(None), Attendance.employee_id.in_(ids)).all()):
            recs[open_att.employee_id] = open_att
    rows = []
    for p in people:
        a = recs.get(p.id)
        rows.append({"employee_id": p.id, "name": f"{p.first_name} {p.last_name}", "role": p.role,
                     "status": a.status if a else "NOT_CHECKED_IN", "work_mode": a.work_mode if a else None,
                     "check_in_at": a.check_in_at if a else None, "check_out_at": a.check_out_at if a else None,
                     "worked_minutes": a.worked_minutes if a else 0, "late_minutes": a.late_minutes if a else 0})
    return {"work_date": d, "rows": rows}


@router.get("/my-daily")
def my_daily(start: date | None = None, end: date | None = None, db: Session = Depends(get_db),
             user: Employee = Depends(get_current_employee)):
    """Finalized day-by-day results (PRESENT / HALF_DAY / ABSENT / ON_LEAVE ...)."""
    from models import DailyAttendanceStatus as D
    end = end or get_company_now(get_company_settings(db)).date()
    start = start or end - timedelta(days=30)
    rows = (db.query(D).filter(D.employee_id == user.id, D.work_date >= start, D.work_date <= end)
            .order_by(D.work_date.desc()).all())
    return [{"work_date": r.work_date, "status": r.status, "worked_minutes": r.worked_minutes,
             "required_work_minutes": r.required_work_minutes, "late_minutes": r.late_minutes,
             "early_checkout_minutes": r.early_checkout_minutes, "overtime_minutes": r.overtime_minutes,
             "is_finalized": r.is_finalized, "notes": r.notes} for r in rows]


# =====================================================================================================
# Working-time report (powers the "Working Time" dashboard and its slicer)
# =====================================================================================================
Preset = Literal["today", "last7", "last14", "last30", "this_month", "last_month"]


def resolve_range(preset, start, end, today):
    """Turn the slicer choice into real dates, in the company's timezone."""
    if preset == "today":
        return today, today
    if preset == "last7":
        return today - timedelta(days=6), today
    if preset == "last14":
        return today - timedelta(days=13), today
    if preset == "last30":
        return today - timedelta(days=29), today
    if preset == "this_month":
        return today.replace(day=1), today
    if preset == "last_month":
        last_prev = today.replace(day=1) - timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    end = min(end or today, today)                       # custom range; the future has no data yet
    return (start or end - timedelta(days=6)), end


def can_view(user: Employee, target: Employee) -> bool:
    return (user.id == target.id or user.role == "SUPER_ADMIN"
            or (user.role == "MANAGER" and target.manager_id == user.id))


@router.get("/report/people")
def report_people(db: Session = Depends(get_db), user: Employee = Depends(get_current_employee)):
    """Whose working time this user may look at: themselves; a manager's team; everyone for the Super Admin."""
    q = db.query(Employee).filter(Employee.is_active.is_(True), Employee.id != user.id)
    if user.role == "EMPLOYEE":
        others = []
    elif user.role == "MANAGER":
        others = q.filter(Employee.manager_id == user.id).order_by(Employee.first_name).all()
    else:
        others = q.order_by(Employee.first_name).all()
    return [{"id": p.id, "name": f"{p.first_name} {p.last_name}", "role": p.role, "code": p.employee_code}
            for p in [user, *others]]


@router.get("/report")
def working_time_report(preset: Preset | None = None, start: date | None = None, end: date | None = None,
                        employee_id: int | None = None, db: Session = Depends(get_db),
                        user: Employee = Depends(get_current_employee)):
    """Working time for every day in a range, plus totals. Pass `preset` OR `start`/`end`."""
    settings = get_company_settings(db)
    now = get_company_now(settings)
    today = now.date()
    target = user
    if employee_id and employee_id != user.id:
        target = db.get(Employee, employee_id)
        if not target:
            raise HTTPException(404, "Employee not found")
        if not can_view(user, target):
            raise HTTPException(403, "You can only view your own team's working time")
    first, last = resolve_range(preset, start, end, today)
    if first > last:
        raise HTTPException(400, "The start date cannot be after the end date (or after today)")
    if (last - first).days > 365:
        raise HTTPException(400, "Choose a period of at most one year")

    days = build_days(db, [target], first, last, now, settings)[target.id]
    summary = summarize(days, today)
    return {"employee": {"id": target.id, "name": f"{target.first_name} {target.last_name}", "role": target.role},
            "start": first, "end": last, "today": today, "summary": summary, "days": days}