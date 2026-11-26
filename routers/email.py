from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from database import get_db
from models import EmailSetting, EmailOutbox
from routers.auth import require_roles
from services.email_services import KINDS, settings, configured, config, deliver

router = APIRouter(prefix='/admin/email', tags=['Email management'], dependencies=[Depends(require_roles('SUPER_ADMIN'))])

class SettingsBody(BaseModel):
    enabled: bool
    kinds: list[str]

@router.get('/settings')
def read_settings(db=Depends(get_db)):
    enabled, kinds = settings(db)
    try: c = config()
    except ValueError: c = {}
    return dict(enabled=enabled, kinds=sorted(kinds), available=KINDS, configured=configured(),
                host=c.get('host'), port=c.get('port'), security=c.get('security'), sender=c.get('sender'))

@router.put('/settings')
def save_settings(body: SettingsBody, db=Depends(get_db)):
    if set(body.kinds)-set(KINDS): raise HTTPException(400,'Unknown email category')
    row = db.get(EmailSetting,1) or EmailSetting(id=1)
    row.enabled=body.enabled; row.kinds=','.join(sorted(set(body.kinds)))
    db.add(row); db.commit()
    return read_settings(db)

@router.post('/test')
def test_email(admin=Depends(require_roles('SUPER_ADMIN'))):
    if not configured(): raise HTTPException(400,'Configure SMTP in .env first')
    try: deliver(admin.email,'Attendance email test','Your attendance SMTP configuration works.')
    except Exception as exc: raise HTTPException(502,'SMTP test failed: '+type(exc).__name__)
    return {'message':'Test accepted by SMTP server', 'recipient':admin.email}

@router.get('/history')
def history(limit: int=Query(100,ge=1,le=500), db=Depends(get_db)):
    counts=dict(db.query(EmailOutbox.status,func.count(EmailOutbox.id)).group_by(EmailOutbox.status).all())
    rows=db.query(EmailOutbox).order_by(EmailOutbox.id.desc()).limit(limit).all()
    return {'counts':counts,'items':[{k:getattr(r,k) for k in ('id','to_address','subject','kind','status','attempts','created_at','sent_at','last_error')} for r in rows]}

@router.post('/retry')
def retry(db=Depends(get_db)):
    n=db.query(EmailOutbox).filter_by(status='FAILED').update({'status':'PENDING','attempts':0,'next_attempt_at':None,'last_error':None})
    db.commit(); return {'message':f'{n} emails queued for retry'}
