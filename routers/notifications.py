from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db
from models import Employee, Notification
from routers.auth import get_current_employee

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def out(n: Notification):
    return {"id": n.id, "kind": n.kind, "title": n.title, "message": n.message, "attendance_id": n.attendance_id,
            "request_id": n.request_id, "requires_action": n.requires_action, "is_read": n.is_read,
            "created_at": n.created_at}


@router.get("/")
def my_notifications(limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db),
                     user: Employee = Depends(get_current_employee)):
    q = db.query(Notification).filter(Notification.employee_id == user.id)
    unread = q.filter(Notification.is_read.is_(False)).count()
    rows = q.order_by(Notification.id.desc()).limit(limit).all()
    return {"unread": unread, "items": [out(n) for n in rows]}


@router.post("/read-all")
def read_all(db: Session = Depends(get_db), user: Employee = Depends(get_current_employee)):
    db.query(Notification).filter(Notification.employee_id == user.id, Notification.is_read.is_(False)
                                  ).update({"is_read": True, "read_at": func.now()}, synchronize_session=False)
    db.commit()
    return {"message": "All notifications marked as read"}


@router.post("/{notification_id}/read")
def read_one(notification_id: int, db: Session = Depends(get_db), user: Employee = Depends(get_current_employee)):
    n = db.query(Notification).filter(Notification.id == notification_id, Notification.employee_id == user.id).first()
    if not n:
        raise HTTPException(404, "Notification not found")
    n.is_read, n.read_at = True, func.now()
    db.commit()
    return {"message": "Marked as read"}
