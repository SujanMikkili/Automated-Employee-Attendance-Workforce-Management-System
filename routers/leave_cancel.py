from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Employee, LeaveBalance, DailyAttendanceStatus, CompanySetting
from routers.auth import get_current_employee
from routers.leaves import LeaveResponse, require_active_employee, get_employee_request, write_audit_log

router = APIRouter(prefix="/leaves", tags=["Leave Management"])


@router.post("/my-requests/{request_id}/cancel", response_model=LeaveResponse)
def cancel_approved_leave(request_id: int, db: Session = Depends(get_db),
                          user: Employee = Depends(get_current_employee)):
    """Cancel an APPROVED leave that has not started yet; the balance is restored."""
    employee = require_active_employee(user, db)
    settings = db.query(CompanySetting).first()
    if settings and not settings.allow_leave_cancellation:
        raise HTTPException(403, "Leave cancellation is disabled by company policy")
    req = get_employee_request(db, request_id, employee.id)
    if req.status != "APPROVED":
        raise HTTPException(400, "Only approved requests can be cancelled here (pending ones can be withdrawn)")
    if req.start_date <= date.today():
        raise HTTPException(400, "Leave that has already started cannot be cancelled")
    if req.leave_type != "UNPAID":
        bal = db.query(LeaveBalance).filter(LeaveBalance.employee_id == req.employee_id,
                                            LeaveBalance.leave_type == req.leave_type,
                                            LeaveBalance.year == req.start_date.year).with_for_update().first()
        if bal:
            bal.used_days = max(Decimal(0), Decimal(bal.used_days) - Decimal(req.duration_days or 0))
    db.query(DailyAttendanceStatus).filter(
        DailyAttendanceStatus.employee_id == req.employee_id,
        DailyAttendanceStatus.work_date >= req.start_date, DailyAttendanceStatus.work_date <= req.end_date,
        DailyAttendanceStatus.status == "ON_LEAVE", DailyAttendanceStatus.is_finalized.is_(False)
    ).delete(synchronize_session=False)
    req.status = "CANCELLED"
    req.reviewer_comment = "Cancelled by employee after approval"
    write_audit_log(db, employee.id, "LEAVE_CANCELLED_AFTER_APPROVAL", req.id)
    db.commit()
    db.refresh(req)
    return req
