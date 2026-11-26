from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import (Employee,CompanySetting,Shift,Attendance,AttendanceSession,AttendanceConflict,Request)
from routers.auth import get_current_employee

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def get_company_settings(db: Session):
    return db.query(CompanySetting).first()


def get_company_now(settings):
    timezone_name = (settings.timezone if settings else "Asia/Kolkata")
    try:
        timezone = ZoneInfo(timezone_name)
    except Exception:
        raise HTTPException(status_code=500,detail="Invalid company timezone setting")
    return datetime.now(timezone)


def get_shift_datetimes(shift, work_date, timezone):
    if not shift:
        return None, None

    start_at = datetime.combine(work_date, shift.start_time).replace(tzinfo=timezone)
    end_date = work_date

    if shift.is_overnight:
        end_date += timedelta(days=1)
    elif shift.end_time <= shift.start_time:
        end_date += timedelta(days=1)

    end_at = datetime.combine( end_date, shift.end_time).replace(tzinfo=timezone)
    return start_at, end_at


def current_work_date(db, employee, now):
    """The work date a punch made `now` belongs to.

    For an overnight shift (e.g. 22:00-06:00) a punch after midnight but before the shift's end time belongs to the
    shift that STARTED the previous day. Everyone else: the calendar date.
    """
    shift = db.query(Shift).filter(Shift.id == employee.shift_id).first() if employee.shift_id else None
    if shift and (shift.is_overnight or shift.end_time <= shift.start_time) and now.time() < shift.end_time:
        return now.date() - timedelta(days=1)
    return now.date()


def auto_close_stale_sessions(db, employee, today, now):
    """A session left open on an earlier day must not block today's check-in.

    It is closed at the end of its shift (never later than now), the day is marked INCOMPLETE,
    and a MISSING_CHECK_OUT conflict is raised so a manager can review it.
    Returns how many sessions were closed.
    """
    stale = (db.query(AttendanceSession, Attendance)
             .join(Attendance, AttendanceSession.attendance_id == Attendance.id)
             .filter(Attendance.employee_id == employee.id,
                     AttendanceSession.check_out_at.is_(None),
                     Attendance.work_date < today).all())
    for sess, att in stale:
        check_in_at = sess.check_in_at if sess.check_in_at.tzinfo else sess.check_in_at.replace(tzinfo=now.tzinfo)
        end = check_in_at
        shift = db.query(Shift).filter(Shift.id == att.shift_id).first() if att.shift_id else None
        if shift:
            shift_end = get_shift_datetimes(shift, att.work_date, now.tzinfo)[1]
            if shift_end and shift_end > check_in_at:
                end = shift_end
        end = min(end, now)
        sess.check_out_at = end
        sess.worked_minutes = int((end - check_in_at).total_seconds() // 60)
        db.flush()
        done = (db.query(AttendanceSession).filter(AttendanceSession.attendance_id == att.id,
                                                   AttendanceSession.check_out_at.isnot(None)).all())
        att.worked_minutes = sum(x.worked_minutes for x in done)
        att.check_out_at = end
        att.status = "INCOMPLETE"
        att.overtime_minutes = 0   # the closing time is an estimate: no overtime until a person corrects the times
        if not db.query(AttendanceConflict.id).filter(AttendanceConflict.attendance_id == att.id,
                                                      AttendanceConflict.conflict_type == "MISSING_CHECK_OUT").first():
            db.add(AttendanceConflict(
                employee_id=employee.id, attendance_id=att.id, conflict_type="MISSING_CHECK_OUT", status="OPEN",
                description="Employee did not check out. The session was closed automatically at the end of "
                            "the shift when the next check-in happened. Please review the times."))
    return len(stale)


@router.post("/check-in", status_code=status.HTTP_201_CREATED)
def check_in(db: Session = Depends(get_db),current_user: Employee = Depends(get_current_employee)):
    settings = get_company_settings(db)
    now = get_company_now(settings)
    today = current_work_date(db, current_user, now)
    closed_previous = auto_close_stale_sessions(db, current_user, today, now)
    # Prevent another check-in while a session is open.
    open_session = (db.query(AttendanceSession).join(Attendance).filter
                    (Attendance.employee_id == current_user.id,
                     AttendanceSession.check_out_at.is_(None)).first())
    if open_session:
        raise HTTPException(status_code=400,
                            detail="Please check out of your current session first")
    attendance = (db.query(Attendance).filter(Attendance.employee_id == current_user.id,
                                              Attendance.work_date == today).first())

    if attendance and attendance.is_finalized:
        raise HTTPException(status_code=400,
                            detail="Attendance for today has already been finalized")

    # Check approved WFH request for today.
    approved_wfh = (db.query(Request)
        .filter(Request.employee_id == current_user.id,
                Request.request_type == "WFH",
                Request.status == "APPROVED",
                Request.start_date <= today,
                Request.end_date >= today).first())
    work_mode = "OFFICE"

    if approved_wfh:
        if settings and not settings.wfh_enabled:
            raise HTTPException(status_code=400,
                                detail="Work from home is currently disabled")
        work_mode = "WFH"

    shift = (db.query(Shift).filter(Shift.id == current_user.shift_id).first()
             if current_user.shift_id else None)
    if not attendance:
        attendance = Attendance(employee_id=current_user.id,
                                shift_id=current_user.shift_id,
                                work_date=today,
                                check_in_at=now,
                                work_mode=work_mode,
                                status="IN_PROGRESS",
                                worked_minutes=0,
                                late_minutes=0,
                                overtime_minutes=0)
        db.add(attendance)
        db.flush()

        # Calculate lateness only for the first check-in.
        if shift:
            timezone = now.tzinfo
            shift_start, _ = get_shift_datetimes(shift, today, timezone)
            grace_minutes = (settings.late_grace_minutes if settings else 0)

            late_minutes = int(max(0,(now - shift_start).total_seconds() / 60 - grace_minutes))
            attendance.late_minutes = late_minutes
    elif attendance.check_in_at is None:
        attendance.check_in_at = now

    # Create a separate session for every check-in.
    session_record = AttendanceSession(
        attendance_id=attendance.id,
        check_in_at=now,
        worked_minutes=0,
    )

    attendance.status = "IN_PROGRESS"
    attendance.check_out_at = None

    db.add(session_record)

    try:
        db.commit()
        db.refresh(attendance)
        db.refresh(session_record)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to record check-in",
        )

    return {
        "message": "Check-in successful",
        "attendance_id": attendance.id,
        "session_id": session_record.id,
        "check_in_at": session_record.check_in_at,
        "work_date": attendance.work_date,
        "work_mode": attendance.work_mode,
        "status": attendance.status,
        "previous_session_closed": closed_previous > 0,
    }


@router.post("/check-out")
def check_out(db: Session = Depends(get_db),current_user: Employee = Depends(get_current_employee)):
    settings = get_company_settings(db)
    now = get_company_now(settings)

    # A session left open from an earlier day is closed at its shift end (not at "now") and flagged for review.
    closed_previous = auto_close_stale_sessions(db, current_user, current_work_date(db, current_user, now), now)
    if closed_previous:
        db.flush()

    # Find the employee's currently open session.
    session_record = (db.query(AttendanceSession).join(Attendance).filter(Attendance.employee_id == current_user.id,
            AttendanceSession.check_out_at.is_(None))
        .order_by(AttendanceSession.id.desc())
        .first())

    if not session_record:
        if closed_previous:
            db.commit()
            return {"message": "Your earlier unfinished session was closed automatically at the end of its shift "
                               "and flagged for review", "previous_session_closed": True}
        raise HTTPException(status_code=400,detail="No active check-in session found")

    attendance = (db.query(Attendance).filter(Attendance.id == session_record.attendance_id).first())

    if not attendance or attendance.is_finalized:
        raise HTTPException(status_code=400,detail="Attendance is unavailable or finalized")

    check_in_at = session_record.check_in_at

    # Normalize timestamps to the same timezone before subtraction.
    if check_in_at.tzinfo is None:
        check_in_at = check_in_at.replace(tzinfo=now.tzinfo)

    if now < check_in_at:
        raise HTTPException(status_code=400,detail="Check-out cannot be before check-in")

    session_minutes = int((now - check_in_at).total_seconds() // 60)

    session_record.check_out_at = now
    session_record.worked_minutes = session_minutes

    # Recalculate the day's total from all completed sessions.
    db.flush()

    completed_sessions = (db.query(AttendanceSession).filter(AttendanceSession.attendance_id == attendance.id,
                                                             AttendanceSession.check_out_at.isnot(None)).all())
    total_worked_minutes = sum(item.worked_minutes for item in completed_sessions)

    attendance.worked_minutes = total_worked_minutes
    attendance.check_out_at = now
    attendance.status = "COMPLETED"

    shift = (db.query(Shift).filter(Shift.id == attendance.shift_id).first() if attendance.shift_id else None)

    # Calculate early checkout for this session's checkout.
    early_checkout_minutes = 0

    if shift:
        timezone = now.tzinfo
        _, shift_end = get_shift_datetimes(shift, attendance.work_date, timezone)

        # For overnight shifts, the end may be on the next day.
        if shift.is_overnight and now.date() > attendance.work_date:
            _, shift_end = get_shift_datetimes(shift, attendance.work_date, timezone)

        if now < shift_end:
            early_checkout_minutes = int((shift_end - now).total_seconds() // 60)

    overtime_minutes = 0

    if settings and settings.allow_overtime and shift:
        overtime_minutes = max(0,total_worked_minutes - shift.required_work_minutes)
    attendance.overtime_minutes = overtime_minutes

    try:
        db.commit()
        db.refresh(attendance)
        db.refresh(session_record)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500,detail="Failed to record check-out")
    return {"message": "Check-out successful",
            "attendance_id": attendance.id,
            "session_id": session_record.id,
            "check_out_at": session_record.check_out_at,
            "session_worked_minutes": session_minutes,
            "total_worked_minutes": attendance.worked_minutes,
            "late_minutes": attendance.late_minutes,
            "early_checkout_minutes": early_checkout_minutes,
            "overtime_minutes": attendance.overtime_minutes,
            "status": attendance.status}