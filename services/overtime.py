"""Forgotten check-out / overtime workflow.

Every minute run_cycle() looks at every OPEN work session and compares the time worked so far with the
required minutes of THAT person's own shift (falling back to the company full-day minutes):

  1. Required duration reached        -> ask "Are you still working overtime?"
  2. No answer                        -> remind every `reminder_interval_minutes`
  3. No answer after `max_reminders`  -> close the session PROVISIONALLY at the moment the required
                                         duration was reached (no overtime counted) and queue it for
                                         Super Admin review
  4. Employee confirms overtime       -> attendance stays open, no further questions
  5. Confirmed overtime               -> reminder every `overtime_reminder_interval_minutes` (default 2 h)
  6. Employee can check out whenever they finish (normal Check out)
  7. Super Admin reviews / corrects provisionally closed records
"""
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import Employee, Attendance, AttendanceSession, Shift, OvertimePrompt, OvertimeSetting
from services.jobs import get_settings as get_company, company_tz
from services.notifications import notify, resolve_actions

ACTIVE = ("AWAITING_RESPONSE", "OVERTIME_CONFIRMED")


def fmt(minutes) -> str:
    m = max(0, int(round(minutes or 0)))
    return f"{m // 60}h {m % 60:02d}m"


def _aware(dt, tz):
    return dt if dt.tzinfo else dt.replace(tzinfo=tz)


def get_overtime_settings(db: Session) -> OvertimeSetting:
    row = db.query(OvertimeSetting).first()
    if not row:
        row = OvertimeSetting(enabled=True, reminder_interval_minutes=15, max_reminders=3,
                              overtime_reminder_interval_minutes=120)
        db.add(row)
        db.flush()
    return row


def required_minutes(db: Session, att: Attendance, emp: Employee, company) -> int:
    """Dynamic: the attendance day's shift, else the employee's shift, else the company full-day minutes."""
    shift = db.query(Shift).filter(Shift.id == (att.shift_id or emp.shift_id)).first() if (att.shift_id or emp.shift_id) else None
    if shift:
        return shift.required_work_minutes
    return company.full_day_minutes if company else 480


def worked_so_far(att: Attendance, sess: AttendanceSession, now, tz):
    done = sum(x.worked_minutes for x in att.sessions if x.check_out_at is not None)
    cin = _aware(sess.check_in_at, tz)
    return done, cin, done + max(0.0, (now - cin).total_seconds() / 60)


def _latest_prompt(db, attendance_id):
    return (db.query(OvertimePrompt).filter(OvertimePrompt.attendance_id == attendance_id)
            .order_by(OvertimePrompt.id.desc()).first())


def run_cycle(db: Session, now=None) -> dict:
    company = get_company(db)
    tz = company_tz(company)
    now = now or datetime.now(tz)
    cfg = get_overtime_settings(db)
    out = {"prompted": 0, "reminded": 0, "auto_closed": 0, "overtime_reminders": 0, "ended": 0}
    if not cfg.enabled:
        db.commit()
        return out
    gap, ot_gap = timedelta(minutes=cfg.reminder_interval_minutes), timedelta(minutes=cfg.overtime_reminder_interval_minutes)

    rows = (db.query(AttendanceSession, Attendance).join(Attendance, AttendanceSession.attendance_id == Attendance.id)
            .join(Employee, Employee.id == Attendance.employee_id)
            .filter(AttendanceSession.check_out_at.is_(None), Employee.is_active.is_(True)).all())
    open_session_ids = {s.id for s, _ in rows}

    # tidy: prompts whose session is no longer open (employee checked out, or it was closed another way)
    for pr in db.query(OvertimePrompt).filter(OvertimePrompt.state.in_(ACTIVE)).all():
        if pr.session_id not in open_session_ids:
            pr.state, pr.closed_at = "ENDED", pr.closed_at or now
            resolve_actions(db, pr.employee_id, pr.attendance_id)
            out["ended"] += 1

    admins = db.query(Employee).filter(Employee.role == "SUPER_ADMIN", Employee.is_active.is_(True)).all()
    for sess, att in rows:
        emp = att.employee
        done, cin, worked = worked_so_far(att, sess, now, tz)
        if now - cin > timedelta(hours=36):      # forgotten long ago: handled at the next check-in / nightly job
            continue
        required = required_minutes(db, att, emp, company)
        pr = _latest_prompt(db, att.id)
        if pr is None or pr.session_id != sess.id:
            if worked >= required:               # 1) required duration completed
                reached = cin + timedelta(minutes=max(0, required - done))
                db.add(OvertimePrompt(attendance_id=att.id, session_id=sess.id, employee_id=emp.id,
                                      state="AWAITING_RESPONSE", required_minutes=required,
                                      required_reached_at=reached, next_reminder_at=now + gap))
                notify(db, emp.id, "OVERTIME_PROMPT", "Required hours completed",
                       f"You have completed your required {fmt(required)}. Are you still working overtime? "
                       f"Confirm to keep your attendance open, or check out.",
                       attendance_id=att.id, requires_action=True)
                out["prompted"] += 1
            continue

        if pr.state == "AWAITING_RESPONSE" and pr.next_reminder_at and now >= _aware(pr.next_reminder_at, tz):
            if pr.reminders_sent < cfg.max_reminders:       # 2) remind
                pr.reminders_sent += 1
                pr.next_reminder_at = now + gap
                notify(db, emp.id, "OVERTIME_REMINDER", f"Reminder {pr.reminders_sent} of {cfg.max_reminders}",
                       f"You completed your required {fmt(required)} and have not responded. Are you still working? "
                       f"If you do not respond your attendance will be closed automatically.",
                       attendance_id=att.id, requires_action=True)
                out["reminded"] += 1
            else:                                            # 3) provisional automatic close
                closed_at = max(cin, min(_aware(pr.required_reached_at, tz), now))
                sess.check_out_at = closed_at
                sess.worked_minutes = int((closed_at - cin).total_seconds() // 60)
                db.flush()
                att.worked_minutes = sum(x.worked_minutes for x in att.sessions if x.check_out_at is not None)
                att.check_out_at = closed_at
                att.status = "INCOMPLETE"
                att.overtime_minutes = 0
                att.notes = ((att.notes + " | ") if att.notes else "") + \
                    f"Closed automatically at {closed_at:%H:%M}: no response to overtime reminders (awaiting Super Admin review)"
                pr.state, pr.auto_closed_at, pr.closed_at, pr.next_reminder_at = "AUTO_CLOSED", now, closed_at, None
                resolve_actions(db, emp.id, att.id)
                notify(db, emp.id, "AUTO_CLOSED", "Attendance closed automatically",
                       f"You did not respond, so your attendance for {att.work_date} was closed provisionally at "
                       f"{closed_at:%H:%M}. If you worked longer, ask a Super Admin to correct it.", attendance_id=att.id)
                for a in admins:
                    notify(db, a.id, "AUTO_CLOSED_REVIEW", "Auto-closed attendance to review",
                           f"{emp.first_name} {emp.last_name}'s attendance for {att.work_date} was closed "
                           f"provisionally at {closed_at:%H:%M}.", attendance_id=att.id)
                out["auto_closed"] += 1
        elif pr.state == "OVERTIME_CONFIRMED" and pr.next_reminder_at and now >= _aware(pr.next_reminder_at, tz):
            pr.overtime_reminders_sent += 1                  # 5) overtime reminder every 2 hours
            pr.next_reminder_at = now + ot_gap
            notify(db, emp.id, "OVERTIME_CHECK", "Still working overtime?",
                   f"You have worked {fmt(worked - required)} of overtime. Remember to check out when you finish.",
                   attendance_id=att.id)
            out["overtime_reminders"] += 1
    db.commit()
    return out


def confirm_overtime(db: Session, emp: Employee, now=None) -> OvertimePrompt:
    company = get_company(db)
    now = now or datetime.now(company_tz(company))
    cfg = get_overtime_settings(db)
    row = (db.query(OvertimePrompt, AttendanceSession)
           .join(AttendanceSession, AttendanceSession.id == OvertimePrompt.session_id)
           .filter(OvertimePrompt.employee_id == emp.id, OvertimePrompt.state == "AWAITING_RESPONSE",
                   AttendanceSession.check_out_at.is_(None)).order_by(OvertimePrompt.id.desc()).with_for_update().first())
    if not row:
        raise HTTPException(400, "No overtime question is waiting for your answer")
    pr = row[0]
    pr.state, pr.confirmed_at = "OVERTIME_CONFIRMED", now
    pr.next_reminder_at = now + timedelta(minutes=cfg.overtime_reminder_interval_minutes)
    resolve_actions(db, emp.id, pr.attendance_id)
    notify(db, emp.id, "OVERTIME_CONFIRMED", "Overtime confirmed",
           f"Your attendance stays open. You will be reminded every "
           f"{fmt(cfg.overtime_reminder_interval_minutes)}. Check out whenever you finish.", attendance_id=pr.attendance_id)
    db.commit()
    return pr


def status_for(db: Session, emp: Employee, now=None) -> dict:
    """Live progress + workflow state for the dashboard."""
    company = get_company(db)
    tz = company_tz(company)
    now = now or datetime.now(tz)
    cfg = get_overtime_settings(db)
    row = (db.query(AttendanceSession, Attendance).join(Attendance, AttendanceSession.attendance_id == Attendance.id)
           .filter(Attendance.employee_id == emp.id, AttendanceSession.check_out_at.is_(None))
           .order_by(AttendanceSession.id.desc()).first())
    if not row:
        recent = (db.query(OvertimePrompt).filter(OvertimePrompt.employee_id == emp.id, OvertimePrompt.state == "AUTO_CLOSED",
                                                  OvertimePrompt.reviewed_at.is_(None)).order_by(OvertimePrompt.id.desc()).first())
        if recent:
            return {"active": False, "state": "AUTO_CLOSED", "closed_at": recent.closed_at, "prompt_id": recent.id}
        return {"active": False, "state": "IDLE"}
    sess, att = row
    done, cin, worked = worked_so_far(att, sess, now, tz)
    required = required_minutes(db, att, emp, company)
    pr = _latest_prompt(db, att.id)
    pr = pr if pr and pr.session_id == sess.id else None
    state = pr.state if pr else "WORKING"
    return {"active": True, "state": state, "enabled": cfg.enabled, "prompt_id": pr.id if pr else None,
            "required_minutes": required, "worked_minutes": int(worked), "overtime_minutes": max(0, int(worked - required)),
            "reminders_sent": pr.reminders_sent if pr else 0, "max_reminders": cfg.max_reminders,
            "next_reminder_at": pr.next_reminder_at if pr else None, "check_in_at": cin,
            "completes_at": (cin + timedelta(minutes=max(0, required - done))) if worked < required else None}
