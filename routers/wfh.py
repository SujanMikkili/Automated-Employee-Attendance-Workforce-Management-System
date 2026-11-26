from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from models import Employee, Request, AuditLog
from routers.auth import get_current_employee, require_roles
from services.approvals import resolve_approver
from services.notifications import notify
from routers.attendance import get_company_settings, get_company_now
from routers.leaves import calculate_working_days

router = APIRouter(prefix="/wfh", tags=["Work From Home"])
reviewer_dep = require_roles("MANAGER", "SUPER_ADMIN")


class WFHCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field(min_length=1, max_length=2000)


class WFHReview(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


def out(r: Request):
    return {"id": r.id, "employee_id": r.employee_id, "start_date": r.start_date, "end_date": r.end_date,
            "duration_days": float(r.duration_days or 0), "reason": r.reason, "status": r.status,
            "approver_id": r.approver_id, "reviewed_by": r.reviewed_by, "reviewed_at": r.reviewed_at,
            "reviewer_comment": r.reviewer_comment, "created_at": r.created_at}


def audit(db, actor, action, rid, reason=None):
    db.add(AuditLog(actor_employee_id=actor, action=action, entity_type="REQUEST", entity_id=rid, reason=reason))


@router.post("/", status_code=201)
def create_wfh(payload: WFHCreate, db: Session = Depends(get_db),
               user: Employee = Depends(get_current_employee)):
    if user.role == "SUPER_ADMIN":
        raise HTTPException(403, "Use an employee or manager account to request WFH")
    s = get_company_settings(db)
    now = get_company_now(s)
    if s and not s.wfh_enabled:
        raise HTTPException(400, "Work from home is currently disabled")
    if payload.end_date < payload.start_date:
        raise HTTPException(400, "End date cannot be before start date")
    if payload.start_date < now.date():
        raise HTTPException(400, "WFH cannot start in the past")
    if s and s.wfh_advance_notice_hours:
        start_at = datetime.combine(payload.start_date, datetime.min.time(), tzinfo=now.tzinfo)
        if start_at - now < timedelta(hours=s.wfh_advance_notice_hours):
            raise HTTPException(400, f"WFH must be requested at least {s.wfh_advance_notice_hours} hours in advance")
    approver = resolve_approver(db, user)   # employee -> manager, manager -> Super Admin
    days = calculate_working_days(db, payload.start_date, payload.end_date)
    active = ["PENDING", "APPROVED"]
    if db.query(Request).filter(Request.employee_id == user.id, Request.request_type == "WFH",
                                Request.status.in_(active), Request.start_date <= payload.end_date,
                                Request.end_date >= payload.start_date).first():
        raise HTTPException(409, "You already have a WFH request overlapping these dates")
    if s:
        m0 = payload.start_date.replace(day=1)
        m1 = (m0 + timedelta(days=32)).replace(day=1)
        used = sum(float(r.duration_days or 0) for r in db.query(Request).filter(
            Request.employee_id == user.id, Request.request_type == "WFH", Request.status.in_(active),
            Request.start_date >= m0, Request.start_date < m1).all())
        if used + days > s.wfh_monthly_limit_days:
            raise HTTPException(400, f"Monthly WFH limit of {s.wfh_monthly_limit_days} days would be exceeded "
                                     f"({used:g} already requested)")
    auto = bool(s and not s.wfh_approval_required)
    req = Request(employee_id=user.id, request_type="WFH", start_date=payload.start_date,
                  end_date=payload.end_date, duration_days=Decimal(days), reason=payload.reason.strip(),
                  status="APPROVED" if auto else "PENDING", approver_id=approver.id,
                  reviewed_at=now if auto else None,
                  reviewer_comment="Auto-approved by company policy" if auto else None)
    db.add(req)
    db.flush()
    audit(db, user.id, "WFH_CREATED", req.id)
    notify(db, approver.id, "WFH_REQUEST", "New work-from-home request",
           f"{user.first_name} {user.last_name} requested WFH from {req.start_date} to {req.end_date}.", request_id=req.id)
    db.commit()
    db.refresh(req)
    return out(req)


@router.get("/my-requests")
def my_requests(db: Session = Depends(get_db), user: Employee = Depends(get_current_employee)):
    rows = (db.query(Request).filter(Request.employee_id == user.id, Request.request_type == "WFH")
            .order_by(Request.created_at.desc()).all())
    return [out(r) for r in rows]


@router.delete("/my-requests/{request_id}")
def cancel_wfh(request_id: int, db: Session = Depends(get_db),
               user: Employee = Depends(get_current_employee)):
    r = db.query(Request).filter(Request.id == request_id, Request.employee_id == user.id,
                                 Request.request_type == "WFH").first()
    if not r:
        raise HTTPException(404, "WFH request not found")
    today = get_company_now(get_company_settings(db)).date()
    if not (r.status == "PENDING" or (r.status == "APPROVED" and r.start_date > today)):
        raise HTTPException(400, "Only pending or future approved requests can be cancelled")
    r.status = "CANCELLED"
    r.reviewer_comment = "Cancelled by employee"
    audit(db, user.id, "WFH_CANCELLED", r.id)
    db.commit()
    db.refresh(r)
    return out(r)


@router.get("/manager/pending")
def pending(db: Session = Depends(get_db), me: Employee = Depends(reviewer_dep)):
    q = db.query(Request).filter(Request.request_type == "WFH", Request.status == "PENDING")
    if me.role != "SUPER_ADMIN":
        q = q.filter(Request.approver_id == me.id)
    return [out(r) for r in q.order_by(Request.created_at).all()]


def review(request_id, decision, payload, db, me):
    q = db.query(Request).filter(Request.id == request_id, Request.request_type == "WFH")
    if me.role != "SUPER_ADMIN":
        q = q.filter(Request.approver_id == me.id)
    r = q.with_for_update().first()
    if not r:
        raise HTTPException(404, "Request not found or not assigned to you")
    if r.employee_id == me.id:
        raise HTTPException(403, "You cannot review your own request")
    if r.status != "PENDING":
        raise HTTPException(400, "Only pending requests can be reviewed")
    r.status = decision
    r.reviewed_by = me.id
    r.reviewed_at = datetime.now().astimezone()
    r.reviewer_comment = payload.comment
    audit(db, me.id, f"WFH_{decision}", r.id, payload.comment)
    notify(db, r.employee_id, "WFH_DECISION", f"WFH {decision.lower()}",
           f"Your WFH request for {r.start_date} to {r.end_date} was {decision.lower()}.", request_id=r.id)
    db.commit()
    db.refresh(r)
    return out(r)


@router.post("/manager/requests/{request_id}/approve")
def approve(request_id: int, payload: WFHReview, db: Session = Depends(get_db), me: Employee = Depends(reviewer_dep)):
    return review(request_id, "APPROVED", payload, db, me)


@router.post("/manager/requests/{request_id}/reject")
def reject(request_id: int, payload: WFHReview, db: Session = Depends(get_db), me: Employee = Depends(reviewer_dep)):
    return review(request_id, "REJECTED", payload, db, me)
