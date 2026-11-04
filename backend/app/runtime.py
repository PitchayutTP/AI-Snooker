import threading
import time

from .cameras import PreviewSource
from .m1_assessment import apply_readiness
from .m2_follow_through import (
    FollowThroughMonitor,
    FollowThroughPreparation,
    FollowThroughSource,
)
from .m3_monitor import M3Monitor
from .m3_readiness import M3Preparation
from .recordings import VideoRecorder
from .smoothing import MovingAverage
from .vision import LiveSource


class Runtime:
    def __init__(self):
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = None
        self.latest = None
        self.samples = []
        self.collecting = False
        self.owner_profile_id = None
        self.config = {}
        self.error = None
        self.session_id = None
        self.attempt_id = None
        self.smoother = None
        self.recorder = None
        self.recording_error = None
        self.recorded_videos = {}
        self.recording_limit_reached = False
        self.m2_monitor = None
        self.m3_monitor = None

    def start(self, config):
        self.stop()
        delivery = config.get("exercise_id") == 2
        source = (
            PreviewSource(config)
            if config.get("preview_only")
            else FollowThroughSource(config)
            if delivery
            else LiveSource(config)
        )
        self.stop_event.clear()
        self.config = config
        self.error = None
        self.latest = None
        m1 = (
            config.get("exercise_id") == 1
            and config.get("mode") == "LIVE"
            and not config.get("preview_only")
        )
        smoothing_gap = (
            config.get("smoothing_max_gap_s", 0.25) if m1 else config.get("max_frame_gap_s", 0.25)
        )
        smoother = MovingAverage(
            config.get("smoothing_window", 1),
            smoothing_gap,
            config.get("smoothing_method", "MEAN"),
            config.get("smoothing_tau_seconds", 0.35),
            display_deadband=0.25 if m1 else 0,
        )
        self.smoother = smoother
        m3 = (
            M3Preparation(config)
            if config.get("exercise_id") in (3, 4, 5, 6) and not config.get("preview_only")
            else None
        )
        self.m3_monitor = M3Monitor() if m3 else None
        m2 = (
            FollowThroughPreparation(config)
            if delivery and not config.get("preview_only")
            else None
        )
        self.m2_monitor = FollowThroughMonitor() if m2 else None

        def worker():
            try:
                last = time.monotonic()
                while not self.stop_event.is_set():
                    sample = source.read()
                    stamp = time.monotonic()
                    sample["fps"] = 1 / max(0.001, stamp - last)
                    last = stamp
                    sample["received_at"] = time.time()
                    with self.lock:
                        if not config.get("preview_only"):
                            smoother.apply(sample)
                        if m1:
                            apply_readiness(sample, self.attempt_id is not None)
                        if m3:
                            m3.apply(sample, self.attempt_id is not None)
                        if m2:
                            m2.apply(sample, self.attempt_id is not None)
                        raw = sample.pop("_raw_frames", {})
                        if self.collecting and self.recorder and len(self.samples) < 6000:
                            recording_start = time.monotonic()
                            try:
                                self.recorder.write(raw, sample["t"])
                            except (OSError, ValueError) as exc:
                                self.recording_error = str(exc)
                            sample["recording_ms"] = (time.monotonic() - recording_start) * 1000
                        self.latest = sample
                        if self.collecting:
                            if len(self.samples) >= 6000:
                                self.error = "จำนวนเฟรมเกินขีดจำกัด กรุณาจบครั้งหรือยกเลิก"
                                self.collecting = False
                            else:
                                record = {
                                    k: v
                                    for k, v in sample.items()
                                    if k not in ("image", "images", "elbow_preview")
                                }
                                if not config.get("smoothing_for_evaluation", False):
                                    record.update(sample.get("raw_measurements", {}))
                                self.samples.append(record)
                                if self.m2_monitor:
                                    sample["m2_trial"] = dict(
                                        self.m2_monitor.update(self.samples, self.config)
                                    )
                                    record["m2_trial"] = sample["m2_trial"]
                                if self.m3_monitor:
                                    sample["m3_trial"] = dict(
                                        self.m3_monitor.update(self.samples, self.config)
                                    )
                                    record["m3_trial"] = sample["m3_trial"]
                                if (
                                    self.config.get("m1_auto_seconds")
                                    and self.samples[-1]["t"] - self.samples[0]["t"]
                                    >= self.config["m1_auto_seconds"]
                                ):
                                    self.recording_limit_reached = True
                                    self.collecting = False
                    if sample.get("error"):
                        self.error = sample.get("error")
                        break
                    self.stop_event.wait(0.1 if config.get("preview_only") else 0.001)
            except Exception as exc:
                self.error = str(exc)
            finally:
                source.close()

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()

    def snapshot(self):
        with self.lock:
            frame = dict(self.latest or {})
            fresh = bool(frame) and time.time() - frame.get("received_at", 0) < 2 and not self.error
            issues = list(frame.get("readiness_issues", []))
            if not fresh:
                issues = [
                    self.error
                    or ("ภาพจากกล้องไม่อัปเดต กรุณาตรวจความพร้อมอีกครั้ง" if frame else "กำลังรอภาพจากกล้อง")
                ]
                frame = {k: None for k in ["elbow", "head", "bridge", "knee_shooting", "image"]}
            live = {}
            if fresh and self.samples:
                elapsed = frame["t"] - self.samples[0]["t"]
                baseline = [
                    row
                    for row in self.samples
                    if row["t"] - self.samples[0]["t"] <= self.config.get("baseline_seconds", 1)
                ]
                live["baseline_ready"] = elapsed > self.config.get("baseline_seconds", 1) and len(
                    baseline
                ) >= self.config.get("min_valid_frames", 5)
            return {
                "live_metrics": live,
                "frame": frame,
                "ready": fresh and bool(self.latest.get("ready")),
                "readiness_issues": issues,
                "error": self.error,
                "mode": self.config.get("mode"),
                "configuration": dict(self.config),
                "session_id": self.session_id,
                "attempt_id": self.attempt_id,
                "attempt_elapsed_s": max(0, self.samples[-1]["t"] - self.samples[0]["t"])
                if len(self.samples) > 1
                else 0,
                "recording_limit_reached": self.recording_limit_reached,
                "samples": len(self.samples),
                "collecting": self.collecting,
                "recording_error": self.recording_error,
            }

    def begin(self, attempt_id):
        with self.lock:
            if self.smoother:
                self.smoother.reset()
            if self.m2_monitor:
                self.m2_monitor.reset()
            if self.m3_monitor:
                self.m3_monitor.reset()
            self.samples = []
            self.attempt_id = attempt_id
            self.collecting = True
            self.recording_limit_reached = False
            if self.recorder:
                self.finish_recording()
            self.recording_error = None
            self.recorded_videos = {}
            self.recorder = None
            if self.config.get("record_frames") and self.config.get("mode") == "LIVE":
                try:
                    self.recorder = VideoRecorder(
                        self.owner_profile_id, self.session_id, attempt_id
                    )
                except (OSError, ValueError):
                    self.recording_error = "เปิดไฟล์วิดีโอไม่ได้ ผลการฝึกยังประเมินต่อได้"

    def finish_recording(self):
        if self.recorder:
            self.recorded_videos = self.recorder.close()
            if self.recorder.error:
                self.recording_error = self.recorder.error
            self.recorder = None
        return dict(self.recorded_videos)

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                raise ValueError("กล้องยังไม่หยุด กรุณาปิดและเปิด Backend ใหม่")
        self.thread = None
        self.collecting = False
        self.finish_recording()
        with self.lock:
            self.latest = None


runtime = Runtime()
