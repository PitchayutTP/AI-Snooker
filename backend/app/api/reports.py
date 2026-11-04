"""Reports API routes; public URLs remain unchanged."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import delete, func, select
from starlette.background import BackgroundTask

from ..database import DB, METRICS, Attempt, Measurement, TrainingSession
from ..recordings import RECORDINGS
from ..repositories.report_queries import (
    compact_sessions,
    practice_progress,
)
from ..runtime import runtime
from ..services.reporting import detail
from ..training_reset import cleanup_recordings, recording_cleanup_plan
from .dependencies import current_user, owned_session, require, serialized
from .schemas import DeleteSessionRequest, ResetTrainingRequest

router = APIRouter()


@router.get("/api/sessions")
def sessions(compact: bool = False, user=Depends(current_user)):
    with DB() as db:
        if compact:
            return compact_sessions(db, user["profile_id"])
        return [
            detail(db, s)
            for s in db.scalars(
                select(TrainingSession)
                .where(TrainingSession.profile_id == user["profile_id"])
                .order_by(TrainingSession.started_at.desc())
                .limit(100)
            )
        ]


@router.get("/api/sessions/{sid}")
def session_detail(sid: str, user=Depends(current_user)):
    with DB() as db:
        return detail(db, owned_session(db, sid, user))


@router.get("/api/attempts/{aid}/clip.webm")
def attempt_clip(aid: str, user=Depends(current_user)):
    from ..recordings import recorded_video_path, render_clip

    with DB() as db:
        attempt = require(db, Attempt, aid)
        session = owned_session(db, attempt.session_id, user)
        camera = "side" if session.configuration_snapshot.get("exercise_id") == 1 else "top"
        samples = attempt.evidence.get("samples", [])
        video = attempt.evidence.get("videos", {}).get(camera)
    if video:
        try:
            path = recorded_video_path(video["path"], user["profile_id"])
        except (KeyError, ValueError):
            raise HTTPException(404, "ไม่พบไฟล์วิดีโอ")
        if not path.is_file():
            raise HTTPException(404, "ไฟล์วิดีโอถูกย้ายหรือลบแล้ว")
        return FileResponse(
            path, media_type="video/webm", headers={"Cache-Control": "private, no-store"}
        )
    try:
        path = render_clip(samples, user["profile_id"], camera)
    except FileNotFoundError:
        raise HTTPException(404, "ไม่มีภาพบันทึกของครั้งฝึกนี้")
    except (RuntimeError, ValueError, OSError):
        raise HTTPException(503, "สร้างคลิปไม่ได้ ลองดาวน์โหลด ZIP ภาพดิบจากหน้าสรุปผล")
    return FileResponse(
        path,
        media_type="video/webm",
        headers={"Cache-Control": "private, no-store"},
        background=BackgroundTask(path.unlink, missing_ok=True),
    )


@router.get("/api/sessions/{sid}/export")
def export(sid: str, user=Depends(current_user)):
    with DB() as db:
        result = detail(db, owned_session(db, sid, user))
        result["evidence"] = [
            {"attempt_id": a.id, **a.evidence}
            for a in db.scalars(select(Attempt).where(Attempt.session_id == sid))
        ]
    return Response(
        json.dumps(result, ensure_ascii=False, allow_nan=False),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="session.json"'},
    )


@router.post("/api/sessions/{sid}/delete")
@serialized
def delete_training_session(sid: UUID, body: DeleteSessionRequest, user=Depends(current_user)):
    sid = str(sid)
    with DB.begin() as db:
        session = db.get(TrainingSession, sid)
        if session is not None:
            owned_session(db, sid, user)
            if session.status == "IN_PROGRESS":
                raise HTTPException(409, "จบหรือยุติรอบฝึกนี้ก่อนลบ")
        with runtime.lock:
            if runtime.session_id == sid:
                raise HTTPException(409, "จบหรือยุติรอบฝึกนี้ก่อนลบ")
        try:
            recording_cleanup_plan(RECORDINGS, user["profile_id"], sid)
        except (ValueError, OSError) as exc:
            raise HTTPException(409, "ตรวจโฟลเดอร์หลักฐานของรอบนี้ไม่สำเร็จ ยังไม่ได้ลบข้อมูล") from exc
        measurements = attempts = sessions = 0
        if session is not None:
            owned_ids = select(TrainingSession.id).where(
                TrainingSession.id == sid, TrainingSession.profile_id == user["profile_id"]
            )
            attempt_ids = select(Attempt.id).where(Attempt.session_id.in_(owned_ids))
            measurements = db.execute(
                delete(Measurement).where(Measurement.attempt_id.in_(attempt_ids))
            ).rowcount
            attempts = db.execute(delete(Attempt).where(Attempt.session_id.in_(owned_ids))).rowcount
            sessions = db.execute(
                delete(TrainingSession).where(TrainingSession.id.in_(owned_ids))
            ).rowcount
    # A retry can finish cleanup after the database row was already deleted.
    try:
        files = cleanup_recordings(RECORDINGS, user["profile_id"], sid)
    except (ValueError, OSError):
        files = {"images_removed": 0, "cleanup_complete": False}
    return {
        "session_id": sid,
        "sessions_removed": sessions,
        "attempts_removed": attempts,
        "measurements_removed": measurements,
        **files,
    }


@router.get("/api/compare")
def compare(left: str, right: str, user=Depends(current_user)):
    a = session_detail(left, user)
    b = session_detail(right, user)
    if a["status"] == "IN_PROGRESS" or b["status"] == "IN_PROGRESS":
        raise HTTPException(409, "จบรอบก่อนเปรียบเทียบ")
    if a["criteria_id"] != b["criteria_id"] or a["config"] != b["config"]:
        raise HTTPException(409, "แบบฝึก รุ่นเกณฑ์ หรือการตั้งค่าต่างกัน จึงไม่เปรียบเทียบโดยตรง")
    return {
        "left": a["id"],
        "right": b["id"],
        "mode": a["mode"],
        "note": "ความต่างของค่าวัดไม่ยืนยันว่าทักษะดีขึ้น",
        "metrics": {
            k: {
                "left": a["summary"][k],
                "right": b["summary"][k],
                "difference": b["summary"][k]["mean"] - a["summary"][k]["mean"]
                if a["summary"][k]["mean"] is not None and b["summary"][k]["mean"] is not None
                else None,
            }
            for k in METRICS
        },
    }


@router.get("/api/sessions/{sid}/evidence.zip")
def evidence_bundle(sid: str, user=Depends(current_user)):
    import tempfile
    from zipfile import ZIP_STORED, ZipFile

    from ..recordings import ROOT, recorded_path, recorded_video_path

    data = json.loads(export(sid, user).body)
    directory = ROOT / "data/exports"
    directory.mkdir(parents=True, exist_ok=True)
    stream = tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024, dir=directory)
    included = missing = included_videos = missing_videos = 0
    try:
        with ZipFile(stream, "w", ZIP_STORED) as bundle:
            for evidence in data["evidence"]:
                videos = {}
                for camera, video in evidence.get("videos", {}).items():
                    if camera not in ("side", "top"):
                        continue
                    path = recorded_video_path(video["path"], user["profile_id"])
                    if not path.is_file():
                        missing_videos += 1
                        continue
                    name = f"recordings/{evidence['attempt_id']}/{camera}.webm"
                    bundle.write(path, name)
                    videos[camera] = {**video, "path": name}
                    included_videos += 1
                evidence["videos"] = videos
                for index, sample in enumerate(evidence.get("samples", [])):
                    paths = {}
                    for camera, value in sample.get("recorded_images", {}).items():
                        if camera not in ("side", "top"):
                            continue
                        path = recorded_path(value, user["profile_id"])
                        if not path.is_file():
                            missing += 1
                            continue
                        name = f"recordings/{evidence['attempt_id']}/{camera}/{index:06d}.jpg"
                        bundle.write(path, name)
                        paths[camera] = name
                        included += 1
                    sample["recorded_images"] = paths
            data["bundle_summary"] = {
                "included_images": included,
                "missing_images": missing,
                "included_videos": included_videos,
                "missing_videos": missing_videos,
            }
            bundle.writestr("session.json", json.dumps(data, ensure_ascii=False, allow_nan=False))
        stream.seek(0)
    except Exception:
        stream.close()
        raise

    def chunks():
        try:
            while chunk := stream.read(1024 * 1024):
                yield chunk
        finally:
            stream.close()

    return StreamingResponse(
        chunks(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="trial-evidence.zip"'},
    )


@router.get("/api/progress")
def progress(user=Depends(current_user)):
    with DB() as db:
        return practice_progress(db, user["profile_id"])


@router.get("/api/training/reset-summary")
def training_reset_summary(user=Depends(current_user)):
    with DB() as db:
        session_ids = select(TrainingSession.id).where(
            TrainingSession.profile_id == user["profile_id"]
        )
        sessions = db.scalar(
            select(func.count())
            .select_from(TrainingSession)
            .where(TrainingSession.profile_id == user["profile_id"])
        )
        attempts = db.scalar(
            select(func.count()).select_from(Attempt).where(Attempt.session_id.in_(session_ids))
        )
    try:
        files, _ = recording_cleanup_plan(RECORDINGS, user["profile_id"])
    except (ValueError, OSError) as exc:
        raise HTTPException(
            409, "ไม่สามารถตรวจโฟลเดอร์ภาพหลักฐานได้ กรุณาตรวจสิทธิ์และโครงสร้างโฟลเดอร์ก่อนรีเซ็ต"
        ) from exc
    return {"sessions": sessions, "attempts": attempts, "images": len(files)}


@router.post("/api/training/reset")
@serialized
def reset_training(body: ResetTrainingRequest, user=Depends(current_user)):
    with runtime.lock:
        if runtime.session_id or runtime.attempt_id:
            raise HTTPException(409, "กรุณาจบหรือยุติรอบฝึกก่อนล้างประวัติ")
        own_capture = runtime.owner_profile_id == user["profile_id"]
    try:
        recording_cleanup_plan(RECORDINGS, user["profile_id"])
    except (ValueError, OSError) as exc:
        raise HTTPException(409, "ไม่สามารถตรวจโฟลเดอร์ภาพหลักฐานได้ ยังไม่ได้ลบข้อมูล") from exc
    if own_capture:
        runtime.stop()
    with DB.begin() as db:
        session_ids = select(TrainingSession.id).where(
            TrainingSession.profile_id == user["profile_id"]
        )
        attempt_ids = select(Attempt.id).where(Attempt.session_id.in_(session_ids))
        measurements = db.execute(
            delete(Measurement).where(Measurement.attempt_id.in_(attempt_ids))
        ).rowcount
        attempts = db.execute(delete(Attempt).where(Attempt.session_id.in_(session_ids))).rowcount
        sessions = db.execute(
            delete(TrainingSession).where(TrainingSession.profile_id == user["profile_id"])
        ).rowcount
    if own_capture:
        with runtime.lock:
            runtime.samples = []
            runtime.latest = None
            runtime.recorder = None
            runtime.error = None
            runtime.recording_limit_reached = False
            runtime.config = {}
            runtime.owner_profile_id = None
    try:
        images = cleanup_recordings(RECORDINGS, user["profile_id"])
    except (ValueError, OSError):
        images = {"images_removed": 0, "cleanup_complete": False}
    return {
        "sessions_removed": sessions,
        "attempts_removed": attempts,
        "measurements_removed": measurements,
        **images,
    }
