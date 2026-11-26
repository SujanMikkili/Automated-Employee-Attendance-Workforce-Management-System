from fastapi import HTTPException
from models import Employee


def resolve_approver(db, employee: Employee) -> Employee:
    """Who must approve this person's leave / WFH request.

    EMPLOYEE -> their assigned manager (or the Super Admin if assigned directly)
    MANAGER  -> the Super Admin (their assigned boss if that is a Super Admin, otherwise the first active one)
    """
    if employee.role == "MANAGER":
        boss = None
        if employee.manager_id:
            boss = db.query(Employee).filter(Employee.id == employee.manager_id, Employee.is_active.is_(True),
                                             Employee.role == "SUPER_ADMIN").first()
        if not boss:
            boss = (db.query(Employee).filter(Employee.role == "SUPER_ADMIN", Employee.is_active.is_(True))
                    .order_by(Employee.id).first())
        if not boss:
            raise HTTPException(400, "No active Super Admin is available to approve your request")
        return boss
    if not employee.manager_id:
        raise HTTPException(400, "You must have an assigned manager before applying")
    boss = db.query(Employee).filter(Employee.id == employee.manager_id, Employee.is_active.is_(True),
                                     Employee.role.in_(["MANAGER", "SUPER_ADMIN"])).first()
    if not boss:
        raise HTTPException(400, "Your assigned manager is unavailable")
    return boss
