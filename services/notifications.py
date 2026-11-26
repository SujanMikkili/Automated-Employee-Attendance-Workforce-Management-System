from sqlalchemy import func
from models import Notification


def notify(db, employee_id, kind, title, message, attendance_id=None, request_id=None, requires_action=False):
    """Queue an in-app notification (the caller commits)."""
    db.add(Notification(employee_id=employee_id, kind=kind, title=title, message=message,
                        attendance_id=attendance_id, request_id=request_id, requires_action=requires_action))


def resolve_actions(db, employee_id, attendance_id):
    """Mark the 'please respond' notifications of an attendance day as handled."""
    db.query(Notification).filter(Notification.employee_id == employee_id,
                                  Notification.attendance_id == attendance_id,
                                  Notification.requires_action.is_(True)
                                  ).update({"requires_action": False, "is_read": True, "read_at": func.now()},
                                           synchronize_session=False)
