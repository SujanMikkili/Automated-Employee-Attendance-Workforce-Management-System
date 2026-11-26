from collections import defaultdict
from datetime import timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import AttendanceConflict, Employee, Holiday, LeaveBalance, Request, Shift, OvertimePrompt
from routers.attendance import get_company_settings, get_company_now, current_work_date, get_shift_datetimes
from routers.auth import get_current_employee, require_roles
from services.stats import build_days, month_start, on_time_streak, summarize

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
ACTIVE = ("WORKING", "FINISHED")


def trend(rows, today):
    """Last six months (this one included) of the same totals."""
    out = []
    for back in range(5, -1, -1):
        first = month_start(today, back)
        last = today if back == 0 else month_start(today, back - 1) - timedelta(days=1)
        s = summarize([x for x in rows if first <= x["date"] <= last], today)
        out.append({"month": first.strftime("%Y-%m"), "label": first.strftime("%b"),
                    "worked_minutes": s["total_worked_minutes"], "required_minutes": s["total_required_minutes"],
                    "average_worked_minutes": s["average_worked_minutes"], "overtime_minutes": s["overtime_minutes"],
                    "attendance_rate": s["attendance_rate"], "late_days": s["late_days"],
                    "present_days": s["present_days"], "working_days": s["working_days"]})
    return out


def upcoming_holidays(db, today):
    return [{"name": h.name, "date": h.holiday_date, "is_paid": h.is_paid, "description": h.description}
            for h in db.query(Holiday).filter(Holiday.holiday_date >= today).order_by(Holiday.holiday_date).limit(4)]


# =====================================================================================================
# Personal dashboard (every role)
# =====================================================================================================
@router.get("/me")
def my_dashboard(db: Session = Depends(get_db), user: Employee = Depends(get_current_employee)):
    settings = get_company_settings(db)
    now = get_company_now(settings)
    today = now.date()
    cur0, prev0 = month_start(today), month_start(today, 1)
    rows = build_days(db, [user], month_start(today, 5), today, now, settings)[user.id]
    work_date = current_work_date(db, user, now)
    today_row = next((x for x in rows if x["date"] == work_date), rows[-1])
    cur = summarize([x for x in rows if x["date"] >= cur0], today)
    prev = summarize([x for x in rows if prev0 <= x["date"] < cur0], today)
    shift = db.get(Shift, user.shift_id) if user.shift_id else None
    finish = None
    if today_row["live"] and today_row["worked_minutes"] < today_row["required_minutes"]:
        finish = now + timedelta(minutes=today_row["required_minutes"] - today_row["worked_minutes"])

    balances = [{"leave_type": b.leave_type, "allocated_days": float(b.allocated_days), "used_days": float(b.used_days),
                 "remaining_days": float(b.allocated_days - b.used_days)}
                for b in db.query(LeaveBalance).filter(LeaveBalance.employee_id == user.id, LeaveBalance.year == today.year)
                .order_by(LeaveBalance.leave_type)]
    mine = db.query(Request).filter(Request.employee_id == user.id)
    upcoming = (mine.filter(Request.end_date >= today, Request.status.in_(["PENDING", "APPROVED"]))
                .order_by(Request.start_date).limit(6).all())
    recent = mine.order_by(Request.id.desc()).limit(6).all()
    next_month = month_start(today, -1)
    wfh_used = sum(float(r.duration_days or 0) for r in mine.filter(
        Request.request_type == "WFH", Request.status == "APPROVED", Request.start_date >= cur0,
        Request.start_date < next_month))
    req_out = lambda r: {"id": r.id, "type": r.request_type, "leave_type": r.leave_type, "start_date": r.start_date,
                         "end_date": r.end_date, "days": float(r.duration_days or 0), "status": r.status}
    return {
        "today": {**today_row, "work_date": work_date, "expected_finish_at": finish},
        "shift": {"name": shift.name, "start_time": shift.start_time, "end_time": shift.end_time,
                  "required_minutes": shift.required_work_minutes, "overnight": shift.is_overnight} if shift else None,
        "month": {"label": cur0.strftime("%B %Y"), "start": cur0, "days_in_month": (next_month - cur0).days,
                  "summary": cur, "previous_label": prev0.strftime("%B"), "previous": prev},
        "last_days": [x for x in rows if x["kind"] == "WORKDAY" and (x["date"] < today or x["worked_minutes"] > 0)][-14:],
        "calendar": [x for x in rows if x["date"] >= cur0],
        "trend": trend(rows, today),
        "leave_balances": balances,
        "wfh": {"used_days": wfh_used, "limit_days": settings.wfh_monthly_limit_days if settings else None,
                "pending": mine.filter(Request.request_type == "WFH", Request.status == "PENDING").count()},
        "pending_requests": mine.filter(Request.status == "PENDING").count(),
        "upcoming_requests": [req_out(r) for r in upcoming],
        "recent_requests": [req_out(r) for r in recent],
        "streak_days": on_time_streak(rows, today),
        "holidays": upcoming_holidays(db, today),
    }


# =====================================================================================================
# Team (manager) / company (super admin) dashboard
# =====================================================================================================
@router.get("/team")
def team_dashboard(db: Session = Depends(get_db), user: Employee = Depends(require_roles("MANAGER", "SUPER_ADMIN"))):
    settings = get_company_settings(db)
    now = get_company_now(settings)
    today, tz = now.date(), now.tzinfo
    admin = user.role == "SUPER_ADMIN"
    q = db.query(Employee).filter(Employee.is_active.is_(True), Employee.role != "SUPER_ADMIN")
    if not admin:
        q = q.filter(Employee.manager_id == user.id)
    members = q.order_by(Employee.first_name, Employee.id).all()
    ids = [m.id for m in members] or [0]
    shifts = {s.id: s for s in db.query(Shift).all()}
    cur0, prev0 = month_start(today), month_start(today, 1)
    first = month_start(today, 5)
    by_emp = build_days(db, members, first, today, now, settings)
    name_of = {m.id: f"{m.first_name} {m.last_name}" for m in members}

    # ---------- who is in right now (works for night shifts too) ----------
    people, counts, by_shift, status_of = [], defaultdict(int), defaultdict(lambda: defaultdict(int)), {}
    for m in members:
        rows = by_emp[m.id]
        today_row = rows[-1] if rows else None
        live_row = next((x for x in rows[-2:] if x["live"]), None)
        shift = shifts.get(m.shift_id)
        if live_row:
            status, row = "WORKING", live_row
        elif today_row and today_row["worked_minutes"] > 0:
            status, row = "FINISHED", today_row
        elif today_row and today_row["kind"] == "LEAVE":
            status, row = "ON_LEAVE", today_row
        elif today_row and today_row["kind"] in ("WEEKEND", "HOLIDAY"):
            status, row = "OFF", today_row
        else:
            start = get_shift_datetimes(shift, today, tz)[0] if shift else None
            status, row = ("NOT_STARTED" if start and now < start else "NOT_IN"), today_row
        row = row or {}
        shown = status in ACTIVE
        counts[status] += 1
        by_shift[shift.name if shift else "No shift"][status] += 1
        status_of[m.id] = status
        people.append({"id": m.id, "name": name_of[m.id], "role": m.role, "department": m.department,
                       "shift": shift.name if shift else None, "status": status, "mode": row.get("mode") if shown else None,
                       "check_in_at": row.get("check_in_at") if shown else None,
                       "worked_minutes": row.get("worked_minutes", 0) if shown else 0,
                       "required_minutes": row.get("required_minutes", 0),
                       "late_minutes": row.get("late_minutes", 0) if shown else 0})
    today_block = {
        "date": today, "total": len(members), "working_now": counts["WORKING"], "finished": counts["FINISHED"],
        "not_in": counts["NOT_IN"], "not_started": counts["NOT_STARTED"], "on_leave": counts["ON_LEAVE"], "off": counts["OFF"],
        "expected": counts["WORKING"] + counts["FINISHED"] + counts["NOT_IN"] + counts["NOT_STARTED"],
        "wfh": sum(1 for p in people if p["status"] in ACTIVE and p["mode"] == "WFH"),
        "late": sum(1 for p in people if p["late_minutes"] > 0)}
    shift_list = [{"shift": k, "total": sum(v.values()), **{s: v.get(s, 0) for s in
                   ("WORKING", "FINISHED", "NOT_IN", "NOT_STARTED", "ON_LEAVE", "OFF")}} for k, v in sorted(by_shift.items())]

    # ---------- this month vs last month, leaders, departments ----------
    all_rows = [x for m in members for x in by_emp[m.id]]
    month = summarize([x for x in all_rows if x["date"] >= cur0], today)
    previous = summarize([x for x in all_rows if prev0 <= x["date"] < cur0], today)
    per = {m.id: summarize([x for x in by_emp[m.id] if x["date"] >= cur0], today) for m in members}
    leaders = {
        "overtime": [{"id": i, "name": name_of[i], "minutes": s["overtime_minutes"]} for i, s in
                     sorted(per.items(), key=lambda kv: -kv[1]["overtime_minutes"]) if s["overtime_minutes"] > 0][:5],
        "late": [{"id": i, "name": name_of[i], "days": s["late_days"]} for i, s in
                 sorted(per.items(), key=lambda kv: -kv[1]["late_days"]) if s["late_days"] > 0][:5],
        "low_attendance": [{"id": i, "name": name_of[i], "rate": s["attendance_rate"], "present_days": s["present_days"],
                            "working_days": s["working_days"]} for i, s in
                           sorted((kv for kv in per.items() if kv[1]["working_days"] >= 3 and kv[1]["attendance_rate"] is not None
                                   and kv[1]["attendance_rate"] < 100), key=lambda kv: kv[1]["attendance_rate"])][:5]}
    depts = defaultdict(list)
    for m in members:
        depts[m.department or "No department"].append(m)
    by_department = []
    for dname, ms in sorted(depts.items()):
        s = summarize([x for m in ms for x in by_emp[m.id] if x["date"] >= cur0], today)
        by_department.append({"department": dname, "headcount": len(ms),
                              "present_today": sum(1 for m in ms if status_of[m.id] in ACTIVE),
                              "total_worked_minutes": s["total_worked_minutes"], "average_worked_minutes": s["average_worked_minutes"],
                              "overtime_minutes": s["overtime_minutes"], "attendance_rate": s["attendance_rate"],
                              "late_days": s["late_days"]})

    # ---------- last 14 working days of the whole team ----------
    row_at = {m.id: {x["date"]: x for x in by_emp[m.id]} for m in members}
    hols = {h.holiday_date for h in db.query(Holiday).filter(Holiday.holiday_date >= first, Holiday.holiday_date <= today)}
    dates, d = [], today
    while len(dates) < 14 and d >= first:
        if d.weekday() < 5 and d not in hols:
            dates.append(d)
        d -= timedelta(days=1)
    daily = []
    for d in reversed(dates):
        present = leave = absent = late = worked = 0
        for m in members:
            x = row_at[m.id].get(d)
            if not x:
                continue
            worked += x["worked_minutes"]
            if x["kind"] == "LEAVE":
                leave += 1
            elif x["worked_minutes"] > 0:
                present += 1
                late += 1 if x["late_minutes"] > 0 else 0
            elif x["kind"] == "WORKDAY" and d < today:
                absent += 1
        daily.append({"date": d, "weekday": d.strftime("%a"), "present": present, "on_leave": leave, "absent": absent,
                      "late": late, "total_worked_minutes": worked,
                      "average_worked_minutes": round(worked / present) if present else 0})

    # ---------- things waiting for this person, who is off soon ----------
    pending = {"leave": db.query(Request).filter(Request.request_type == "LEAVE", Request.status == "PENDING",
                                                 Request.approver_id == user.id).count(),
               "wfh": db.query(Request).filter(Request.request_type == "WFH", Request.status == "PENDING",
                                               Request.approver_id == user.id).count(),
               "conflicts": db.query(AttendanceConflict).filter(AttendanceConflict.status.in_(["OPEN", "UNDER_REVIEW"]),
                                                                AttendanceConflict.employee_id.in_(ids)).count(),
               "auto_closed": db.query(OvertimePrompt).filter(OvertimePrompt.state == "AUTO_CLOSED",
                                                              OvertimePrompt.reviewed_at.is_(None)).count() if admin else 0}
    off_soon = (db.query(Request).filter(Request.employee_id.in_(ids), Request.request_type == "LEAVE",
                                         Request.status == "APPROVED", Request.end_date >= today,
                                         Request.start_date <= today + timedelta(days=14))
                .order_by(Request.start_date).limit(15).all())
    headcount = {"total": len(members), "managers": sum(1 for m in members if m.role == "MANAGER"),
                 "employees": sum(1 for m in members if m.role == "EMPLOYEE"),
                 "by_department": [{"name": k, "count": len(v)} for k, v in sorted(depts.items())],
                 "by_shift": [{"name": s["shift"], "count": s["total"]} for s in shift_list]}
    if admin:
        headcount["inactive"] = db.query(Employee).filter(Employee.is_active.is_(False)).count()
    return {"scope": "company" if admin else "team", "headcount": headcount, "today": today_block, "people": people,
            "by_shift": shift_list, "month": {"label": cur0.strftime("%B %Y"), "summary": month,
                                              "previous_label": prev0.strftime("%B"), "previous": previous},
            "leaders": leaders, "by_department": by_department, "daily": daily, "trend": trend(all_rows, today),
            "pending": pending, "upcoming_leave": [{"employee_id": r.employee_id, "employee": name_of.get(r.employee_id, "?"),
                                                    "start_date": r.start_date, "end_date": r.end_date,
                                                    "days": float(r.duration_days or 0), "leave_type": r.leave_type} for r in off_soon],
            "holidays": upcoming_holidays(db, today)}