"""M2 pilot: top-camera estimated cue tip crosses reference red ball #3.

Marker centres are projected onto the cloth plane. This is an image estimate,
not a 3D tip measurement; keep the cue low and camera near overhead.
"""

import math
import statistics
import time

from .cameras import encode_image, open_camera
from .colour import ColourTracker
from .cue_markers import detect_markers
from .m3_readiness import resolution_motion

VERSION = "m2-red-gate-single-v3"
POST_SECONDS = 1.5


def project(points, h):
    import cv2
    import numpy as np

    result = cv2.perspectiveTransform(
        np.array([points], dtype=np.float32), np.asarray(h, dtype=float)
    )[0]
    if not np.isfinite(result).all():
        raise ValueError("จุดที่แปลงพิกัดไม่ถูกต้อง ตรวจการสอบเทียบ")
    return result.tolist()


def reference_geometry(config):
    points = config.get("m2_red_points", [])
    if len(points) != 6:
        raise ValueError("เลือกแดงซ้าย 1–3 แล้วแดงขวา 1–3 รวม 6 จุด")
    red = project(points, config["homography"])
    r = config["ball_radius"]
    centers = [[(red[j][i] + red[j + 3][i]) / 2 for i in (0, 1)] for j in range(3)]
    length = math.dist(centers[0], centers[2])
    if length < 3 * r:
        raise ValueError("เรียงแดงแต่ละข้างจากใกล้ไปไกลผู้แทง")
    axis = [(centers[2][i] - centers[0][i]) / length for i in (0, 1)]

    def cross(p):
        return (p[0] - centers[0][0]) * axis[1] - (p[1] - centers[0][1]) * axis[0]

    for side in (red[:3], red[3:]):
        for first, last in zip(side, side[1:]):
            advance = sum((last[i] - first[i]) * axis[i] for i in (0, 1))
            if not 1.7 * r <= advance <= 2.3 * r:
                raise ValueError("แดงแต่ละแถวต้องชิดกัน เรียง 1–3 และเลือกศูนย์กลางลูก")
        if max(cross(p) for p in side) - min(cross(p) for p in side) > 0.5 * r:
            raise ValueError("เรียงแดงแต่ละข้างให้ตรง")
    for j in range(3):
        if (
            cross(red[j]) * cross(red[j + 3]) >= 0
            or abs(cross(red[j]) - cross(red[j + 3])) <= 4.3 * r
        ):
            raise ValueError("เว้นช่องกลางให้ลูกน้ำเงินผ่านได้ มีระยะเผื่อจากแดงทั้งสองข้าง")
        if abs(sum((red[j][i] - red[j + 3][i]) * axis[i] for i in (0, 1))) > 0.5 * r:
            raise ValueError("แดงซ้ายและขวาต้องตรงคู่กัน")
    w, h = config["table_size"]
    if any(not (r <= x <= w - r and r <= y <= h - r) for x, y in red):
        raise ValueError("ลูกแดงต้องอยู่ในพื้นที่สอบเทียบครบทั้งลูก")
    return red, axis


def gate_centers(red):
    return [[(red[j][i] + red[j + 3][i]) / 2 for i in (0, 1)] for j in range(3)]


def gate_check(samples, config, origin, identity):
    """Conservative 2D clearance estimate, not a physical contact sensor.
    Do not interpolate through missing observations or long/fast steps.
    """
    red, axis = reference_geometry(config)
    centers = gate_centers(red)
    r = config["ball_radius"]

    def progress(p):
        return sum((p[i] - centers[0][i]) * axis[i] for i in (0, 1))

    if math.dist(origin, centers[0]) > 0.75 * r:
        return "INVALID", "วางน้ำเงินกลางช่องตรงแนวแดงคู่แรก"
    target = progress(centers[2]) + r
    previous = origin
    for row in samples:
        balls = [b for b in row.get("balls", []) if b.get("class") == "cue_ball"]
        if len(balls) != 1 or balls[0].get("id") != identity:
            return "INVALID", "น้ำเงินหายหรือรหัสเปลี่ยนก่อนผ่านแดงคู่ที่ 3"
        point = balls[0]["xy"]
        step = math.dist(previous, point)
        if step > 2 * r + 1e-6:
            return "INVALID", "น้ำเงินเคลื่อนเร็วเกินกว่าจะยืนยันช่องผ่าน ลดแรงแทงหรือเพิ่ม FPS"
        for obstacle in red:
            delta = [point[i] - previous[i] for i in (0, 1)]
            den = sum(v * v for v in delta)
            u = (
                max(
                    0.0, min(1.0, sum((obstacle[i] - previous[i]) * delta[i] for i in (0, 1)) / den)
                )
                if den
                else 0.0
            )
            d = math.dist(obstacle, [previous[i] + u * delta[i] for i in (0, 1)])
            if d < 1.85 * r:
                return "FAIL", "แนวทางน้ำเงินเข้าเขตลูกแดง ไม่ผ่านเกณฑ์ช่องทาง"
            if d <= 2.15 * r:
                return "INVALID", "น้ำเงินใกล้ขอบแดงเกินความมั่นใจของภาพ ยังยืนยันว่าไม่ชนไม่ได้"
        if row.get("m2_red_visible") != [True] * 6:
            return "INVALID", "มองเห็นแดงไม่ครบก่อนน้ำเงินผ่านช่อง ตรวจสิ่งบังและสีแดง"
        if progress(point) >= target:
            return "PASS", "ตรวจทางผ่านน้ำเงินพ้นแดงคู่ที่ 3 พร้อมระยะเผื่อแล้ว"
        if progress(point) < -r:
            return "FAIL", "น้ำเงินเคลื่อนย้อนออกจากทางฝึก"
        previous = point
    return "WAITING", "รอน้ำเงินผ่านพ้นแดงคู่ที่ 3"


class FollowThroughSource:
    def __init__(self, config):
        import cv2

        self.cv2 = cv2
        self.config = config
        self.red, self.axis = reference_geometry(config)
        self.ball = ColourTracker(
            {"cue_ball": config["ball_colours"]["cue_ball"]},
            12,
            config["ball_max_area"],
            config["ball_max_jump"],
            max(config["max_frame_gap_s"], 1.0),
            config["ball_radius"],
            config["table_size"],
            temporal_association=True,
        )
        self.cap = open_camera(cv2, config["top_source"], config)

    def read(self):
        import numpy as np

        cv2 = self.cv2
        c = self.config
        stamp = time.monotonic()
        ok, image = self.cap.read()
        if not ok:
            return {
                "t": stamp,
                "source": "LIVE",
                "ready": False,
                "error": "กล้องบนไม่ส่งภาพ",
                "balls": [],
            }
        h, w = image.shape[:2]
        if c.get("calibration_image_size") != [w, h]:
            raise ValueError("ความละเอียดกล้องเปลี่ยน ต้องสอบเทียบและเลือกลูกแดงใหม่")
        original = image.copy() if c.get("record_frames") else None
        H = c["homography"]
        inverse = np.linalg.inv(np.asarray(H, dtype=float))
        r = c["ball_radius"]
        tw, th = c["table_size"]
        roi = np.zeros((h, w), np.uint8)
        cv2.fillConvexPoly(
            roi,
            np.round(project([[0, 0], [tw, 0], [tw, th], [0, th]], inverse)).astype(np.int32),
            255,
        )
        cue, markers = detect_markers(image, c["cue_markers"][:1])
        balls = self.ball.detect(image, stamp, H, roi_mask=roi)
        # Sample inner red discs: touching balls need no separate contour.
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        redmask = np.zeros((h, w), np.uint8)
        for bounds in c["ball_colours"]["target_ball"]:
            redmask = cv2.bitwise_or(
                redmask,
                cv2.inRange(
                    hsv, np.array(bounds["lower"], np.uint8), np.array(bounds["upper"], np.uint8)
                ),
            )
        visible = []
        for p in self.red:
            patch = np.zeros((h, w), np.uint8)
            rim = project([p, [p[0] + r * 0.55, p[1]]], inverse)
            cv2.circle(patch, tuple(map(round, rim[0])), max(2, round(math.dist(*rim))), 255, -1)
            visible.append(
                cv2.countNonZero(cv2.bitwise_and(redmask, patch)) / max(1, cv2.countNonZero(patch))
                >= 0.55
            )
        issues = []
        tip = None
        if not all(visible):
            issues.append("ต้องเห็นสีแดงครบทั้ง 6 ตำแหน่ง เลือกสีแดงหรือจัดลูกใหม่")
        if cue:
            front = project(cue, H)[0]
            tip = [front[i] + self.axis[i] * c["m2_tip_offset_mm"] for i in (0, 1)]
        else:
            issues.append("ต้องเห็นมาร์กเกอร์ใกล้ปลายคิวหนึ่งจุด")
        if len(balls) != 1:
            issues.append("ต้องเห็นลูกที่ใช้แทงหนึ่งลูกก่อนแทง")
        tip_margin = (
            sum((tip[i] - gate_centers(self.red)[2][i]) * self.axis[i] for i in (0, 1))
            if tip
            else None
        )
        # Draw only after every detector has read the untouched image.
        for n, p in enumerate(c["m2_red_points"], 1):
            x, y = map(round, p)
            cv2.circle(image, (x, y), 12, (0, 200, 255), 2)
            cv2.putText(
                image,
                ("L" if n <= 3 else "R") + str((n - 1) % 3 + 1),
                (x + 12, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 200, 255),
                2,
            )
        p = gate_centers(self.red)[2]
        normal = [-self.axis[1], self.axis[0]]
        line = project(
            [[p[i] + sign * normal[i] * 5 * r for i in (0, 1)] for sign in (-1, 1)], inverse
        )
        cv2.line(image, tuple(map(round, line[0])), tuple(map(round, line[1])), (0, 220, 255), 2)
        if tip:
            t = project([tip], inverse)[0]
            cv2.circle(image, tuple(map(round, t)), 6, (255, 180, 0), -1)
        if cue:
            cv2.circle(image, tuple(map(round, cue[0])), 6, (255, 180, 0), 2)
        result = {
            "t": stamp,
            "capture_epoch_ms": time.time() * 1000,
            "source": "LIVE",
            "error": None,
            "ready": not issues,
            "readiness_issues": issues,
            "balls": balls,
            "cue": cue,
            "marker_detection": markers,
            "m2_tip_xy": tip,
            "m2_reference_points": c["m2_red_points"],
            "m2_tip_margin_mm": tip_margin,
            "m2_capture_valid": tip is not None,
            "m2_red_visible": visible,
            "ball_detection": {"detector": "HSV", "roles": self.ball.diagnostics},
            "image": encode_image(cv2, image),
            "image_size": [w, h],
            "images": {"top": encode_image(cv2, image)},
            "image_sizes": {"top": [w, h]},
            "processing_ms": (time.monotonic() - stamp) * 1000,
        }
        if original is not None:
            result["_raw_frames"] = {"top": original}
        return result

    def close(self):
        self.cap.release()


def assess_follow_through(samples, config, finished=True):
    values = {
        k: None
        for k in ("m2_red4_reached", "m2_tip_margin_mm", "m2_tip_advance_mm", "m2_gate_clear")
    }
    evidence = {
        "state": "BASELINE",
        "reason": "นิ่งลูกที่ใช้แทงและคิวช่วงฐาน 1 วินาที",
        "method": VERSION,
        "post_seconds": POST_SECONDS,
        "tip_offset_mm": config.get("m2_tip_offset_mm"),
    }

    def result(state, reason):
        evidence.update(state=state, reason=reason)
        return values, evidence

    def waiting(state, reason):
        return result("INVALID" if finished else state, reason)

    if not samples:
        return waiting("BASELINE", "ยังไม่มีข้อมูล")
    baseline = config.get("baseline_seconds", 1.0)
    minimum = config.get("min_valid_frames", 5)
    start = samples[0]["t"]
    base = []
    trace = []
    origin = None
    identity = None
    onset = None
    pending = None
    tip_start = None
    threshold = None
    reached = 0
    streak = 0
    for row in samples:
        if trace and not 0 < row["t"] - trace[-1]["t"] <= config.get("max_frame_gap_s", 0.25):
            return result("INVALID", "เฟรมขาดช่วงก่อนเก็บ Follow-through ครบ")
        if not row.get("m2_capture_valid") or row.get("m2_tip_margin_mm") is None:
            return result("INVALID", "ปลายคิวหรือจุดอ้างอิงแดงหายก่อนเก็บข้อมูลครบ")
        balls = [
            b
            for b in row.get("balls", [])
            if b.get("class") == "cue_ball" and b.get("id") is not None
        ]
        ball = balls[0] if len(balls) == 1 else None
        if onset is None:
            if ball is None:
                return result("INVALID", "ต้องเห็นลูกที่ใช้แทงจนยืนยันการเริ่มเคลื่อนอย่างน้อยสองเฟรม")
            if identity is not None and identity != ball["id"]:
                return result("INVALID", "รหัสติดตามลูกที่ใช้แทงเปลี่ยนก่อนยืนยันการแทง")
            identity = ball["id"]
        trace.append(row)
        if row["t"] - start <= baseline:
            base.append(row)
            continue
        if origin is None:
            if len(base) < minimum:
                return result("INVALID", "ข้อมูลช่วงฐานไม่พอ นิ่งอย่างน้อย 1 วินาทีก่อนแทง")
            origin = [statistics.median(s["balls"][0]["xy"][i] for s in base) for i in (0, 1)]
            tip_start = [statistics.median(s["m2_tip_xy"][i] for s in base) for i in (0, 1)]
            threshold = resolution_motion(
                [s["balls"][0] for s in base],
                config["ball_radius"],
                config.get("motion_threshold", 0),
            )
            if any(
                math.dist(s["balls"][0]["xy"], origin) > threshold
                or math.dist(s["m2_tip_xy"], tip_start) > threshold
                for s in base
            ):
                return result("INVALID", "ลูกที่ใช้แทงหรือคิวเคลื่อนในช่วงฐาน เริ่มใหม่โดยนิ่ง 1 วินาที")
            if any(s.get("m2_red_visible") != [True] * 6 for s in base):
                return result("INVALID", "ช่วงฐานต้องเห็นแดงครบทั้ง 6 ลูก")
            if (
                math.dist(origin, gate_centers(reference_geometry(config)[0])[0])
                > 0.75 * config["ball_radius"]
            ):
                return result("INVALID", "วางน้ำเงินกลางช่องตรงแนวแดงคู่แรก")
            if (
                sum((tip_start[i] - origin[i]) * reference_geometry(config)[1][i] for i in (0, 1))
                >= 0
            ):
                return result("INVALID", "หัวคิวตั้งต้นต้องอยู่หลังน้ำเงิน")
            if max(s["m2_tip_margin_mm"] for s in base) >= 0:
                return result("INVALID", "แนวแดงลูกที่ 3 ต้องอยู่ข้างหน้าหัวคิวก่อนแทง")
        if onset is None:
            if math.dist(ball["xy"], origin) > threshold:
                if pending is None:
                    pending = row
                else:
                    onset = pending
            else:
                pending = None
        if onset:
            post = [s for s in trace if onset["t"] <= s["t"] <= onset["t"] + POST_SECONDS]
            # Two actual consecutive observations beyond the line avoid one-frame noise.
            streak = 0
            reached = 0
            for s in post:
                streak = streak + 1 if s["m2_tip_margin_mm"] >= 0 else 0
                reached = max(reached, streak)
            elapsed = row["t"] - onset["t"]
            evidence.update(onset_t=onset["t"], post_elapsed_s=elapsed)
            if elapsed >= POST_SECONDS:
                if len(post) < minimum:
                    return result("INVALID", "เฟรมหลังแทงน้อยเกินไป")
                gate_state, gate_reason = gate_check(
                    [
                        s
                        for s in trace
                        if s["t"] > start + baseline and s["t"] <= onset["t"] + POST_SECONDS
                    ],
                    config,
                    origin,
                    identity,
                )
                evidence.update(
                    gate_state=gate_state,
                    gate_reason=gate_reason,
                    clearance_method="observed-segment-clearance-fixed-red-centers",
                )
                if gate_state in ("INVALID", "WAITING"):
                    return result("INVALID", gate_reason)
                values["m2_gate_clear"] = 1.0 if gate_state == "PASS" else 0.0
                _, axis = reference_geometry(config)
                advances = [
                    sum((s["m2_tip_xy"][i] - tip_start[i]) * axis[i] for i in (0, 1)) for s in post
                ]
                values.update(
                    m2_red4_reached=1.0 if reached >= 2 else 0.0,
                    m2_tip_margin_mm=max(s["m2_tip_margin_mm"] for s in post),
                    m2_tip_advance_mm=max(0.0, max(advances)),
                )
                end = onset["t"] + POST_SECONDS
                evidence.update(
                    window_start_t=start,
                    window_end_t=end,
                    valid_active_seconds=end - start - baseline,
                    active_frames=len(post),
                    target_consecutive_frames=reached,
                )
                outcome = (
                    "ผ่านเกณฑ์ระยะส่งคิว"
                    if reached >= 2 and values["m2_gate_clear"] == 1
                    else "ไม่ผ่านเกณฑ์ระยะส่งคิวหรือช่องทางน้ำเงิน"
                )
                return result("READY", f"{outcome} กดจบเพื่อบันทึกผล")
    return waiting(
        "FOLLOW_THROUGH" if onset else "WAITING_SHOT" if origin else "BASELINE",
        "ส่งคิวตามไปถึงแนวแดงลูกที่ 3 และคงคิวให้เห็นครบ 1.5 วินาทีหลังลูกที่ใช้แทงเริ่มเคลื่อน"
        if onset
        else "รอแทงลูกที่ใช้แทง หลังนิ่งช่วงฐาน 1 วินาที",
    )


class FollowThroughPreparation:
    def __init__(self, config):
        self.config = config
        self.anchor = None

    def apply(self, sample, attempt_active=False):
        sample["m2_preparation"] = {"state": "WAITING", "stable_seconds": 0.0}
        if attempt_active:
            sample["ready"] = bool(sample.get("m2_capture_valid"))
            self.anchor = None
            return
        if sample.get("ready"):
            balls = sample.get("balls", [])
            center = gate_centers(reference_geometry(self.config)[0])[0]
            if (
                len(balls) != 1
                or math.dist(balls[0]["xy"], center) > 0.75 * self.config["ball_radius"]
            ):
                sample["ready"] = False
                sample.setdefault("readiness_issues", []).append("วางน้ำเงินกลางช่องตรงแนวแดงคู่แรก")
            elif (
                sum(
                    (tip_value - balls[0]["xy"][i]) * reference_geometry(self.config)[1][i]
                    for i, tip_value in enumerate(sample["m2_tip_xy"])
                )
                >= 0
            ):
                sample["ready"] = False
                sample.setdefault("readiness_issues", []).append("วางหัวคิวหลังน้ำเงินก่อนเริ่ม")
        if not sample.get("ready") or sample.get("m2_tip_margin_mm", 0) >= 0:
            self.anchor = None
            sample["ready"] = False
            return
        ball = sample["balls"][0]
        stamp = sample["t"]
        tip = sample["m2_tip_xy"]
        threshold = resolution_motion(
            [ball], self.config["ball_radius"], self.config.get("motion_threshold", 0)
        )
        if (
            self.anchor is None
            or not 0 < stamp - self.anchor["last"] <= self.config.get("max_frame_gap_s", 0.25)
            or self.anchor["id"] != ball["id"]
            or math.dist(tip, self.anchor["tip"]) > threshold
            or math.dist(ball["xy"], self.anchor["ball"]) > threshold
        ):
            self.anchor = {
                "t": stamp,
                "last": stamp,
                "id": ball["id"],
                "tip": tip,
                "ball": ball["xy"],
                "n": 0,
            }
        self.anchor["last"] = stamp
        self.anchor["n"] += 1
        elapsed = stamp - self.anchor["t"]
        ready = elapsed >= 0.5 and self.anchor["n"] >= 3
        sample["ready"] = ready
        sample["m2_preparation"] = {
            "state": "READY" if ready else "SETTLING",
            "stable_seconds": elapsed,
        }
        if not ready:
            sample.setdefault("readiness_issues", []).append("วางคิวและลูกที่ใช้แทงนิ่งอย่างน้อย 0.5 วินาที")


class FollowThroughMonitor:
    def __init__(self):
        self.reset()

    def reset(self):
        self.last = None
        self.evidence = {"state": "BASELINE", "reason": "รอเก็บฐาน 1 วินาที"}

    def update(self, samples, config):
        if self.evidence["state"] in ("READY", "INVALID"):
            return self.evidence
        stamp = samples[-1]["t"]
        if self.last is None or stamp - self.last >= 0.1:
            self.last = stamp
            _, self.evidence = assess_follow_through(samples, config, finished=False)
        return self.evidence
