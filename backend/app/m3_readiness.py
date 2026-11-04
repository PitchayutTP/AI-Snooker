"""Require two separated, stationary tracked balls before a manual M3 attempt."""

import math


def position_tolerance(balls, radius, configured=0, calibration_error=0):
    pixel = max(
        [
            radius / b["image_radius_px"]
            for b in balls
            if isinstance(b.get("image_radius_px"), (int, float))
            and math.isfinite(b["image_radius_px"])
            and b["image_radius_px"] > 0
        ],
        default=0.0,
    )
    # A relaxed calibration acceptance limit is not a larger ball-contact zone.
    # Retain the original proximity budget; a single check point does not bound
    # physical error everywhere on the cloth.
    return max(configured, pixel + min(calibration_error or 0.0, radius * 0.25))


def resolution_motion(balls, radius, configured=0):
    noise = [
        2 * radius / b["image_radius_px"]
        for b in balls
        if isinstance(b.get("image_radius_px"), (int, float)) and b["image_radius_px"] > 0
    ]
    return max([configured, radius * 0.2] + noise)


class M3Preparation:
    def __init__(self, config):
        self.config = config
        self.anchor = None
        self.last = None

    def apply(self, sample, attempt_active=False):
        balls = sample.get("balls", [])
        roles = [
            [b for b in balls if b.get("class") == r and b.get("id") is not None]
            for r in ("cue_ball", "target_ball")
        ]
        good = all(
            len(items) == 1
            and len(items[0].get("xy", [])) == 2
            and all(math.isfinite(v) for v in items[0]["xy"])
            for items in roles
        )
        sample["ball_ready"] = good
        sample["ready"] = bool(sample.get("ready")) and good
        sample["m3_preparation"] = {
            "state": "RECORDING" if attempt_active else "WAITING",
            "stable_seconds": 0.0,
        }
        if attempt_active:
            self.anchor = None
            self.last = None
            return
        if not sample["ready"]:
            self.anchor = None
            self.last = None
            return
        cue, target = [items[0] for items in roles]
        radius = self.config["ball_radius"]
        tolerance = position_tolerance(
            [cue, target],
            radius,
            self.config.get("contact_tolerance", 0),
            self.config.get("calibration_check_error"),
        )
        if math.dist(cue["xy"], target["xy"]) <= 2 * radius + tolerance:
            sample["ready"] = False
            self.anchor = None
            self.last = None
            sample["m3_preparation"]["state"] = "TOUCHING"
            sample.setdefault("readiness_issues", []).append("แยกลูกที่ใช้แทงกับลูกแดงไม่ให้แตะกันก่อนเริ่ม")
            return
        ids = (cue["id"], target["id"])
        positions = (cue["xy"], target["xy"])
        stamp = sample["t"]
        threshold = resolution_motion([cue, target], radius, self.config.get("motion_threshold", 0))
        reset = (
            self.anchor is None
            or self.anchor["ids"] != ids
            or self.last is None
            or not 0 < stamp - self.last <= self.config.get("max_frame_gap_s", 0.25)
            or any(math.dist(a, b) > threshold for a, b in zip(self.anchor["positions"], positions))
        )
        if reset:
            self.anchor = {"ids": ids, "positions": positions, "t": stamp, "n": 0}
        self.anchor["n"] += 1
        self.last = stamp
        elapsed = stamp - self.anchor["t"]
        stable = elapsed >= 0.5 and self.anchor["n"] >= 3
        sample["m3_preparation"] = {
            "state": "READY" if stable else "SETTLING",
            "stable_seconds": elapsed,
        }
        sample["ready"] = stable
        if not stable:
            sample.setdefault("readiness_issues", []).append(
                "วางลูกทั้งสองให้นิ่งอย่างน้อย 0.5 วินาทีก่อนเริ่มบันทึก"
            )
