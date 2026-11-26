from datetime import date, datetime, time, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from models import (Employee, Attendance, AttendanceSession, AttendanceConflict, DailyAttendanceStatus,
                    LeaveAccrualHistory, LeaveBalance, Request, AuditLog, OvertimePrompt)
from sqlalchemy import func
from services.notifications import notify
from routers.auth import require_roles, get_password_hash
from routers.admin import validate_email, check_duplicate_employee
from routers.attendance import get_shift_datetimes
from routers.attendance_history import att_out
from services.jobs import (get_settings, company_tz, finalize_day, finalize_employee_day, accrue_month)

router = APIRouter(prefix="/admin", tags=["Admin Operations"])
admin_only = require_roles("SUPER_ADMIN")


def log(db, actor, action, entity, eid, old=None, new=None, reason=None):
    db.add(AuditLog(actor_employee_id=actor, action=action, entity_type=entity, entity_id=eid,
                    old_values=old, new_values=new, reason=reason))


def get_emp(db, employee_id) -> Employee:
    e = db.query(Employee).filter(Employee.id == employee_id).first()
    if not e:
        raise HTTPException(404, "Employee not found")
    return e


# ---------- Account management ----------
class PasswordReset(BaseModel):
    new_password: str


@router.post("/employees/{employee_id}/reset-password")
def reset_password(employee_id: int, body: PasswordReset, db: Session = Depends(get_db),
                   admin: Employee = Depends(admin_only)):
    e = get_emp(db, employee_id)
    if not 8 <= len(body.new_password.encode("utf-8")) <= 72:
        raise HTTPException(400, "Password must be at least 8 characters and at most 72 bytes")
    e.password_hash = get_password_hash(body.new_password)
    log(db, admin.id, "PASSWORD_RESET", "EMPLOYEE", e.id)
    db.commit()
    return {"message": f"Password reset for {e.first_name} {e.last_name}"}


class AccountChange(BaseModel):
    email: str | None = None
    employee_code: str | None = None


@router.patch("/employees/{employee_id}/account")
def change_account(employee_id: int, body: AccountChange, db: Session = Depends(get_db),
                   admin: Employee = Depends(admin_only)):
    e = get_emp(db, employee_id)
    if not (body.email and body.email.strip()) and not (body.employee_code and body.employee_code.strip()):
        raise HTTPException(400, "Provide an email or an employee code")
    email = validate_email(body.email) if body.email and body.email.strip() else e.email
    code = body.employee_code.strip().upper() if body.employee_code and body.employee_code.strip() else e.employee_code
    check_duplicate_employee(db, code, email, exclude_id=e.id)
    old = f"email={e.email}, employee_code={e.employee_code}"
    e.email, e.employee_code = email, code
    log(db, admin.id, "ACCOUNT_CHANGED", "EMPLOYEE", e.id, old, f"email={email}, employee_code={code}")
    db.commit()
    return {"message": "Account details updated", "email": email, "employee_code": code}


@router.delete("/employees/{employee_id}")
def delete_employee(employee_id: int, db: Session = Depends(get_db), admin: Employee = Depends(admin_only)):
    """Permanently delete an employee and their records. Deactivating is usually the better choice."""
    e = get_emp(db, employee_id)
    if e.id == admin.id or e.role == "SUPER_ADMIN":
        raise HTTPException(400, "Super Admin accounts cannot be deleted")
    if db.query(Employee.id).filter(Employee.manager_id == e.id).first():
        raise HTTPException(400, "Reassign this manager's team before deleting the account")
    name = f"{e.first_name} {e.last_name} ({e.employee_code})"
    for model in (AttendanceConflict, DailyAttendanceStatus, LeaveAccrualHistory, LeaveBalance, Request):
        db.query(model).filter(model.employee_id == e.id).delete(synchronize_session=False)
    db.query(Request).filter(Request.approver_id == e.id).update({"approver_id": None})
    db.query(Request).filter(Request.reviewed_by == e.id).update({"reviewed_by": None})
    db.query(AttendanceConflict).filter(AttendanceConflict.resolved_by == e.id).update({"resolved_by": None})
    db.query(AuditLog).filter(AuditLog.actor_employee_id == e.id).update({"actor_employee_id": None})
    db.expire_all()
    db.delete(get_emp(db, employee_id))
    log(db, admin.id, "EMPLOYEE_DELETED", "EMPLOYEE", employee_id, old=name)
    db.commit()
    return {"message": f"Deleted {name}"}


# ---------- Attendance corrections ----------
class Correction(BaseModel):
    employee_id: int
    work_date: date
    check_in: time
    check_out: time | None = None
    work_mode: Literal["OFFICE", "WFH"] = "OFFICE"
    reason: str = Field(min_length=3, max_length=1000)


@router.get("/attendance")
def employee_attendance(employee_id: int, start: date | None = None, end: date | None = None,
                        db: Session = Depends(get_db), _: Employee = Depends(admin_only)):
    get_emp(db, employee_id)
    end = end or date.today()
    start = start or end - timedelta(days=30)
    rows = (db.query(Attendance).filter(Attendance.employee_id == employee_id, Attendance.work_date >= start,
                                        Attendance.work_date <= end).order_by(Attendance.work_date.desc()).all())
    return [att_out(a) for a in rows]


@router.post("/attendance/correct")
def correct_attendance(body: Correction, db: Session = Depends(get_db), admin: Employee = Depends(admin_only)):
    """Create or replace a day's attendance (one session) and recompute its daily result."""
    emp = get_emp(db, body.employee_id)
    s = get_settings(db)
    tz = company_tz(s)
    if body.work_date > datetime.now(tz).date():
        raise HTTPException(400, "Cannot record attendance for a future date")
    cin = datetime.combine(body.work_date, body.check_in, tzinfo=tz)
    cout = None
    if body.check_out:
        cout = datetime.combine(body.work_date, body.check_out, tzinfo=tz)
        if cout <= cin:
            cout += timedelta(days=1)
    att = db.query(Attendance).filter(Attendance.employee_id == emp.id,
                                      Attendance.work_date == body.work_date).first()
    old = None
    if att:
        old = f"in={att.check_in_at}, out={att.check_out_at}, worked={att.worked_minutes}, status={att.status}"
        att.sessions.clear()
        db.flush()
    else:
        att = Attendance(employee_id=emp.id, shift_id=emp.shift_id, work_date=body.work_date)
        db.add(att)
        db.flush()
    minutes = int((cout - cin).total_seconds() // 60) if cout else 0
    att.sessions.append(AttendanceSession(check_in_at=cin, check_out_at=cout, worked_minutes=minutes))
    late = 0
    if emp.shift:
        start_at = get_shift_datetimes(emp.shift, body.work_date, tz)[0]
        late = int(max(0, (cin - start_at).total_seconds() / 60 - (s.late_grace_minutes if s else 0)))
    att.check_in_at, att.check_out_at, att.work_mode = cin, cout, body.work_mode
    att.worked_minutes, att.late_minutes, att.overtime_minutes = minutes, late, 0
    att.status = "COMPLETED" if cout else "IN_PROGRESS"
    att.is_finalized = False
    att.notes = f"Corrected by admin: {body.reason}"
    db.flush()
    result = None
    if cout:
        db.expire(emp)
        result = finalize_employee_day(db, emp, body.work_date, s, force=True)
    db.query(OvertimePrompt).filter(OvertimePrompt.attendance_id == att.id, OvertimePrompt.state == "AUTO_CLOSED",
                                    OvertimePrompt.reviewed_at.is_(None)).update(
        {"reviewed_by": admin.id, "reviewed_at": func.now(), "review_note": f"Corrected: {body.reason}"}, synchronize_session=False)
    notify(db, emp.id, "ATTENDANCE_CORRECTED", "Attendance corrected",
           f"A Super Admin corrected your attendance for {body.work_date}.", attendance_id=att.id)
    log(db, admin.id, "ATTENDANCE_CORRECTED", "ATTENDANCE", att.id, old,
        f"in={cin}, out={cout}, worked={minutes}", body.reason)
    db.commit()
    db.refresh(att)
    return {"message": "Attendance corrected", "daily_status": result, "attendance": att_out(att)}


# ---------- Automation (manual triggers) ----------
class FinalizeBody(BaseModel):
    work_date: date
    force: bool = False


@router.post("/jobs/finalize-day")
def run_finalize(body: FinalizeBody, db: Session = Depends(get_db), _: Employee = Depends(admin_only)):
    if body.work_date > datetime.now(company_tz(get_settings(db))).date():
        raise HTTPException(400, "A future day cannot be finalized")
    return finalize_day(db, body.work_date, body.force)


class AccrueBody(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


@router.post("/jobs/accrue-month")
def run_accrual(body: AccrueBody, db: Session = Depends(get_db), _: Employee = Depends(admin_only)):
    try:
        return accrue_month(db, body.year, body.month)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/accruals")
def accrual_history(employee_id: int, db: Session = Depends(get_db), _: Employee = Depends(admin_only)):
    rows = (db.query(LeaveAccrualHistory).filter_by(employee_id=employee_id)
            .order_by(LeaveAccrualHistory.year.desc(), LeaveAccrualHistory.month.desc()).all())
    return [{"year": r.year, "month": r.month, "allocated_days": float(r.allocated_days),
             "carried_forward_days": float(r.carried_forward_days), "used_days": float(r.used_days),
             "closing_balance": float(r.closing_balance)} for r in rows]