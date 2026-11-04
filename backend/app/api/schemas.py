"""Validated request contracts shared by API routes."""

import math
from copy import deepcopy
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from ..colour import DEFAULT_BALL_COLOURS, M3_BALL_COLOURS


class CaptureConfig(BaseModel):
    m1_auto_seconds: Literal[0, 8] = 0
    mode: Literal["LIVE"] = "LIVE"
    hand: Literal["LEFT", "RIGHT"] = "RIGHT"
    side_source: str = "0"
    top_source: str = "1"
    camera_backend: Literal["AUTO", "DSHOW", "MSMF"] = "AUTO"
    camera_mjpeg: bool = False
    capture_width: int = Field(default=1280, ge=320, le=3840)
    capture_height: int = Field(default=720, ge=240, le=2160)
    capture_fps: int = Field(default=30, ge=5, le=120)
    calibration_image_size: list[int] = Field(default_factory=list)
    pose_model: str = "models/pose_landmarker_full.task"
    ball_detector: Literal["HSV"] = "HSV"
    cue_ball_colour: Literal["WHITE", "BLUE"] = "WHITE"
    ball_colours: dict[str, list[dict]] = Field(
        default_factory=lambda: deepcopy(DEFAULT_BALL_COLOURS)
    )
    ball_min_area: float = Field(default=50, gt=0, allow_inf_nan=False)
    ball_max_area: float = Field(default=5000, gt=0, allow_inf_nan=False)
    ball_max_jump: float = Field(default=120, gt=0, allow_inf_nan=False)
    visibility: float = Field(default=0.7, ge=0, le=1, allow_inf_nan=False)
    baseline_seconds: float = Field(default=1.0, ge=0.5, le=10, allow_inf_nan=False)
    smoothing_window: int = Field(default=1, ge=1, le=31)
    smoothing_method: Literal["MEAN", "MEDIAN_EMA"] = "MEAN"
    smoothing_tau_seconds: float = Field(default=0.35, ge=0.05, le=2, allow_inf_nan=False)
    smoothing_max_gap_s: float = Field(default=0.25, gt=0, le=2, allow_inf_nan=False)
    smoothing_for_evaluation: bool = False
    record_frames: bool = False
    min_valid_frames: int = Field(default=5, ge=2, le=1000)
    min_valid_ratio: float = Field(default=0.7, gt=0, le=1, allow_inf_nan=False)
    homography: list[list[float]] | None = None
    table_size: list[float] = Field(default_factory=list)
    ball_radius: float = Field(default=0, ge=0, allow_inf_nan=False)
    calibration_check_error: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    contact_tolerance: float = Field(default=0, ge=0, allow_inf_nan=False)
    max_frame_gap_s: float = Field(default=0.25, gt=0, le=5, allow_inf_nan=False)
    m2_mode: Literal["RED_GATE3"] = "RED_GATE3"
    m2_tip_offset_mm: float | None = Field(default=None, ge=0, le=1000, allow_inf_nan=False)
    m2_red_points: list[list[float]] = Field(default_factory=list)
    motion_threshold: float = Field(default=0, ge=0, allow_inf_nan=False)
    cue_markers: list[dict] = Field(default_factory=list)
    setup_notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def geometry(self):
        if self.cue_ball_colour == "BLUE" and "ball_colours" not in self.model_fields_set:
            self.ball_colours = deepcopy(M3_BALL_COLOURS)
        if self.m2_red_points and (
            len(self.m2_red_points) != 6
            or any(len(p) != 2 or any(not math.isfinite(x) for x in p) for p in self.m2_red_points)
        ):
            raise ValueError("m2_red_points ต้องเป็นพิกัดลูกแดงซ้าย 1–3 ขวา 1–3 รวม 6 จุด")
        for size in [self.calibration_image_size]:
            if size and (len(size) != 2 or any(x <= 0 for x in size)):
                raise ValueError("ขนาดภาพต้องเป็น [width,height] มากกว่าศูนย์")
        if self.ball_min_area >= self.ball_max_area:
            raise ValueError("ball_min_area ต้องน้อยกว่า ball_max_area")
        if self.ball_detector == "HSV":
            if set(self.ball_colours) != {"cue_ball", "target_ball"}:
                raise ValueError("HSV ต้องกำหนดลูกที่ใช้แทงและลูกเป้าอย่างละหนึ่งบทบาท")
            for ranges in self.ball_colours.values():
                if not ranges or len(ranges) > 4:
                    raise ValueError("ต้องมีช่วงสี 1–4 ช่วงต่อบทบาท")
                for bounds in ranges:
                    lo, hi = bounds.get("lower", []), bounds.get("upper", [])
                    if len(lo) != 3 or len(hi) != 3 or any(type(x) is not int for x in lo + hi):
                        raise ValueError("HSV ต้องเป็นจำนวนเต็มสามค่า")
                    if any(
                        a < 0 or b > limit or a > b for a, b, limit in zip(lo, hi, [179, 255, 255])
                    ):
                        raise ValueError("ช่วง HSV ไม่ถูกต้อง")
        if self.homography is not None:
            import numpy as np

            h = np.asarray(self.homography, dtype=float)
            if h.shape != (3, 3) or not np.isfinite(h).all() or abs(np.linalg.det(h)) < 1e-12:
                raise ValueError("homography ต้องเป็นเมทริกซ์ 3x3 ที่ผกผันได้")
        if self.table_size and (
            len(self.table_size) != 2
            or any(not math.isfinite(x) or x <= 0 for x in self.table_size)
        ):
            raise ValueError("table_size ต้องเป็นความกว้างและความสูงมากกว่าศูนย์")
        if self.cue_markers:
            if len(self.cue_markers) not in (1, 2):
                raise ValueError("เลือกมาร์กเกอร์ปลายคิวหนึ่งจุด")
            for marker in self.cue_markers:
                for k in ["lower", "upper"]:
                    v = marker.get(k, [])
                    if len(v) != 3 or any(
                        type(x) is not int or x < 0 or x > limit
                        for x, limit in zip(v, [179, 255, 255])
                    ):
                        raise ValueError("HSV bounds ไม่ถูกต้อง")
                if any(a > b for a, b in zip(marker["lower"], marker["upper"])):
                    raise ValueError("HSV lower > upper")
                area = marker.get("min_area", 10)
                if type(area) not in (float, int) or not math.isfinite(area) or area <= 0:
                    raise ValueError("พื้นที่ marker ต้องมากกว่าศูนย์")
        return self


class ReadyRequest(BaseModel):
    exercise_id: int
    config: CaptureConfig


class StartRequest(BaseModel):
    request_id: UUID
    criteria_id: int
    purpose: Literal["PILOT", "ASSESSMENT"] = "PILOT"


class AttemptRequest(BaseModel):
    request_id: UUID


class DisplayTiming(BaseModel):
    n: int = Field(ge=0, le=6000)
    median_ms: float = Field(ge=0, allow_inf_nan=False)
    p95_ms: float = Field(ge=0, allow_inf_nan=False)
    max_ms: float = Field(ge=0, allow_inf_nan=False)
    clock_uncertainty_ms: float = Field(ge=0, allow_inf_nan=False)


class FinishRequest(BaseModel):
    aborted: bool = False
    display_timing: DisplayTiming | None = None


class Rule(BaseModel):
    min: float | None = Field(default=None, allow_inf_nan=False)
    max: float | None = Field(default=None, allow_inf_nan=False)

    @model_validator(mode="after")
    def bounds(self):
        if self.min is None and self.max is None:
            raise ValueError("ต้องระบุ min หรือ max")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min > max")
        return self


class TrialProtocol(BaseModel):
    required_valid_attempts: int = Field(ge=1, le=1000)
    minimum_pass_rate: float = Field(gt=0, le=1, allow_inf_nan=False)
    rationale: str = Field(min_length=5, max_length=1000)


class CriteriaRequest(BaseModel):
    validation_scope: Literal["REPORT", "PROTOTYPE"] = "REPORT"
    template_version: str | None = Field(default=None, min_length=1, max_length=60)
    source: str = Field(min_length=5, max_length=1000)
    approved: bool = False
    rules: dict[str, Rule]
    frame_rules: dict[Literal["forearm_tilt", "knee_shooting"], Rule] | None = None
    minimum_valid_frame_ratio: float | None = Field(default=None, gt=0, le=1, allow_inf_nan=False)
    preparation_lean_min: float | None = Field(default=None, ge=0, le=90, allow_inf_nan=False)
    protocol: TrialProtocol | None = None
    minimum_active_seconds: float | None = Field(default=None, ge=0, le=600, allow_inf_nan=False)


class DeleteSessionRequest(BaseModel):
    confirmation: Literal["DELETE_SESSION"]


class PreviewRequest(BaseModel):
    camera: Literal["side", "top"]
    config: CaptureConfig
    detect_balls: bool = False


class ResetTrainingRequest(BaseModel):
    confirmation: Literal["RESET_TRAINING"]


class CalibrationRequest(BaseModel):
    image_points: list[list[float]]
    table_width: float = Field(gt=0, allow_inf_nan=False)
    table_height: float = Field(gt=0, allow_inf_nan=False)
    check_image_point: list[float]
    check_table_point: list[float]
