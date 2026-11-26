"""Transactional notification outbox; SMTP runs outside attendance requests."""
import os, ssl, smtplib, logging
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate
from sqlalchemy import or_
from models import Employee, CompanySetting, AttendanceSession, EmailSetting, EmailOutbox, Notification, OvertimePrompt

log = logging.getLogger(__name__)
KINDS = {
    'OVERTIME_PROMPT': 'Required hours completed', 'OVERTIME_REMINDER': 'Missing check-out reminder',
    'OVERTIME_CHECK': 'Confirmed overtime reminder', 'OVERTIME_CONFIRMED': 'Overtime confirmation',
    'FORGOT_CHECKOUT': 'Forgotten check-out (manager)', 'AUTO_CLOSED': 'Automatic attendance closure',
    'AUTO_CLOSED_REVIEW': 'Super Admin review', 'AUTO_CLOSE_REVIEWED': 'Review completed',
    'ATTENDANCE_CORRECTED': 'Attendance correction', 'LEAVE_REQUEST': 'Leave request',
    'LEAVE_DECISION': 'Leave decision', 'WFH_REQUEST': 'WFH request', 'WFH_DECISION': 'WFH decision',
}
DEFAULT_ON = set(KINDS) - {'LEAVE_REQUEST', 'LEAVE_DECISION', 'WFH_REQUEST', 'WFH_DECISION', 'OVERTIME_CONFIRMED'}
LIVE = {'OVERTIME_PROMPT', 'OVERTIME_REMINDER', 'OVERTIME_CHECK'}

def config():
    user = os.getenv('SMTP_USER', '').strip()
    return dict(host=os.getenv('SMTP_HOST', '').strip(), port=int(os.getenv('SMTP_PORT', '587')),
                security=os.getenv('SMTP_SECURITY', 'starttls').lower(), user=user,
                password=os.getenv('SMTP_PASSWORD', ''), sender=os.getenv('SMTP_FROM', '').strip() or user,
                app_url=os.getenv('APP_URL', 'http://127.0.0.1:8000/app/'))

def configured():
    try:
        c = config()
        return bool(c['host'] and c['sender'] and c['security'] in ('ssl','starttls') and (not c['user'] or c['password']))
    except ValueError:
        return False

def settings(db):
    row = db.get(EmailSetting, 1)
    return (row.enabled, set(row.kinds.split(','))) if row else (True, DEFAULT_ON.copy())

def queue(db, note):
    enabled, kinds = settings(db)
    if not enabled or note.kind not in kinds:
        return
    emp = db.get(Employee, note.employee_id)
    if not emp or not emp.is_active or not emp.email:
        return
    session_id = None
    if note.kind in LIVE:
        session = db.query(AttendanceSession).filter_by(attendance_id=note.attendance_id, check_out_at=None).order_by(AttendanceSession.id.desc()).first()
        if not session:
            return
        session_id = session.id
    company = (db.query(CompanySetting.company_name).first() or ('Attendance',))[0] or 'Attendance'
    subject = f'[{company}] {note.title}'.replace('\n',' ').replace('\r',' ')[:190]
    url = os.getenv('APP_URL', 'http://127.0.0.1:8000/app/')
    body = f'Hi {emp.first_name},\n\n{note.message}\n\nOpen attendance: {url}\n\n{company}\nAutomated message; please do not reply.'
    db.add(EmailOutbox(notification_id=note.id, employee_id=emp.id, session_id=session_id,
                       to_address=emp.email, subject=subject, body=body, kind=note.kind))

def deliver(to, subject, body, message_id=None):
    if not configured():
        raise RuntimeError('SMTP is not configured')
    c = config()
    msg = EmailMessage()
    msg['From'], msg['To'], msg['Subject'] = c['sender'], to, subject
    msg['Date'] = formatdate()
    if message_id: msg['Message-ID'] = message_id
    msg.set_content(body)
    ctx = ssl.create_default_context()
    server = smtplib.SMTP_SSL(c['host'], c['port'], timeout=20, context=ctx) if c['security']=='ssl' else smtplib.SMTP(c['host'], c['port'], timeout=20)
    with server:
        server.ehlo()
        if c['security']=='starttls':
            server.starttls(context=ctx); server.ehlo()
        if c['user']: server.login(c['user'], c['password'])
        if server.send_message(msg): raise RuntimeError('Recipient refused')

def valid(db, row):
    enabled, kinds = settings(db)
    emp = db.get(Employee, row.employee_id)
    if not enabled or row.kind not in kinds or not emp or not emp.is_active or emp.email != row.to_address:
        return False
    if row.kind not in LIVE: return True
    sess = db.get(AttendanceSession, row.session_id)
    if not sess or sess.check_out_at is not None: return False
    pr = db.query(OvertimePrompt).filter_by(session_id=sess.id).order_by(OvertimePrompt.id.desc()).first()
    return bool(pr and pr.state == ('OVERTIME_CONFIRMED' if row.kind=='OVERTIME_CHECK' else 'AWAITING_RESPONSE'))

def send_pending(db, sender=deliver, limit=50):
    counts = dict(sent=0, failed=0, retrying=0, cancelled=0)
    if not configured(): return dict(counts, skipped='SMTP not configured')
    for _ in range(limit):
        now = datetime.now(timezone.utc)
        row = db.query(EmailOutbox).filter(EmailOutbox.status=='PENDING', or_(EmailOutbox.next_attempt_at==None, EmailOutbox.next_attempt_at<=now)).order_by(EmailOutbox.id).with_for_update(skip_locked=True).first()
        if not row: db.rollback(); break
        if not valid(db,row):
            row.status='CANCELLED'; counts['cancelled']+=1
        else:
            row.attempts += 1
            try:
                sender(row.to_address,row.subject,row.body, f'<attendance-{row.id}@attendance.local>')
                row.status='SENT'; row.sent_at=now; row.last_error=None; counts['sent']+=1
            except Exception as exc:
                row.last_error=type(exc).__name__  # do not persist credentials or SMTP response content
                if row.attempts>=5: row.status='FAILED'; counts['failed']+=1
                else: row.next_attempt_at=now+timedelta(minutes=2**row.attempts); counts['retrying']+=1
        db.commit()
    return counts
