"""Statistics shared by the dashboards and the Working Time report (one source of truth)."""
from collections import defaultdict
from datetime import date, timedelta
from sqlalchemy.orm import Session, selectinload
from models import Attendance, DailyAttendanceStatus, Holiday, Request, Shift


def month_start(d: date, back: int = 0) -> date:
    y, m = d.year, d.month - back
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def build_days(db: Session, emps, first: date, last: date, now, settings) -> dict:
    """Per-day working-time facts for every employee between `first` and `last` (inclusive), oldest first."""
    ids = [e.id for e in emps] or [0]
    atts, dailies, leaves = defaultdict(dict), defaultdict(dict), defaultdict(list)
    for a in (db.query(Attendance).options(selectinload(Attendance.sessions))
              .filter(Attendance.employee_id.in_(ids), Attendance.work_date >= first, Attendance.work_date <= last)):
        atts[a.employee_id][a.work_date] = a
    for x in db.query(DailyAttendanceStatus).filter(DailyAttendanceStatus.employee_id.in_(ids),
                                                    DailyAttendanceStatus.work_date >= first,
                                                    DailyAttendanceStatus.work_date <= last):
        dailies[x.employee_id][x.work_date] = x
    holidays = {h.holiday_date: h for h in db.query(Holiday).filter(Holiday.holiday_date >= first,
                                                                    Holiday.holiday_date <= last)}
    for r in db.query(Request).filter(Request.employee_id.in_(ids), Request.request_type == "LEAVE",
                                      Request.status == "APPROVED", Request.start_date <= last,
                                      Request.end_date >= first):
        leaves[r.employee_id].append(r)
    shifts = {s.id: s for s in db.query(Shift).all()}
    default_full = settings.full_day_minutes if settings else 480
    today = now.date()

    out = {}
    for e in emps:
        own = shifts.get(e.shift_id)
        fallback = own.required_work_minutes if own else default_full
        rows, d = [], first
        while d <= last:
            att, daily, holiday = atts[e.id].get(d), dailies[e.id].get(d), holidays.get(d)
            leave = next((l for l in leaves[e.id] if l.start_date <= d <= l.end_date and (l.duration_days or 1) >= 1), None)
            kind = "WEEKEND" if d.weekday() >= 5 else "HOLIDAY" if holiday else "LEAVE" if leave else "WORKDAY"
            shift = shifts.get(att.shift_id) if att and att.shift_id else own
            required = (shift.required_work_minutes if shift else fallback) if kind == "WORKDAY" else 0
            worked = att.worked_minutes if att else 0
            overtime = att.overtime_minutes if att else 0
            live = False
            open_s = next((x for x in att.sessions if x.check_out_at is None), None) if att else None
            if open_s:
                cin = open_s.check_in_at if open_s.check_in_at.tzinfo else open_s.check_in_at.replace(tzinfo=now.tzinfo)
                if (now - cin).total_seconds() < 36 * 3600:        # still working (also a night shift across midnight)
                    worked += int(max(0.0, (now - cin).total_seconds() / 60))
                    overtime = max(0, worked - required) if required else 0
                    live = True
            status = (daily.status if daily else None) or (att.status if att else None) or \
                     ("NO_RECORD" if kind == "WORKDAY" and d < today else None)
            rows.append({"employee_id": e.id, "date": d, "weekday": d.strftime("%a"), "kind": kind,
                         "holiday": holiday.name if holiday and kind == "HOLIDAY" else None, "status": status,
                         "required_minutes": required, "worked_minutes": worked, "overtime_minutes": overtime,
                         "late_minutes": att.late_minutes if att else 0,
                         "check_in_at": att.check_in_at if att else None, "check_out_at": att.check_out_at if att else None,
                         "sessions": len(att.sessions) if att else 0, "live": live,
                         "mode": att.work_mode if att and worked > 0 else None})
            d += timedelta(days=1)
        out[e.id] = rows
    return out


def summarize(days, today: date) -> dict:
    """Totals for a list of day rows (one person or many)."""
    worked_days = [x for x in days if x["worked_minutes"] > 0]
    # Today only counts towards the required time once the person has started working (the day is not over yet).
    workdays = [x for x in days if x["kind"] == "WORKDAY" and (x["date"] < today or x["worked_minutes"] > 0)]
    present = [x for x in workdays if x["worked_minutes"] > 0]
    late_present = sum(1 for x in present if x["late_minutes"] > 0)
    total_worked = sum(x["worked_minutes"] for x in days)
    total_required = sum(x["required_minutes"] for x in workdays)
    return {"total_worked_minutes": total_worked, "total_required_minutes": total_required,
            "difference_minutes": total_worked - total_required,
            "average_worked_minutes": round(total_worked / len(worked_days)) if worked_days else 0,
            "overtime_minutes": sum(x["overtime_minutes"] for x in days),
            "days_worked": len(worked_days), "working_days": len(workdays),
            "leave_days": sum(1 for x in days if x["kind"] == "LEAVE"),
            "absent_days": sum(1 for x in workdays if x["status"] == "ABSENT"),
            "late_days": sum(1 for x in days if x["late_minutes"] > 0),
            "present_days": len(present),
            "half_days": sum(1 for x in workdays if x["status"] == "HALF_DAY"),
            "incomplete_days": sum(1 for x in workdays if x["status"] in ("INCOMPLETE", "FLAGGED")),
            "wfh_days": sum(1 for x in worked_days if x["mode"] == "WFH"),
            "on_time_days": len(present) - late_present,
            "attendance_rate": round(100 * len(present) / len(workdays)) if workdays else None,
            "punctuality_rate": round(100 * (len(present) - late_present) / len(present)) if present else None}


def on_time_streak(days, today: date) -> int:
    """Consecutive working days (newest first) on which the person worked and was not late."""
    streak = 0
    for x in reversed(days):
        if x["kind"] != "WORKDAY" or x["date"] > today:
            continue
        if x["worked_minutes"] == 0:
            if x["date"] == today:       # today has not started yet: do not break the streak
                continue
            break
        if x["late_minutes"] > 0:
            break
        streak += 1
    return streak