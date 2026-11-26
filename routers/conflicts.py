from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from models import Employee, AttendanceConflict, AuditLog
from routers.auth import get_current_employee, require_roles

router = APIRouter(prefix="/conflicts", tags=["Attendance Conflicts"])
reviewer_dep = require_roles("MANAGER", "SUPER_ADMIN")


class Resolve(BaseModel):
    status: Literal["UNDER_REVIEW", "RESOLVED", "DISMISSED"]
    reason: str | None = Field(default=None, max_length=2000)


def out(c: AttendanceConflict):
    return {"id": c.id, "employee_id": c.employee_id, "attendance_id": c.attendance_id,
            "request_id": c.request_id, "conflict_type": c.conflict_type, "status": c.status,
            "description": c.description, "resolved_by": c.resolved_by,
            "resolution_reason": c.resolution_reason, "resolved_at": c.resolved_at, "created_at": c.created_at}


@router.get("/my")
def my_conflicts(db: Session = Depends(get_db), user: Employee = Depends(get_current_employee)):
    rows = db.query(AttendanceConflict).filter(AttendanceConflict.employee_id == user.id) \
        .order_by(AttendanceConflict.id.desc()).all()
    return [out(c) for c in rows]


@router.get("/")
def list_conflicts(status: Literal["OPEN", "UNDER_REVIEW", "RESOLVED", "DISMISSED"] | None = None,
                   db: Session = Depends(get_db), me: Employee = Depends(reviewer_dep)):
    q = db.query(AttendanceConflict)
    if me.role == "MANAGER":
        ids = [e.id for e in db.query(Employee.id).filter(Employee.manager_id == me.id).all()]
        q = q.filter(AttendanceConflict.employee_id.in_(ids or [0]))
    if status:
        q = q.filter(AttendanceConflict.status == status)
    return [out(c) for c in q.order_by(AttendanceConflict.id.desc()).limit(200).all()]


@router.post("/{conflict_id}/resolve")
def resolve(conflict_id: int, payload: Resolve, db: Session = Depends(get_db),
            me: Employee = Depends(reviewer_dep)):
    c = db.query(AttendanceConflict).filter(AttendanceConflict.id == conflict_id).with_for_update().first()
    if not c:
        raise HTTPException(404, "Conflict not found")
    if me.role == "MANAGER":
        owner = db.query(Employee).filter(Employee.id == c.employee_id).first()
        if not owner or owner.manager_id != me.id:
            raise HTTPException(403, "This conflict belongs to someone outside your team")
    if c.status in ("RESOLVED", "DISMISSED"):
        raise HTTPException(400, "This conflict is already closed")
    closing = payload.status in ("RESOLVED", "DISMISSED")
    if closing and not (payload.reason and payload.reason.strip()):
        raise HTTPException(400, "A reason is required to resolve or dismiss a conflict")
    old = f"status={c.status}"
    c.status = payload.status
    if closing:
        c.resolved_by, c.resolved_at, c.resolution_reason = me.id, datetime.now().astimezone(), payload.reason.strip()
    db.add(AuditLog(actor_employee_id=me.id, action=f"CONFLICT_{payload.status}", entity_type="CONFLICT",
                    entity_id=c.id, old_values=old, new_values=f"status={c.status}", reason=payload.reason))
    db.commit()
    db.refresh(c)
    return out(c)
