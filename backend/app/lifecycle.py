"""Application startup recovery and camera shutdown."""

from contextlib import asynccontextmanager

from sqlalchemy import select

from .database import DB, Attempt, TrainingSession, init_db, now
from .runtime import runtime


@asynccontextmanager
async def lifespan(app):
    init_db()
    # A previous process cannot keep capturing: preserve evidence, mark interrupted work.
    with DB.begin() as db:
        for a in db.scalars(select(Attempt).where(Attempt.result_status == "IN_PROGRESS")):
            a.result_status = "ABORTED"
            a.result_reason = "โปรแกรมปิดก่อนบันทึกเสร็จ"
            a.ended_at = now()
        for s in db.scalars(select(TrainingSession).where(TrainingSession.status == "IN_PROGRESS")):
            s.status = "ABORTED"
            s.ended_at = now()
    yield
    runtime.stop()
