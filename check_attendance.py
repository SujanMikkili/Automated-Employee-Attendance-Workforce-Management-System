"""Find out why check-in says "check out of your current session first", and fix it.

Run from the project folder:  python check_attendance.py
It first checks that the NEW code is installed, then looks at the account's open sessions.
Nothing is changed unless you answer y.
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import func
from database import SessionLocal
from models import Employee, Attendance, AttendanceSession, AttendanceConflict, CompanySetting, Shift


def read(path):
    try:
        return open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return ""


def check_installed_code():
    print("1) Checking the code in this folder")
    print("   Folder:", os.getcwd())
    problems = 0
    if "auto_close_stale_sessions" in read(os.path.join("routers", "attendance.py")):
        print("   OK      routers/attendance.py is the NEW version")
    else:
        problems += 1
        print("   PROBLEM routers/attendance.py is the OLD version. Replace it with the one from the zip.")
    if "You forgot to check out" in read(os.path.join("frontend", "index.html")):
        print("   OK      frontend/index.html is the NEW version")
    else:
        problems += 1
        print("   PROBLEM frontend/index.html is the OLD version. Replace it with the one from the zip.")
    if "open_session" in read(os.path.join("routers", "attendance_history.py")):
        print("   OK      routers/attendance_history.py is the NEW version")
    else:
        problems += 1
        print("   PROBLEM routers/attendance_history.py is the OLD version. Replace it with the one from the zip.")
    if problems:
        print("   -> After replacing the files, STOP uvicorn (Ctrl+C) and start it again, then press Ctrl+F5 in the browser.")
    return problems


def main():
    problems = check_installed_code()
    print("\n2) Checking the account")
    email = input("   Email of the user who cannot check in: ").strip()
    db = SessionLocal()
    try:
        emp = db.query(Employee).filter(func.lower(Employee.email) == email.lower()).first()
        if not emp:
            print("   PROBLEM: no employee has that email.")
            return
        settings = db.query(CompanySetting).first()
        tz = ZoneInfo(settings.timezone if settings else "Asia/Kolkata")
        now = datetime.now(tz)
        today = now.date()
        print(f"   {emp.first_name} {emp.last_name} ({emp.role}). Company date today: {today}")

        rows = (db.query(AttendanceSession, Attendance)
                .join(Attendance, AttendanceSession.attendance_id == Attendance.id)
                .filter(Attendance.employee_id == emp.id, AttendanceSession.check_out_at.is_(None))
                .order_by(AttendanceSession.id).all())
        if not rows:
            print("   This account has NO open session, so the 'check out first' message cannot come from this database.")
            print("   -> The server you are using is probably connected to a different database, or is still running old code.")
            print("      Check that .env DATABASE_URL is the one uvicorn uses, then restart uvicorn.")
            return
        for sess, att in rows:
            kind = "from an EARLIER day (forgotten check-out)" if att.work_date < today else "from TODAY (you are checked in right now)"
            print(f"   OPEN session {sess.id}: work date {att.work_date}, checked in {sess.check_in_at}  -> {kind}")
        if problems:
            print("\n   With the old code installed, an earlier-day session blocks every new check-in.")
        else:
            print("\n   With the new code, an earlier-day session is closed automatically at the next check-in.")
            print("   A session from TODAY must be closed with the Check out button.")

        if input("\n3) Close these open sessions now? (y/n): ").strip().lower() != "y":
            return
        for sess, att in rows:
            check_in = sess.check_in_at if sess.check_in_at.tzinfo else sess.check_in_at.replace(tzinfo=tz)
            stale = att.work_date < today
            end = now
            if stale:
                shift = db.query(Shift).filter(Shift.id == att.shift_id).first() if att.shift_id else None
                end = check_in
                if shift:
                    from routers.attendance import get_shift_datetimes
                    shift_end = get_shift_datetimes(shift, att.work_date, tz)[1]
                    if shift_end and shift_end > check_in:
                        end = shift_end
                end = min(end, now)
            sess.check_out_at = end
            sess.worked_minutes = max(0, int((end - check_in).total_seconds() // 60))
            db.flush()
            done = db.query(AttendanceSession).filter(AttendanceSession.attendance_id == att.id,
                                                      AttendanceSession.check_out_at.isnot(None)).all()
            att.worked_minutes = sum(x.worked_minutes for x in done)
            att.check_out_at = end
            att.status = "INCOMPLETE" if stale else "COMPLETED"
            if stale and not db.query(AttendanceConflict.id).filter(
                    AttendanceConflict.attendance_id == att.id,
                    AttendanceConflict.conflict_type == "MISSING_CHECK_OUT").first():
                db.add(AttendanceConflict(employee_id=emp.id, attendance_id=att.id, conflict_type="MISSING_CHECK_OUT",
                                          status="OPEN", description="Session closed manually with check_attendance.py. Please review the times."))
            print(f"   Closed session {sess.id} at {end:%Y-%m-%d %H:%M}")
        db.commit()
        print("\nDone. The user can check in now.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
