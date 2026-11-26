import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import models
from database import engine
from routers import (auth, admin, admin_extra, admin_ops, password, attendance, attendance_history, holidays, dashboard,
                     shifts, company_settings, leaves, leave_cancel, balances, wfh, conflicts, notifications, overtime,
                     email)
from services.scheduler import start_scheduler

# Development convenience. For schema changes use Alembic (see README).
models.Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = start_scheduler()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Employee Attendance Management System", lifespan=lifespan)

# Lets the page work when opened as a file ("null" origin) or from any IDE/dev server on this computer
# (PyCharm preview :63342, VS Code Live Server :5500, ...). Add more origins with CORS_ORIGINS in .env.
origins = ["null"] + [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins,
                   allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
                   allow_methods=["*"], allow_headers=["*"])

for router in (
    auth.router,
    admin.router,
    admin_extra.router,
    admin_ops.router,
    password.router,
    attendance.router,
    attendance_history.router,
    holidays.router,
    shifts.router,
    dashboard.router,
    company_settings.router,
    leaves.router,
    leave_cancel.router,
    balances.router,
    wfh.router,
    conflicts.router,
    notifications.router,
    overtime.router,
    overtime.admin_router,
    email.router
):
    app.include_router(router)

# Frontend: http://127.0.0.1:8000/app/
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
