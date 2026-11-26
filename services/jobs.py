"""Attendance finalization and monthly leave accrual.

finalize_day()  -> turns raw check-ins into one DailyAttendanceStatus per employee per working day.
accrue_month()  -> credits monthly paid leave and records a LeaveAccrualHistory snapshot.
Both are idempotent, so running them twice is safe.
"""
import calendar
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from models import (Employee, Attendance, AttendanceConflict, DailyAttendanceStatus, Holiday, Request, Shift,
                    CompanySetting, LeaveBalance, LeaveAccrualHistory,OvertimePrompt)
from routers.attendance import get_shift_datetimes


def get_settings(db: Session):
    return db.query(CompanySetting).first()


def company_tz(s):
    return ZoneInfo(s.timezone if s else "Asia/Kolkata")


def is_working_day(db: Session, d: date) -> bool:
    return d.weekday() < 5 and not db.query(Holiday.id).filter(Holiday.holiday_date == d).first()


FINALIZE_GRACE = timedelta(hours=3)    # people may still add a late session after their shift has ended
ABANDON_AFTER = timedelta(hours=12)    # an open session this long after the shift ended is a forgotten check-out


def day_ready_at(shift, d, tz):
    """(ready_time, shift_end) for one employee's work date.

    A day is only finalized once that employee's OWN shift is over: the later of (shift end + 3 hours) and 00:30 after
    the work date. A day shift is therefore finalized at 00:30, an evening shift ending 23:00 at 02:00 and a night
    shift ending 06:00 at 09:00. Without a shift the day ends at 00:30.
    """
    cutoff = datetime.combine(d + timedelta(days=1), time(0, 30), tzinfo=tz)
    if not shift:
        return cutoff, None
    shift_end = get_shift_datetimes(shift, d, tz)[1]
    return max(shift_end + FINALIZE_GRACE, cutoff), shift_end


def _aware(dt, tz):
    return dt if dt.tzinfo else dt.replace(tzinfo=tz)


def _add_conflict(db, emp_id, att_id, req_id, ctype, text):
    exists = db.query(AttendanceConflict).filter(
        AttendanceConflict.employee_id == emp_id, AttendanceConflict.attendance_id == att_id,
        AttendanceConflict.conflict_type == ctype,
        AttendanceConflict.status.in_(["OPEN", "UNDER_REVIEW"])).first()
    if not exists:
        db.add(AttendanceConflict(employee_id=emp_id, attendance_id=att_id, request_id=req_id,
                                  conflict_type=ctype, status="OPEN", description=text))


def finalize_employee_day(db: Session, emp: Employee, d: date, s, force: bool = False, now=None):
    """Compute and store the final daily status.

    Returns the status, None if it was already finalized, or "NOT_READY" while the employee's shift is still running.
    """
    daily = db.query(DailyAttendanceStatus).filter(DailyAttendanceStatus.employee_id == emp.id,
                                                   DailyAttendanceStatus.work_date == d).first()
    if daily and daily.is_finalized and not force:
        return None
    tz = company_tz(s)
    now = now or datetime.now(tz)
    full, half, short = (s.full_day_minutes, s.half_day_minutes, s.short_hours_minutes) if s else (480, 240, 360)
    require_out = s.require_check_out if s else True
    att = db.query(Attendance).filter(Attendance.employee_id == emp.id, Attendance.work_date == d).first()
    shift = db.get(Shift, att.shift_id) if att and att.shift_id else emp.shift
    if not force:
        ready, shift_end_ = day_ready_at(shift, d, tz)
        if att and any(x.check_out_at is None for x in att.sessions):    # still checked in: wait until it is clearly forgotten
            ready = max(ready, (shift_end_ + ABANDON_AFTER) if shift_end_ else ready + ABANDON_AFTER)
        if now < ready:
            return "NOT_READY"
    leave = db.query(Request).filter(Request.employee_id == emp.id, Request.request_type == "LEAVE",
                                     Request.status == "APPROVED", Request.start_date <= d,
                                     Request.end_date >= d).first()
    half_leave = bool(leave and leave.duration_days is not None and leave.duration_days < 1)
    full_leave = bool(leave and not half_leave)
    notes, worked, late, early, overtime = [], 0, 0, 0, 0
    status, has_open = "ABSENT", False

    if att:
        shift_end = get_shift_datetimes(shift, d, tz)[1] if shift else None
        has_open = att.status == "INCOMPLETE"   # already auto-closed at check-in time; still needs review
        for x in [x for x in att.sessions if x.check_out_at is None]:
            cin = _aware(x.check_in_at, tz)
            end = shift_end if shift_end and shift_end > cin else cin
            end = min(end, now)                  # never close a session in the future
            x.check_out_at, x.worked_minutes = end, int((end - cin).total_seconds() // 60)
            has_open = True
        if has_open:
            att.check_out_at = max(_aware(x.check_out_at, tz) for x in att.sessions)
            if require_out:
                att.status = "INCOMPLETE"
                notes.append("Missing check-out; session auto-closed at shift end (overtime not counted until the times are corrected)")
                if not db.query(OvertimePrompt.id).filter(OvertimePrompt.attendance_id == att.id,
                                                          OvertimePrompt.state == "AUTO_CLOSED").first():
                    _add_conflict(db, emp.id, att.id, None, "MISSING_CHECK_OUT",
                                  "Employee did not check out. The session was closed automatically; please review.")
        worked = sum(x.worked_minutes for x in att.sessions)
        att.worked_minutes, late = worked, att.late_minutes
        if s and s.allow_overtime and shift and not has_open:   # no overtime on an unreviewed, auto-closed day
            overtime = max(0, worked - shift.required_work_minutes)
        att.overtime_minutes = overtime
        if shift_end and att.check_out_at:
            early = max(0, int((shift_end - _aware(att.check_out_at, tz)).total_seconds() // 60))

    if att and att.check_in_at and full_leave:
        status = "FLAGGED"
        notes.append("Attendance recorded on an approved leave day")
        att.status = "FLAGGED"
        _add_conflict(db, emp.id, att.id, leave.id, "ATTENDANCE_DURING_LEAVE",
                      "Attendance activity exists on an approved leave date. Review required.")
    elif has_open and require_out:
        status = "INCOMPLETE"
    elif full_leave:
        status = "ON_LEAVE"
        notes.append(f"Approved leave request ID {leave.id}")
    elif half_leave:
        status = "HALF_DAY" if worked >= half else "ABSENT"
        notes.append(f"Half-day leave (request ID {leave.id})")
    elif att:
        if worked >= full:
            status = "PRESENT"
        elif worked >= short:
            status = "PRESENT"
            notes.append("Short hours")
        elif worked >= half:
            status = "HALF_DAY"
        else:
            status = "ABSENT"
            notes.append("Worked less than the half-day threshold")

    if att and not is_working_day(db, d):
        notes.append("Worked on a weekend or holiday")

    if not daily:
        daily = DailyAttendanceStatus(employee_id=emp.id, work_date=d)
        db.add(daily)
    daily.shift_id = att.shift_id if att else emp.shift_id
    daily.worked_minutes, daily.late_minutes = worked, late
    daily.early_checkout_minutes, daily.overtime_minutes = early, overtime
    daily.required_work_minutes = shift.required_work_minutes if shift else full
    daily.status, daily.is_finalized, daily.finalized_at = status, True, now
    daily.notes = "; ".join(notes) or None
    if att:
        att.is_finalized = True
    return status


def finalize_day(db: Session, d: date, force: bool = False, now=None) -> dict:
    """Finalize every employee whose shift for work date `d` is over; the others are picked up on a later run."""
    s = get_settings(db)
    now = now or datetime.now(company_tz(s))
    working = is_working_day(db, d)
    attended = select(Attendance.employee_id).where(Attendance.work_date == d)
    q = db.query(Employee).filter(Employee.is_active.is_(True), Employee.date_of_joining <= d)
    if working:    # Super Admins only on days they actually punched (never marked absent)
        q = q.filter(or_(Employee.role != "SUPER_ADMIN", Employee.id.in_(attended)))
    else:          # weekend / holiday: only people who actually worked
        q = q.filter(Employee.id.in_(attended))
    emps = q.all()
    done = set() if force else {r[0] for r in db.query(DailyAttendanceStatus.employee_id).filter(
        DailyAttendanceStatus.work_date == d, DailyAttendanceStatus.is_finalized.is_(True)).all()}
    counts, skipped, waiting = {}, 0, 0
    for emp in emps:
        if emp.id in done:
            skipped += 1
            continue
        st = finalize_employee_day(db, emp, d, s, force, now)
        if st == "NOT_READY":
            waiting += 1
        elif st is None:
            skipped += 1
        else:
            counts[st] = counts.get(st, 0) + 1
    db.commit()
    out = {"work_date": d, "employees": len(emps), "already_finalized": skipped, "not_ready": waiting, "counts": counts}
    if not working:
        out["note"] = "Weekend or holiday: only people who worked were finalized"
    return out


def finalize_pending(db: Session, up_to: date, lookback: int = 7, now=None) -> list:
    return [finalize_day(db, up_to - timedelta(days=i), now=now) for i in range(lookback - 1, -1, -1)]


def accrue_month(db: Session, year: int, month: int) -> dict:
    s = get_settings(db)
    if not s:
        raise ValueError("Company settings must be created before accruing leave")
    q1 = Decimal("0.1")
    monthly, annual = Decimal(s.monthly_paid_leave_days), Decimal(s.annual_paid_leave_days)
    first, last = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    emps = db.query(Employee).filter(Employee.is_active.is_(True), Employee.role != "SUPER_ADMIN",
                                     Employee.date_of_joining <= last).all()
    created = skipped = 0
    for emp in emps:
        if db.query(LeaveAccrualHistory.id).filter_by(employee_id=emp.id, year=year, month=month).first():
            skipped += 1
            continue
        prev = (db.query(LeaveAccrualHistory).filter_by(employee_id=emp.id, year=year, month=month - 1).first()
                if month > 1 else None)
        carried = Decimal(prev.closing_balance) if prev else Decimal("0.0")
        bal = db.query(LeaveBalance).filter_by(employee_id=emp.id, leave_type="PAID", year=year).first()
        if not bal:
            bal = LeaveBalance(employee_id=emp.id, leave_type="PAID", year=year, allocated_days=0, used_days=0)
            db.add(bal)
            db.flush()
        grant = min(monthly, max(Decimal(0), annual - Decimal(bal.allocated_days))).quantize(q1)
        used = sum((Decimal(r.duration_days or 0) for r in db.query(Request).filter(
            Request.employee_id == emp.id, Request.request_type == "LEAVE", Request.status == "APPROVED",
            Request.leave_type == "PAID", Request.start_date >= first, Request.start_date <= last).all()),
            Decimal(0))
        used = min(used, carried + grant).quantize(q1)
        db.add(LeaveAccrualHistory(employee_id=emp.id, year=year, month=month, allocated_days=grant,
                                   carried_forward_days=carried.quantize(q1), used_days=used,
                                   closing_balance=(carried + grant - used).quantize(q1)))
        bal.allocated_days = Decimal(bal.allocated_days) + grant
        created += 1
    db.commit()
    return {"year": year, "month": month, "created": created, "already_done": skipped}