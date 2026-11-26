from datetime import datetime
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from database import get_db
from models import Employee, LeaveBalance, AuditLog
from routers.auth import require_roles

router = APIRouter(prefix="/admin", tags=["Admin Extras"])
admin_only = require_roles("SUPER_ADMIN")


# ---------- Employee list ----------
@router.get("/employees")
def list_employees(q: str | None = None,
                   role: Literal["EMPLOYEE", "MANAGER", "SUPER_ADMIN"] | None = None,
                   is_active: bool | None = None,
                   limit: int = Query(100, ge=1, le=500),
                   offset: int = Query(0, ge=0),
                   db: Session = Depends(get_db),
                   _: Employee = Depends(admin_only)):
    query = db.query(Employee)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(Employee.first_name.ilike(like), Employee.last_name.ilike(like),
                                 Employee.email.ilike(like), Employee.employee_code.ilike(like)))
    if role:
        query = query.filter(Employee.role == role)
    if is_active is not None:
        query = query.filter(Employee.is_active.is_(is_active))
    rows = query.order_by(Employee.id).offset(offset).limit(limit).all()
    return [{"id": e.id, "employee_code": e.employee_code, "first_name": e.first_name,
             "last_name": e.last_name, "email": e.email, "role": e.role,
             "department": e.department, "job_title": e.job_title, "shift_id": e.shift_id,
             "manager_id": e.manager_id, "is_active": e.is_active} for e in rows]


# ---------- Leave balances ----------
class BalanceUpsert(BaseModel):
    employee_id: int
    leave_type: Literal["PAID", "SICK", "CASUAL", "EARNED"]
    year: int = Field(ge=2000, le=2100)
    allocated_days: Decimal = Field(ge=0, le=365)


def balance_out(b: LeaveBalance):
    return {"id": b.id, "employee_id": b.employee_id, "leave_type": b.leave_type, "year": b.year,
            "allocated_days": float(b.allocated_days), "used_days": float(b.used_days),
            "remaining_days": float(b.allocated_days - b.used_days)}


@router.get("/leave-balances")
def get_balances(employee_id: int, year: int | None = None,
                 db: Session = Depends(get_db), _: Employee = Depends(admin_only)):
    query = db.query(LeaveBalance).filter(LeaveBalance.employee_id == employee_id)
    if year:
        query = query.filter(LeaveBalance.year == year)
    return [balance_out(b) for b in query.order_by(LeaveBalance.year.desc(), LeaveBalance.leave_type).all()]


@router.put("/leave-balances")
def upsert_balance(payload: BalanceUpsert, db: Session = Depends(get_db),
                   admin: Employee = Depends(admin_only)):
    if not db.query(Employee).filter(Employee.id == payload.employee_id).first():
        raise HTTPException(404, "Employee not found")
    row = db.query(LeaveBalance).filter(LeaveBalance.employee_id == payload.employee_id,
                                        LeaveBalance.leave_type == payload.leave_type,
                                        LeaveBalance.year == payload.year).with_for_update().first()
    if row:
        if payload.allocated_days < row.used_days:
            raise HTTPException(400, f"Allocation cannot be below the {row.used_days} days already used")
        old = f"allocated_days={row.allocated_days}"
        row.allocated_days = payload.allocated_days
    else:
        old = None
        row = LeaveBalance(employee_id=payload.employee_id, leave_type=payload.leave_type,
                           year=payload.year, allocated_days=payload.allocated_days, used_days=0)
        db.add(row)
    db.flush()
    db.add(AuditLog(actor_employee_id=admin.id, action="LEAVE_BALANCE_SET", entity_type="LEAVE_BALANCE",
                    entity_id=row.id, old_values=old, new_values=f"allocated_days={payload.allocated_days}"))
    db.commit()
    db.refresh(row)
    return balance_out(row)


# ---------- Audit log ----------
@router.get("/audit-logs")
def audit_logs(entity_type: str | None = None, limit: int = Query(100, ge=1, le=500),
               db: Session = Depends(get_db), _: Employee = Depends(admin_only)):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type.upper())
    rows = query.order_by(AuditLog.id.desc()).limit(limit).all()
    return [{"id": a.id, "actor_employee_id": a.actor_employee_id, "action": a.action,
             "entity_type": a.entity_type, "entity_id": a.entity_id, "old_values": a.old_values,
             "new_values": a.new_values, "reason": a.reason, "created_at": a.created_at} for a in rows]
