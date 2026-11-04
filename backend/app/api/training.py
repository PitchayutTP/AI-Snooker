"""Training API routes; public URLs remain unchanged."""

import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from ..database import (
    DB,
    Attempt,
    Criteria,
    Exercise,
    Measurement,
    MetricDefinition,
    TrainingSession,
    now,
)
from ..lessons import LESSONS, feedback
from ..m1_assessment import assess_m1
from ..m2_follow_through import assess_follow_through
from ..metrics import data_quality, evaluate, summarize
from ..protocol import assessment_problem
from ..runtime import runtime
from ..services.reporting import detail
from ..vision import ball_metrics
from .dependencies import current_user, owned_session, require, serialized
from .reports import session_detail
from .schemas import AttemptRequest, FinishRequest, StartRequest

router = APIRouter()


@router.post("/api/sessions")
@serialized
def start_session(body: StartRequest, user=Depends(current_user)):
    sid = str(body.request_id)
    with runtime.lock, DB.begin() as db:
        old = db.get(TrainingSession, sid)
        if old:
            owned_session(db, sid, user)
            if (
                old.criteria_id != body.criteria_id
                or old.configuration_snapshot.get("purpose", "PILOT") != body.purpose
            ):
                raise HTTPException(409, "request_id ถูกใช้กับคำขออื่นแล้ว")
            return {"id": old.id, "status": old.status}
        if runtime.session_id:
            raise HTTPException(409, "มีรอบฝึกที่ยังไม่จบ")
        if runtime.owner_profile_id != user["profile_id"]:
            raise HTTPException(409, "กรุณาตรวจความพร้อมด้วยบัญชีนี้ก่อน")
        if not runtime.snapshot()["ready"]:
            raise HTTPException(409, "กล้องหรือข้อมูลยังไม่พร้อม")
        c = require(db, Criteria, body.criteria_id)
        if c.exercise_id != runtime.config["exercise_id"]:
            raise HTTPException(409, "เกณฑ์ไม่ตรงกับแบบฝึกที่ตรวจความพร้อม")
        if body.purpose == "ASSESSMENT":
            problem = assessment_problem(c.definition, runtime.config)
            if problem:
                raise HTTPException(422, problem)
        configuration = {**runtime.config, "purpose": body.purpose}
        s = TrainingSession(
            id=sid,
            profile_id=user["profile_id"],
            criteria_id=c.id,
            configuration_snapshot=configuration,
        )
        db.add(s)
    runtime.session_id = sid
    return {"id": sid, "status": "IN_PROGRESS"}


@router.post("/api/sessions/{sid}/attempts")
@serialized
def begin_attempt(sid: str, body: AttemptRequest, user=Depends(current_user)):
    aid = str(body.request_id)
    with runtime.lock, DB.begin() as db:
        owned_session(db, sid, user)
        old = db.get(Attempt, aid)
        if old:
            owned_session(db, old.session_id, user)
            if old.session_id != sid:
                raise HTTPException(409, "request_id ถูกใช้ในรอบอื่น")
            return {"id": old.id, "status": old.result_status}
        s = require(db, TrainingSession, sid)
        if s.status != "IN_PROGRESS" or runtime.session_id != sid:
            raise HTTPException(409, "รอบนี้ไม่ได้กำลังทำงาน")
        if runtime.attempt_id:
            raise HTTPException(409, "ต้องจบครั้งก่อนหน้า")
        current = detail(db, s)
        if current["protocol_result"]["remaining"] == 0:
            raise HTTPException(409, "ครบจำนวนครั้งที่ประเมินได้แล้ว กรุณาจบรอบและดูสรุป")
        if not runtime.snapshot()["ready"]:
            raise HTTPException(409, "ข้อมูลกล้องไม่พร้อม")
        number = (
            db.scalar(select(func.max(Attempt.attempt_number)).where(Attempt.session_id == sid))
            or 0
        ) + 1
        db.add(Attempt(id=aid, session_id=sid, attempt_number=number))
    runtime.begin(aid)
    return {"id": aid, "status": "IN_PROGRESS"}


@router.post("/api/attempts/{aid}/finish")
@serialized
def finish_attempt(aid: str, body: FinishRequest, user=Depends(current_user)):
    with runtime.lock:
        with DB.begin() as db:
            a = require(db, Attempt, aid)
            owned_session(db, a.session_id, user)
            if a.result_status != "IN_PROGRESS":
                return {"id": aid, "status": a.result_status, "reason": a.result_reason}
            if runtime.attempt_id != aid:
                raise HTTPException(409, "ไม่ใช่ครั้งที่กำลังบันทึก")
            # Freeze samples; a failed database commit can retry the exact same evidence.
            runtime.collecting = False
            samples = list(runtime.samples)
            s = require(db, TrainingSession, a.session_id)
            c = require(db, Criteria, s.criteria_id)
            exercise = require(db, Exercise, c.exercise_id)
            config = s.configuration_snapshot
            try:
                recorded_videos = runtime.finish_recording() if config.get("record_frames") else {}
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc
            measured = summarize(
                samples,
                config["baseline_seconds"],
                config.get("min_valid_frames", 5),
                config.get("min_valid_ratio", 0.7),
            )
            m2_evidence = None
            if exercise.module_id == 2:
                measured, m2_evidence = assess_follow_through(samples, config)
            balls, events = ball_metrics(samples, config, exercise.setup_definition)
            measured.update(balls)
            m1_evidence = None
            if exercise.module_id == 1:
                m1_status, m1_reason, m1_values, m1_evidence = assess_m1(
                    samples,
                    c.definition,
                    config["baseline_seconds"],
                    config.get("min_valid_frames", 5),
                )
                measured.update(m1_values)
            if body.aborted:
                status, reason = "ABORTED", "ผู้ฝึกยุติก่อนจบ"
            elif runtime.error:
                status, reason = "INVALID", runtime.error
            elif config["mode"] == "DEMO":
                status, reason = "INVALID", "ข้อมูลสาธิต ไม่ใช่ผลฝึกจริง"
            elif exercise.module_id == 1:
                status, reason = m1_status, m1_reason
            elif exercise.module_id == 2 and m2_evidence["state"] != "READY":
                status, reason = "INVALID", m2_evidence["reason"]
            elif exercise.module_id == 3 and measured.get("contact_fraction") is None:
                status, reason = (
                    "INVALID",
                    next(
                        (event.get("reason_th") for event in events if event.get("reason_th")),
                        "หลักฐานลูกหรือการกระทบไม่ครบ กรุณาตรวจภาพและทดลองใหม่",
                    ),
                )
            else:
                active_duration = (
                    max(0, samples[-1]["t"] - samples[0]["t"] - config["baseline_seconds"])
                    if samples
                    else 0
                )
                if exercise.module_id == 2:
                    active_duration = m2_evidence.get("valid_active_seconds", 0.0)
                if exercise.module_id == 3:
                    active_duration = next(
                        (
                            event["valid_active_seconds"]
                            for event in events
                            if "valid_active_seconds" in event
                        ),
                        0.0,
                    )
                status, reason = evaluate(measured, c.definition, active_duration)
            a.result_status = status
            a.result_reason = reason
            a.ended_at = now()
            a.evidence = {
                "samples": samples,
                "events": events,
                "source": config["mode"],
                "videos": recorded_videos,
                "algorithm": "table-trial-m1-m3-v0.4",
                "segmentation": "ready-start-timed-stop"
                if config.get("m1_auto_seconds")
                else "manual-start-stop",
                "display_timing": body.display_timing.model_dump() if body.display_timing else None,
                "quality": {
                    **data_quality(samples, config["baseline_seconds"]),
                    **(
                        {
                            "recorded_frames": sum(
                                v["captured_frames"] for v in recorded_videos.values()
                            )
                        }
                        if recorded_videos
                        else {}
                    ),
                    "recording_error": runtime.recording_error
                    if config.get("record_frames")
                    else None,
                    "m1_frame_assessment": m1_evidence,
                    "m3_events": events if exercise.module_id == 3 else None,
                    "m2_assessment": m2_evidence,
                },
            }
            for metric in db.scalars(select(MetricDefinition)):
                metric_codes = LESSONS[exercise.module_id]["metrics"]
                if metric.code not in metric_codes:
                    continue
                value = measured.get(metric.code)
                if value is not None and not math.isfinite(value):
                    value = None
                db.add(
                    Measurement(
                        attempt_id=aid,
                        metric_id=metric.id,
                        value=value,
                        validity_status="VALID" if value is not None else "INVALID",
                        invalid_reason=None if value is not None else "ข้อมูลไม่พอหรือยังไม่มีวิธีวัดที่รองรับ",
                    )
                )
        runtime.attempt_id = None
        runtime.samples = []
    return {
        "id": aid,
        "status": status,
        "reason": reason,
        "metrics": measured,
        "feedback": feedback(measured, c.definition.get("rules")),
    }


@router.post("/api/sessions/{sid}/finish")
@serialized
def finish_session(sid: str, body: FinishRequest, user=Depends(current_user)):
    with DB() as db:
        owned_session(db, sid, user)
    with runtime.lock:
        with DB() as db:
            s = owned_session(db, sid, user)
            if s.status == "IN_PROGRESS" and not body.aborted:
                if runtime.session_id == sid and runtime.attempt_id:
                    raise HTTPException(409, "จบการบันทึกครั้งนี้ก่อนจบรอบ หรือเลือกยุติรอบ")
                result = detail(db, s)["protocol_result"]
                if result["purpose"] == "ASSESSMENT" and result["remaining"] not in (None, 0):
                    raise HTTPException(
                        409, f"ยังขาดผล PASS/FAIL อีก {result['remaining']} ครั้ง หากไม่ทำต่อให้เลือกยุติรอบ"
                    )
        if runtime.session_id == sid and runtime.attempt_id:
            finish_attempt(runtime.attempt_id, FinishRequest(aborted=True), user)
        with DB.begin() as db:
            s = require(db, TrainingSession, sid)
            if s.status == "IN_PROGRESS":
                s.status = "ABORTED" if body.aborted else "COMPLETED"
                s.ended_at = now()
        if runtime.session_id == sid:
            runtime.session_id = None
    return session_detail(sid, user)
