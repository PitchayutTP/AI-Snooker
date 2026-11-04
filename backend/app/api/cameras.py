"""Cameras API routes; public URLs remain unchanged."""

import hashlib
from copy import deepcopy
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..calibration_policy import (
    M2_CALIBRATION_LIMIT_MM,
    M3_CALIBRATION_LIMIT_MM,
    PRACTICE_BALL_RADIUS,
    PRACTICE_TABLE_SIZE,
    m3_calibration_accepted,
)
from ..colour import M3_BALL_COLOURS
from ..database import (
    DB,
    Exercise,
)
from ..lessons import LESSONS
from ..m2_follow_through import reference_geometry
from ..paths import BACKEND_ROOT
from ..pose_settings import M1_POSE_CONFIDENCE, m1_capture_defaults
from ..runtime import runtime
from .dependencies import current_user, require, serialized
from .schemas import CalibrationRequest, PreviewRequest, ReadyRequest

router = APIRouter()


@router.post("/api/readiness")
@serialized
def readiness(body: ReadyRequest, user=Depends(current_user)):
    # Do not hold the worker lock while joining the previous worker.
    if runtime.session_id:
        raise HTTPException(409, "ต้องจบรอบฝึกก่อนเปลี่ยนกล้อง")
    with DB() as db:
        exercise = require(db, Exercise, body.exercise_id)
        if exercise.module_id not in LESSONS:
            raise HTTPException(409, "prototype นี้ยังไม่เปิดแบบฝึกแก้สนุก")
        config = body.config.model_dump()
        if exercise.module_id == 1:
            config = m1_capture_defaults(config, body.config.model_fields_set)
            config["pose_pipeline"] = {
                "version": "m1-full-quality-v1",
                "pose_confidence": M1_POSE_CONFIDENCE,
                "landmark_visibility": config["visibility"],
                "minimum_segment": "max(20px, 3% of shorter image side)",
                "measurement_space": "image_pixels_2d",
                "fine_tuned_for_snooker": False,
            }
        config.update(
            required=["side"] if exercise.module_id == 1 else ["top"], exercise_id=exercise.id
        )
        if (
            exercise.module_id in (2, 3)
            and config["table_size"]
            and (
                config["table_size"] != list(PRACTICE_TABLE_SIZE)
                or config["ball_radius"] != PRACTICE_BALL_RADIUS
            )
        ):
            raise HTTPException(
                422, "พื้นที่ฝึกกำหนดเป็น 1500 × 750 มม. รัศมีลูก 26.25 มม. กรุณาเลือกจุดสอบเทียบใหม่"
            )
        if config["m1_auto_seconds"] and exercise.module_id != 1:
            raise HTTPException(422, "การบันทึกอัตโนมัติใช้เฉพาะ M1")
        if exercise.module_id == 2:
            config["m2_mode"] = "RED_GATE3"
            config["max_frame_gap_s"] = max(config["max_frame_gap_s"], 0.35)
            if "cue_ball_colour" not in body.config.model_fields_set:
                config["cue_ball_colour"] = "BLUE"
                if "ball_colours" not in body.config.model_fields_set:
                    config["ball_colours"] = deepcopy(M3_BALL_COLOURS)
            if not config["cue_markers"]:
                raise HTTPException(422, "M2 ต้องเลือกสีมาร์กเกอร์ใกล้ปลายคิวหนึ่งจุด")
            config["cue_markers"] = config["cue_markers"][:1]
            marker = config["cue_markers"][0]
            if any(
                all(
                    max(a, c) <= min(b, d)
                    for a, b, c, d in zip(
                        marker["lower"], marker["upper"], colour["lower"], colour["upper"]
                    )
                )
                for colour in config["ball_colours"]["cue_ball"]
            ):
                raise HTTPException(422, "สีมาร์กเกอร์ซ้อนกับสีลูกที่ใช้แทง เลือกมาร์กเกอร์สีอื่น เช่น สีเหลือง")
            if config["m2_tip_offset_mm"] is None:
                raise HTTPException(422, "กรอกระยะจากศูนย์กลางมาร์กเกอร์ด้านหน้าไปถึงหัวคิว (มม.)")
            if (
                not config["homography"]
                or not config["table_size"]
                or not config["ball_radius"]
                or not config["calibration_image_size"]
            ):
                raise HTTPException(422, "สอบเทียบพื้นที่กล้องบนก่อนวัดระยะ Follow-through")
            if (
                config.get("calibration_check_error") is not None
                and config["calibration_check_error"] > M2_CALIBRATION_LIMIT_MM
            ):
                raise HTTPException(422, "จุดสอบเทียบ M2 คลาดเคลื่อนเกิน 20 มม. กรุณาสอบเทียบใหม่")
            config["calibration_check_limit_mm"] = M2_CALIBRATION_LIMIT_MM
            try:
                reference_geometry(config)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            config["delivery_pipeline_version"] = "m2-red-gate-single-v3"
        if exercise.module_id == 3:
            config["target_fraction"] = exercise.setup_definition["fraction"]
            if "ball_min_area" not in body.config.model_fields_set:
                config["ball_min_area"] = 12.0
            if config["ball_radius"] and not config["motion_threshold"]:
                config["motion_threshold"] = config["ball_radius"] * 0.2
            error = config.get("calibration_check_error")
            if not m3_calibration_accepted(error):
                raise HTTPException(422, "จุดตรวจสอบคลาดเคลื่อนเกิน 50 มม. กรุณาสอบเทียบใหม่")
            config["calibration_check_limit_mm"] = M3_CALIBRATION_LIMIT_MM
            config["calibration_quality"] = (
                "UNKNOWN"
                if error is None
                else "PILOT_RELAXED"
                if error > config["ball_radius"] * 0.25
                else "PILOT"
            )
            config["max_frame_gap_s"] = max(config["max_frame_gap_s"], 0.35)
            config["m3_brief_loss_seconds"] = 0.35
            config["m3_max_missing_frames"] = 6
            config["m3_stationary_loss_seconds"] = 1.0
            config["ball_pipeline_version"] = "m3-hsv-delivery-recovery-v5"
        config["software_version"] = "table-trial-m1-m3-v0.4"
        if config["mode"] == "LIVE":
            hashes = {}
            model = Path(config["pose_model"])
            if not model.is_absolute():
                model = BACKEND_ROOT / model
            if "side" in config["required"] and model.is_file():
                with open(model, "rb") as model_file:
                    hashes["pose_model"] = hashlib.file_digest(model_file, "sha256").hexdigest()
            config["model_sha256"] = hashes
        if config["mode"] == "LIVE" and "top" in config["required"]:
            if not config["homography"] or not config["table_size"] or not config["ball_radius"]:
                raise HTTPException(422, "กรุณาระบุ homography ขนาดโต๊ะ และรัศมีลูกในหน่วยเดียวกัน")
        try:
            runtime.stop()
            with runtime.lock:
                runtime.owner_profile_id = user["profile_id"]
            runtime.start(config)
        except Exception as exc:
            raise HTTPException(400, str(exc)) from exc
    return {"status": "STARTING", "note": "รอสถานะพร้อมจากภาพจริงก่อนเริ่มรอบ"}


@router.post("/api/cameras/preview")
@serialized
def camera_preview(body: PreviewRequest, user=Depends(current_user)):
    if runtime.session_id:
        raise HTTPException(409, "จบรอบฝึกก่อนเปิดภาพตั้งค่า")
    if body.detect_balls and body.camera != "top":
        raise HTTPException(422, "ทดลองตรวจจับสีลูกจากกล้องด้านบนเท่านั้น")
    runtime.stop()
    config = body.config.model_dump()
    config.update(
        mode="LIVE",
        preview_only=True,
        preview_camera=body.camera,
        detect_ball_preview=body.detect_balls,
    )
    with runtime.lock:
        runtime.owner_profile_id = user["profile_id"]
    try:
        runtime.start(config)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"status": "PREVIEW", "camera": body.camera}


@router.post("/api/cameras/stop")
@serialized
def camera_stop(user=Depends(current_user)):
    with runtime.lock:
        if runtime.owner_profile_id not in (None, user["profile_id"]):
            raise HTTPException(409, "กล้องถูกใช้งานโดยบัญชีอื่น")
        if runtime.session_id:
            raise HTTPException(409, "จบรอบฝึกก่อนปิดกล้อง")
    runtime.stop()
    with runtime.lock:
        runtime.config = {}
        runtime.error = None
        runtime.owner_profile_id = None
    return {"status": "STOPPED"}


@router.post("/api/calibration")
def calibration(body: CalibrationRequest):
    if (
        len(body.image_points) != 4
        or any(len(p) != 2 for p in body.image_points)
        or len(body.check_image_point) != 2
        or len(body.check_table_point) != 2
    ):
        raise HTTPException(422, "ต้องมีมุมโต๊ะ 4 จุดและจุดตรวจสอบอิสระ 1 จุด")
    try:
        from ..calibration import calibrate

        return calibrate(
            {
                "image_points": body.image_points,
                "table_points": [
                    [0, 0],
                    [body.table_width, 0],
                    [body.table_width, body.table_height],
                    [0, body.table_height],
                ],
                "check_image_points": [body.check_image_point],
                "check_table_points": [body.check_table_point],
            }
        )
    except ImportError:
        raise HTTPException(400, "ต้องติดตั้ง backend/requirements-camera.txt ก่อนสอบเทียบ")
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
