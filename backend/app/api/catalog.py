"""Catalog API routes; public URLs remain unchanged."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from ..database import DB, METRICS, Criteria, Exercise
from ..lessons import LESSONS
from ..repositories.report_queries import exercise_catalog
from ..runtime import runtime
from .dependencies import require, serialized
from .schemas import CriteriaRequest

router = APIRouter()


@router.get("/api/catalog")
def catalog():
    with DB() as db:
        return exercise_catalog(db, LESSONS)


@router.get("/api/metrics")
def metric_catalog():
    active = {code for lesson in LESSONS.values() for code in lesson["metrics"]}
    return {code: unit for code, unit in METRICS.items() if code in active}


@router.post("/api/exercises/{eid}/criteria")
@serialized
def new_criteria(eid: int, body: CriteriaRequest):
    if any(k not in METRICS for k in body.rules):
        raise HTTPException(422, "รหัสตัวชี้วัดไม่ถูกต้อง")
    if body.approved and not body.rules:
        raise HTTPException(422, "ต้องกำหนดกฎก่อนยืนยัน")
    with runtime.lock, DB.begin() as db:
        require(db, Exercise, eid)
        version = (
            db.scalar(select(func.max(Criteria.version_no)).where(Criteria.exercise_id == eid)) or 0
        ) + 1
        exercise = require(db, Exercise, eid)
        if exercise.module_id not in LESSONS:
            raise HTTPException(409, "prototype นี้ยังไม่เปิดแบบฝึกแก้สนุก")
        if any(k not in LESSONS[exercise.module_id]["metrics"] for k in body.rules):
            raise HTTPException(422, "ตัวชี้วัดไม่ตรงกับบทเรียน")
        c = Criteria(
            exercise_id=eid, version_no=version, definition=body.model_dump(exclude_none=True)
        )
        db.add(c)
        db.flush()
        return {"id": c.id, "version": version}


@router.get("/api/exercises/{eid}/criteria-template")
def criteria_template(eid: int):
    with DB() as db:
        exercise = require(db, Exercise, eid)
        module_id = exercise.module_id
        fraction = exercise.setup_definition.get("fraction")
    from ..criteria_templates import training_template

    try:
        return training_template(module_id, fraction)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
