import datetime as dt
import pytest
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal
from models import (Employee, Attendance, AttendanceSession, AttendanceConflict, DailyAttendanceStatus,
                    Request, LeaveBalance, LeaveAccrualHistory)
from routers.auth import get_password_hash

client = TestClient(app)
db = SessionLocal()
S = {}  # shared state between ordered tests


def hdr(email, pw="password1"):
    r = client.post("/auth/token", data={"username": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def weekday_before(n):
    d = dt.date.today() - dt.timedelta(days=n)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def next_weekday(n):
    d = dt.date.today() + dt.timedelta(days=n)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def test_setup():
    db.add(Employee(employee_code="A1", first_name="Ad", last_name="Min", email="admin@gmail.com",
                    password_hash=get_password_hash("password1"), role="SUPER_ADMIN"))
    db.commit()
    S["A"] = hdr("admin@gmail.com")
    A = S["A"]
    assert client.post("/company-settings/", headers=A, data={"wfh_advance_notice_hours": 0}).status_code == 201
    for n, a, b in (("Morning Shift", "09:00", "18:00"), ("Evening Shift", "14:00", "23:00")):
        assert client.post("/shifts/", headers=A, data={"name": n, "start_time": a, "end_time": b,
                           "required_work_minutes": 480, "is_overnight": "false"}).status_code == 201
    base = {"password": "password1", "department": "Data and AI", "job_title": "x", "shift_name": "Morning Shift"}
    people = [("M1", "Man", "ager", "m@gmail.com", "MANAGER", None), ("E1", "Emp", "one", "e@gmail.com", "EMPLOYEE", 2),
              ("E2", "Emp", "two", "e2@gmail.com", "EMPLOYEE", 2), ("E3", "Emp", "three", "e3@gmail.com", "EMPLOYEE", 2),
              ("E4", "Emp", "four", "e4@gmail.com", "EMPLOYEE", 2)]
    for code, f, l, em, role, mgr in people:
        data = {**base, "employee_code": code, "first_name": f, "last_name": l, "email": em, "role": role}
        if mgr:
            data["manager_id"] = mgr
        r = client.post("/admin/employees", headers=A, data=data)
        assert r.status_code == 201, r.text
    S["M"], S["E"] = hdr("m@gmail.com"), hdr("e@gmail.com")
    assert client.get("/admin/employees?q=emp", headers=A).status_code == 200
    assert client.get("/admin/employees", headers=S["E"]).status_code == 403


def test_leave_balance_and_approval():
    A, E, M = S["A"], S["E"], S["M"]
    y = dt.date.today().year
    assert client.put("/admin/leave-balances", headers=A, json={"employee_id": 3, "leave_type": "PAID", "year": y,
                                                               "allocated_days": 10}).status_code == 200
    d = next_weekday(10)
    r = client.post("/leaves/", headers=E, json={"leave_type": "PAID", "start_date": str(d), "end_date": str(d), "reason": "r"})
    assert r.status_code == 201, r.text
    assert client.post(f"/leaves/manager/requests/{r.json()['id']}/approve", headers=M, json={}).status_code == 200
    assert client.get("/leaves/my-balances", headers=E).json()[0]["used_days"] == 1.0


def test_half_day_and_cancel_after_approval():
    A, E, M = S["A"], S["E"], S["M"]
    d = next_weekday(12)
    r = client.post("/leaves/", headers=E, json={"leave_type": "PAID", "start_date": str(d), "end_date": str(d),
                                                 "reason": "dentist", "half_day": True})
    assert r.status_code == 201 and r.json()["duration_days"] in (0.5, "0.5"), r.text
    rid = r.json()["id"]
    bad = client.post("/leaves/", headers=E, json={"leave_type": "PAID", "start_date": str(d),
                                                   "end_date": str(d + dt.timedelta(days=1)), "reason": "x", "half_day": True})
    assert bad.status_code == 400
    assert client.post(f"/leaves/manager/requests/{rid}/approve", headers=M, json={}).status_code == 200
    assert client.get("/leaves/my-balances", headers=E).json()[0]["used_days"] == 1.5
    r = client.post(f"/leaves/my-requests/{rid}/cancel", headers=E)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED", r.text
    assert client.get("/leaves/my-balances", headers=E).json()[0]["used_days"] == 1.0


def test_auto_approval_policy_and_cancellation_policy():
    A, E = S["A"], S["E"]
    assert client.put("/company-settings/", headers=A, data={"leave_approval_required": "false"}).status_code == 200
    d = next_weekday(14)
    r = client.post("/leaves/", headers=E, json={"leave_type": "PAID", "start_date": str(d), "end_date": str(d), "reason": "auto"})
    assert r.status_code == 201 and r.json()["status"] == "APPROVED", r.text
    assert client.put("/company-settings/", headers=A, data={"allow_leave_cancellation": "false"}).status_code == 200
    assert client.post(f"/leaves/my-requests/{r.json()['id']}/cancel", headers=E).status_code == 403
    client.put("/company-settings/", headers=A, data={"allow_leave_cancellation": "true", "leave_approval_required": "true"})


def test_wfh_flow():
    E, M = S["E"], S["M"]
    d = next_weekday(20)
    r = client.post("/wfh/", headers=E, json={"start_date": str(d), "end_date": str(d), "reason": "w"})
    assert r.status_code == 201, r.text
    assert client.post(f"/wfh/manager/requests/{r.json()['id']}/approve", headers=M, json={}).status_code == 200
    assert client.post("/wfh/", headers=E, json={"start_date": str(d), "end_date": str(d), "reason": "w"}).status_code == 409


def test_check_in_out_and_history():
    E, M = S["E"], S["M"]
    assert client.post("/attendance/check-in", headers=E).status_code == 201
    assert client.get("/attendance/today", headers=E).json()["checked_in"] is True
    assert client.post("/attendance/check-out", headers=E).status_code == 200
    assert len(client.get("/attendance/my-records", headers=E).json()[0]["sessions"]) == 1
    assert client.get("/attendance/team", headers=M).json()["rows"]
    assert client.get("/attendance/team", headers=E).status_code == 403


def test_admin_attendance_correction_and_finalize():
    A, E = S["A"], S["E"]
    d = weekday_before(3)
    r = client.post("/admin/attendance/correct", headers=A, json={"employee_id": 3, "work_date": str(d), "check_in": "09:00",
                                                                  "check_out": "18:00", "reason": "forgot to punch"})
    assert r.status_code == 200 and r.json()["daily_status"] == "PRESENT", r.text
    db.query(Employee).update({"date_of_joining": d - dt.timedelta(days=60)}); db.commit()
    # E2 (id 4): open session, never checked out
    att = Attendance(employee_id=4, shift_id=1, work_date=d, check_in_at=dt.datetime.combine(d, dt.time(9, 0), tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30))),
                     status="IN_PROGRESS")
    db.add(att); db.flush()
    db.add(AttendanceSession(attendance_id=att.id, check_in_at=att.check_in_at)); db.commit()
    # E3 (id 5): approved full-day leave on d
    db.add(Request(employee_id=5, request_type="LEAVE", leave_type="PAID", start_date=d, end_date=d, duration_days=1,
                   status="APPROVED", approver_id=2)); db.commit()
    assert client.post("/admin/jobs/finalize-day", headers=A, json={"work_date": str(dt.date.today())}).status_code == 400
    r = client.post("/admin/jobs/finalize-day", headers=A, json={"work_date": str(d)})
    assert r.status_code == 200, r.text
    db.expire_all()
    st = {x.employee_id: x.status for x in db.query(DailyAttendanceStatus).filter_by(work_date=d).all()}
    assert st[3] == "PRESENT" and st[4] == "INCOMPLETE" and st[5] == "ON_LEAVE" and st[6] == "ABSENT", st
    assert db.query(AttendanceConflict).filter_by(employee_id=4, conflict_type="MISSING_CHECK_OUT").count() == 1
    again = client.post("/admin/jobs/finalize-day", headers=A, json={"work_date": str(d)}).json()
    assert again["already_finalized"] == again["employees"]
    mine = client.get("/attendance/my-daily", headers=E).json()
    assert any(x["status"] == "PRESENT" for x in mine)


def test_monthly_accrual_is_idempotent():
    A = S["A"]
    t = dt.date.today()
    r1 = client.post("/admin/jobs/accrue-month", headers=A, json={"year": t.year, "month": t.month}).json()
    r2 = client.post("/admin/jobs/accrue-month", headers=A, json={"year": t.year, "month": t.month}).json()
    assert r1["created"] == 5 and r2["created"] == 0 and r2["already_done"] == 5, (r1, r2)
    assert db.query(LeaveAccrualHistory).count() == 5
    assert client.get("/admin/accruals?employee_id=3", headers=A).json()[0]["allocated_days"] == 2.0


def test_conflict_resolution():
    M = S["M"]
    c = client.get("/conflicts/?status=OPEN", headers=M).json()
    assert c, "manager should see the missing check-out conflict of a direct report"
    cid = c[0]["id"]
    assert client.post(f"/conflicts/{cid}/resolve", headers=M, json={"status": "RESOLVED"}).status_code == 400
    assert client.post(f"/conflicts/{cid}/resolve", headers=M, json={"status": "RESOLVED", "reason": "ok"}).status_code == 200


def test_account_tools_and_holiday_route():
    A = S["A"]
    assert client.post("/employees/1/reset-password", headers=A).status_code == 404
    assert client.post("/admin/employees/3/reset-password", headers=A, json={"new_password": "short"}).status_code == 400
    assert client.post("/admin/employees/3/reset-password", headers=A, json={"new_password": "newpass123"}).status_code == 200
    hdr("e@gmail.com", "newpass123")
    assert client.patch("/admin/employees/3/account", headers=A, json={"email": "e.new@gmail.com"}).status_code == 200
    assert client.patch("/admin/employees/3/account", headers=A, json={"email": "m@gmail.com"}).status_code == 400
    h = client.post("/holidays/", headers=A, data={"name": "H", "holiday_date": str(next_weekday(60)), "is_paid": "true", "description": "d"})
    assert client.put(f"/holidays/{h.json()['id']}", headers=A, data={"name": "H2"}).status_code == 200


def test_delete_employee_and_guards():
    A = S["A"]
    assert client.delete("/admin/employees/2", headers=A).status_code == 400   # manager with reports
    assert client.delete("/admin/employees/1", headers=A).status_code == 400   # super admin
    assert client.delete("/admin/employees/5", headers=A).status_code == 200   # E3 has leave + daily rows
    assert client.get("/admin/employees/5", headers=A).status_code == 404
    assert client.get("/admin/audit-logs?limit=5", headers=A).json()[0]["action"] == "EMPLOYEE_DELETED"
