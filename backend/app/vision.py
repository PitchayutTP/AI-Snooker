"""Optional camera adapters. Heavy libraries load only in live mode."""

import time
from pathlib import Path

from .cameras import encode_image, open_camera
from .elbow_preview import ElbowPreview
from .pose import measure_pose
from .pose_settings import pose_options
from .smoothing import LandmarkAverage


class LiveSource:
    def __init__(self, config):
        import cv2

        self.cv2 = cv2
        self.config = config
        self.elbow_preview = ElbowPreview()
        self.pose_overlay = LandmarkAverage(
            config.get("smoothing_window", 1) if config["exercise_id"] == 1 else 1,
            config.get("smoothing_max_gap_s", 0.25)
            if config["exercise_id"] == 1
            else config.get("max_frame_gap_s", 0.25),
            config.get("smoothing_method", "MEAN") if config["exercise_id"] == 1 else "MEAN",
            config.get("smoothing_tau_seconds", 0.35),
            display_deadband=1.5 if config["exercise_id"] == 1 else 0,
        )
        self.caps = {}
        self.pose = None
        self.colour = None
        try:
            for name in config["required"]:
                source = config[f"{name}_source"]
                # Camera indices or video paths; files must be explicitly selected.
                cap = open_camera(cv2, source, config)
                self.caps[name] = cap
                if not cap.isOpened():
                    raise ValueError(f"เปิดกล้อง/วิดีโอ {name} ไม่ได้")
            if "side" in self.caps:
                import mediapipe as mp

                model = Path(config["pose_model"])
                if not model.is_absolute():
                    model = Path(__file__).resolve().parents[1] / model
                if not model.is_file():
                    raise ValueError("ไม่พบโมเดล Pose: รัน setup-camera.ps1 ที่โฟลเดอร์โปรเจกต์ก่อน")
                self.mp = mp
                self.pose = mp.tasks.vision.PoseLandmarker.create_from_options(
                    pose_options(mp, model, config["exercise_id"])
                )
                self.pose_model_name = model.name
            if "top" in self.caps:
                if not config.get("homography"):
                    raise ValueError("ต้องมี homography ของกล้องด้านบน")
                from .colour import ColourTracker

                self.colour = ColourTracker(
                    config["ball_colours"],
                    config["ball_min_area"],
                    config["ball_max_area"],
                    config["ball_max_jump"],
                    max(config["max_frame_gap_s"], config.get("m3_stationary_loss_seconds", 0)),
                    ball_radius=config.get("ball_radius"),
                    table_size=config.get("table_size"),
                    temporal_association=True,
                )
            self.ts = 0
        except Exception:
            self.close()
            raise

    def read(self):
        cv2 = self.cv2
        import numpy as np

        start = time.monotonic()
        sample = {
            "t": start,
            "capture_epoch_ms": time.time() * 1000,
            "source": "LIVE",
            "image": None,
            "balls": [],
            "cue": None,
            "elbow": None,
            "head": None,
            "bridge": None,
            "knee_shooting": None,
            "error": None,
            "ready": True,
        }
        frames = {}
        times = {}
        pose_issues = []
        # Grab all devices before decoding; timestamps describe receipt, not hardware sync.
        grabbed = {name: cap.grab() for name, cap in self.caps.items()}
        for name, cap in self.caps.items():
            ok, frame = cap.retrieve() if grabbed[name] else (False, None)
            times[name] = time.monotonic()
            if not ok:
                sample.update(ready=False, error=f"{name}: กล้องขาดการเชื่อมต่อหรือวิดีโอสิ้นสุด")
                return sample
            frames[name] = frame
            expected = self.config.get("calibration_image_size") if name == "top" else None
            if expected and list(expected) != [frame.shape[1], frame.shape[0]]:
                raise ValueError(f"ความละเอียดกล้อง {name} เปลี่ยน ต้องสอบเทียบ/เลือกจุดใหม่")
        sample["capture_ms"] = (time.monotonic() - start) * 1000
        if self.config.get("record_frames"):
            sample["_raw_frames"] = {name: frame.copy() for name, frame in frames.items()}
        sample["frame_receive_times"] = times
        if "side" in frames:
            frame = frames["side"]
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.ts = max(self.ts + 1, int(start * 1000))
            sample["pose_model_name"] = self.pose_model_name
            inference_start = time.monotonic()
            res = self.pose.detect_for_video(
                self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb), self.ts
            )
            sample["pose_inference_ms"] = (time.monotonic() - inference_start) * 1000
            if res.pose_landmarks:
                measured, visible, pose_issues = measure_pose(
                    res.pose_landmarks[0],
                    w,
                    h,
                    self.config["hand"],
                    self.config["visibility"],
                    self.config["exercise_id"],
                )
                sample.update(measured)
                # Display only the joints used by this module, not the hidden far shoulder.
                shown_points = self.pose_overlay.apply(visible, start)
                if self.config["exercise_id"] == 1:
                    arm = (12, 14, 16) if self.config["hand"] == "RIGHT" else (11, 13, 15)
                    for a, b in zip(arm, arm[1:]):
                        if a in shown_points and b in shown_points:
                            cv2.line(
                                frame,
                                tuple(round(v * 16) for v in shown_points[a]),
                                tuple(round(v * 16) for v in shown_points[b]),
                                (255, 190, 40),
                                2,
                                cv2.LINE_AA,
                                4,
                            )
                for index, p in shown_points.items():
                    xy = tuple(map(int, p))
                    # Fractional pixel centres avoid a one-pixel jump from integer rounding.
                    cv2.circle(
                        frame,
                        tuple(round(v * 16) for v in p),
                        80,
                        (60, 220, 90),
                        -1,
                        cv2.LINE_AA,
                        4,
                    )
                    cv2.putText(
                        frame,
                        str(index),
                        (xy[0] + 6, xy[1] - 6),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4,
                        (60, 220, 90),
                        1,
                    )
                if self.config["exercise_id"] == 1:
                    sample["elbow_preview"] = self.elbow_preview.render(
                        frame, shown_points, self.config["hand"]
                    )
            else:
                self.pose_overlay.apply({}, start)
                pose_issues = [
                    "ยังตรวจไม่พบร่างกาย จัดกล้องให้เห็นแขนและขาฝั่งแทง"
                    if self.config["exercise_id"] == 1
                    else "ยังตรวจไม่พบร่างกาย จัดกล้องให้เห็นผู้ฝึกชัดเจน"
                ]
            if sample.get("cue"):
                cv2.line(
                    frame,
                    tuple(map(int, sample["cue"][0])),
                    tuple(map(int, sample["cue"][1])),
                    (255, 180, 0),
                    2,
                )
        if "top" in frames:
            frame = frames["top"]
            if self.colour:
                # Mask outside table quadrilateral, computed from the inverse calibration.
                width, height = self.config["table_size"]
                corners = np.array(
                    [[[0, 0], [width, 0], [width, height], [0, height]]], dtype=np.float32
                )
                inv = np.linalg.inv(np.asarray(self.config["homography"], dtype=float))
                imagecorners = cv2.perspectiveTransform(corners, inv)[0]
                mask = np.zeros(frame.shape[:2], dtype=np.uint8)
                cv2.fillConvexPoly(mask, np.round(imagecorners).astype(np.int32), 255)
                sample["balls"] = self.colour.detect(
                    frame, start, self.config["homography"], roi_mask=mask
                )
                sample["ball_detection"] = {
                    "detector": "HSV",
                    "roles": self.colour.diagnostics,
                    "calibrated": True,
                    "table_size": self.config["table_size"],
                    "ball_radius": self.config["ball_radius"],
                }
                cv2.polylines(
                    frame, [np.round(imagecorners).astype(np.int32)], True, (255, 180, 0), 2
                )
                for ball in sample["balls"]:
                    x, y = map(int, ball["image_xy"])
                    cv2.circle(frame, (x, y), 10, (0, 200, 200), 2)
                    cv2.putText(
                        frame,
                        ball["class"],
                        (x + 12, y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4,
                        (0, 200, 200),
                        1,
                    )
        if "top" in frames:
            width, height = self.config["table_size"]
            sample["balls"] = [
                ball
                for ball in sample["balls"]
                if 0 <= ball["xy"][0] <= width and 0 <= ball["xy"][1] <= height
            ]
        # Selected preview; raw reference frames are opt-in.
        frame = frames.get("side", frames.get("top"))
        preview = cv2.resize(frame, (640, int(frame.shape[0] * 640 / frame.shape[1])))
        ok, jpeg = cv2.imencode(".jpg", preview, [cv2.IMWRITE_JPEG_QUALITY, 65])
        if ok:
            import base64

            sample["image"] = base64.b64encode(jpeg).decode("ascii")
        if "side" in frames:
            if self.config["exercise_id"] == 1:
                sample["ready"] = all(
                    sample.get(key) is not None for key in ["forearm_tilt", "knee_shooting"]
                )
        if "top" in frames:
            sample["ready"] = sample["ready"] and all(
                len([b for b in sample["balls"] if b["class"] == name and b["id"] is not None]) == 1
                for name in ["cue_ball", "target_ball"]
            )
        issues = []
        if "side" in frames:
            issues += pose_issues
        if "top" in frames:
            cue_label = "ลูกน้ำเงิน" if self.config.get("cue_ball_colour") == "BLUE" else "ลูกขาว"
            for role, label in [("cue_ball", cue_label), ("target_ball", "ลูกเป้า")]:
                if (
                    len([b for b in sample["balls"] if b["class"] == role and b["id"] is not None])
                    != 1
                ):
                    issues.append(f"ต้องตรวจพบ{label}พร้อมรหัสติดตามอย่างละหนึ่งลูก")
                    if self.colour:
                        detail = self.colour.diagnostics.get(role, {})
                        if detail.get("status") == "AMBIGUOUS":
                            issues.append(
                                f"{label}: พบวัตถุสีและขนาดใกล้เคียงหลายชิ้น ให้นำลูกหรือสิ่งของอื่นออก"
                            )
                        elif detail.get("status") == "COLOUR_OVERLAP":
                            issues.append("ช่วงสีลูกที่ใช้แทงกับลูกแดงซ้อนกัน ให้เลือกสีใหม่")
                        elif (
                            detail.get("roi_mask_pixels") == 0
                            and detail.get("raw_mask_pixels", 0) > 0
                        ):
                            issues.append(
                                f"{label}: พบสีในภาพ แต่ไม่อยู่ในพื้นที่สอบเทียบ ตรวจมุมพื้นที่และตำแหน่งลูก"
                            )
                        elif not detail.get("mask_pixels"):
                            issues.append(f"{label}: ไม่พบสีที่เลือกในพื้นที่โต๊ะ เลือกสีจากภาพจริงใหม่")
                        elif detail.get("rejected", {}).get("size"):
                            issues.append(
                                f"{label}: พบสีและรูปร่าง แต่ขนาดที่แปลงจากการสอบเทียบไม่ตรงกับรัศมีลูก ตรวจขนาดพื้นที่จริง แนวนอน/แนวตั้ง และความละเอียดกล้อง"
                            )
                        else:
                            issues.append(
                                f"{label}: พบสีแต่พื้นที่พิกเซลหรือรูปร่างไม่ผ่าน ตรวจแสง ความคมชัด และอย่าวางลูกชิดขอบพื้นที่"
                            )
        sample["readiness_issues"] = issues
        sample["images"] = {}
        sample["image_sizes"] = {}
        for name, raw in frames.items():
            small = cv2.resize(raw, (640, int(raw.shape[0] * 640 / raw.shape[1])))
            sample["images"][name] = encode_image(cv2, small, 65)
            sample["image_sizes"][name] = [raw.shape[1], raw.shape[0]]
        sample["processing_ms"] = (time.monotonic() - start) * 1000
        return sample

    def close(self):
        for cap in self.caps.values():
            cap.release()
        if self.pose:
            self.pose.close()


def ball_metrics(samples, config, setup):
    """M3 contact measurements; M1/M2 do not evaluate ball contact.
    Reject long gaps, missing IDs, ambiguity and ID switches. The configured
    M3 brief-loss path uses only real observations with the same track IDs.
    """
    if "fraction" in setup:
        from .contact import contact_metrics

        return contact_metrics(samples, config, setup)
    return {}, []
