from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Employee, LeaveBalance
from routers.auth import get_current_employee

router = APIRouter(prefix="/leaves", tags=["Leave Management"])


@router.get("/my-balances")
def my_balances(year: int | None = None, db: Session = Depends(get_db),
                user: Employee = Depends(get_current_employee)):
    rows = (db.query(LeaveBalance)
            .filter(LeaveBalance.employee_id == user.id, LeaveBalance.year == (year or date.today().year))
            .order_by(LeaveBalance.leave_type).all())
    return [{"leave_type": b.leave_type, "year": b.year, "allocated_days": float(b.allocated_days),
             "used_days": float(b.used_days), "remaining_days": float(b.allocated_days - b.used_days)}
            for b in rows]
