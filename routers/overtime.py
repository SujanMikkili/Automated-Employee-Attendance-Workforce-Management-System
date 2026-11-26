from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from models import Employee, Attendance, AuditLog, OvertimePrompt
from routers.auth import get_current_employee, require_roles
from services.jobs import get_settings as get_company, company_tz, finalize_employee_day
from services.notifications import notify
from services.overtime import (run_cycle, confirm_overtime, status_for, get_overtime_settings, fmt)

router = APIRouter(prefix="/overtime", tags=["Overtime"])
admin_router = APIRouter(prefix="/admin", tags=["Overtime Review"])
admin_only = require_roles("SUPER_ADMIN")


# ---------- employee ----------
@router.get("/status")
def my_status(db: Session = Depends(get_db), user: Employee = Depends(get_current_employee)):
    """Progress towards the required duration and the state of the overtime question."""
    return status_for(db, user)


@router.post("/confirm")
def confirm(db: Session = Depends(get_db), user: Employee = Depends(get_current_employee)):
    """'Yes, I am still working overtime': keep the attendance open."""
    pr = confirm_overtime(db, user)
    return {"message": "Overtime confirmed. Your attendance stays open until you check out.", "state": pr.state}


# ---------- settings ----------
class OvertimeSettingsIn(BaseModel):
    enabled: bool
    reminder_interval_minutes: int = Field(ge=1, le=240)
    max_reminders: int = Field(ge=0, le=20)
    overtime_reminder_interval_minutes: int = Field(ge=15, le=720)


def settings_out(s):
    return {"enabled": s.enabled, "reminder_interval_minutes": s.reminder_interval_minutes,
            "max_reminders": s.max_reminders, "overtime_reminder_interval_minutes": s.overtime_reminder_interval_minutes}


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), _: Employee = Depends(get_current_employee)):
    s = get_overtime_settings(db)
    db.commit()
    return settings_out(s)


@router.put("/settings")
def put_settings(body: OvertimeSettingsIn, db: Session = Depends(get_db), admin: Employee = Depends(admin_only)):
    s = get_overtime_settings(db)
    old = str(settings_out(s))
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    db.add(AuditLog(actor_employee_id=admin.id, action="OVERTIME_SETTINGS_CHANGED", entity_type="COMPANY_SETTINGS",
                    old_values=old, new_values=str(settings_out(s))))
    db.commit()
    return settings_out(s)


# ---------- super admin: run now + review queue ----------
@admin_router.post("/jobs/overtime-cycle")
def run_now(db: Session = Depends(get_db), _: Employee = Depends(admin_only)):
    return run_cycle(db)


def prompt_out(pr, att, emp):
    return {"id": pr.id, "attendance_id": att.id, "employee_id": emp.id, "employee": f"{emp.first_name} {emp.last_name}",
            "employee_code": emp.employee_code, "work_date": att.work_date, "check_in_at": att.check_in_at,
            "provisional_check_out_at": pr.closed_at, "required_minutes": pr.required_minutes,
            "worked_minutes": att.worked_minutes, "reminders_sent": pr.reminders_sent, "auto_closed_at": pr.auto_closed_at,
            "reviewed_at": pr.reviewed_at, "review_note": pr.review_note}


@admin_router.get("/auto-closed")
def auto_closed(show: Literal["pending", "reviewed", "all"] = "pending", db: Session = Depends(get_db),
                _: Employee = Depends(admin_only)):
    q = (db.query(OvertimePrompt, Attendance, Employee).join(Attendance, Attendance.id == OvertimePrompt.attendance_id)
         .join(Employee, Employee.id == OvertimePrompt.employee_id).filter(OvertimePrompt.state == "AUTO_CLOSED"))
    if show == "pending":
        q = q.filter(OvertimePrompt.reviewed_at.is_(None))
    elif show == "reviewed":
        q = q.filter(OvertimePrompt.reviewed_at.isnot(None))
    return [prompt_out(*r) for r in q.order_by(OvertimePrompt.id.desc()).limit(200).all()]


class ReviewBody(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


@admin_router.post("/auto-closed/{prompt_id}/confirm")
def confirm_provisional(prompt_id: int, body: ReviewBody, db: Session = Depends(get_db),
                        admin: Employee = Depends(admin_only)):
    """Accept the provisional closing time as correct (to change the times use Attendance Corrections)."""
    pr = db.query(OvertimePrompt).filter(OvertimePrompt.id == prompt_id, OvertimePrompt.state == "AUTO_CLOSED"
                                         ).with_for_update().first()
    if not pr:
        raise HTTPException(404, "Auto-closed record not found")
    if pr.reviewed_at:
        raise HTTPException(400, "This record was already reviewed")
    att = db.get(Attendance, pr.attendance_id)
    emp = db.get(Employee, pr.employee_id)
    company = get_company(db)
    att.status, att.is_finalized = "COMPLETED", False
    att.notes = ((att.notes + " | ") if att.notes else "") + f"Provisional close confirmed by {admin.first_name} {admin.last_name}"
    pr.reviewed_by, pr.reviewed_at, pr.review_note = admin.id, datetime.now(company_tz(company)), body.note
    db.add(AuditLog(actor_employee_id=admin.id, action="AUTO_CLOSE_CONFIRMED", entity_type="ATTENDANCE", entity_id=att.id,
                    reason=body.note))
    notify(db, emp.id, "AUTO_CLOSE_REVIEWED", "Attendance confirmed",
           f"Your attendance for {att.work_date} was reviewed and confirmed ({fmt(att.worked_minutes)} worked).",
           attendance_id=att.id)
    db.flush()
    if att.work_date < datetime.now(company_tz(company)).date():
        finalize_employee_day(db, emp, att.work_date, company, force=True)
    db.commit()
    return {"message": "Provisional closing time confirmed"}
