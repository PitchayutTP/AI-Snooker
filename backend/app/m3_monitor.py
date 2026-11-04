"""Live M3 feedback uses the same evidence calculation as final persistence."""

import math

from .contact import contact_metrics
from .m3_readiness import resolution_motion


class M3Monitor:
    def __init__(self):
        self.reset()

    def reset(self):
        self.last = None
        self.state = {"state": "BASELINE", "reason": "กำลังเก็บฐาน นิ่งลูกทั้งสอง 1 วินาทีก่อนแทง"}

    def update(self, samples, config):
        if self.state["state"] == "READY":
            return self.state
        if not samples:
            return self.state
        now = samples[-1]["t"]
        if self.last is not None and now - self.last < 0.15:
            return self.state
        self.last = now
        elapsed = now - samples[0]["t"]
        baseline = config.get("baseline_seconds", 1.0)
        if elapsed <= baseline:
            self.state = {"state": "BASELINE", "reason": "ยังไม่ต้องแทง กำลังเก็บลูกนิ่งช่วงฐาน 1 วินาที"}
            return self.state
        fraction = config.get("target_fraction")
        if fraction is None:
            self.state = {"state": "WAITING", "reason": "กำลังบันทึก กดจบครั้งนี้เพื่อประเมินผล"}
            return self.state
        values, events = contact_metrics(samples, config, {"fraction": fraction})
        event = events[0] if events else {}
        if values.get("contact_fraction") is not None:
            supported = event.get("valid_active_seconds", 0) >= 1.0
            valid_end = samples[0]["t"] + baseline + event.get("valid_active_seconds", 0)
            after = (
                valid_end - event.get("t", now) if event.get("type") == "CONTACT_CANDIDATE" else 0.5
            )
            confirmed = event.get("type") == "CONTACT_CANDIDATE" and event.get("confirmation") in (
                "single-departure-and-cue-impulse",
                "two-departure-observations",
            )
            ready = (
                confirmed
                or supported
                and elapsed >= baseline + 1
                and (event.get("departure_frames", 0) >= 2 or after >= 0.5)
            )
            self.state = {
                "state": "READY" if ready else "CONTACT",
                "reason": "พบหลักฐานครบ กำลังสรุปและบันทึกผลอัตโนมัติ"
                if ready
                else "พบหลักฐานการกระทบแล้ว กำลังเก็บข้อมูลให้ครบก่อนบันทึก",
                "contact_fraction": values["contact_fraction"],
                "fraction_error": values["fraction_error"],
                "event_type": event.get("type"),
                "detected_events": 1,
                "elapsed_s": elapsed,
            }
            return self.state
        code = event.get("reason", "")
        if code == "brief reacquisition pending":
            self.state = {
                "state": "RECOVERING",
                "reason": event["reason_th"],
                "detected_events": 0,
                "elapsed_s": elapsed,
            }
            return self.state
        fatal = any(
            word in code
            for word in (
                "missing",
                "ambiguous",
                "ID changed",
                "frame gap",
                "brief loss gap exceeded",
                "invalid coordinates",
                "movement during baseline",
                "movement during occlusion",
                "target moved",
                "start touching",
            )
        )
        cue_start = next(
            (b["xy"] for b in samples[0].get("balls", []) if b.get("class") == "cue_ball"), None
        )
        cue_now = next(
            (b["xy"] for b in samples[-1].get("balls", []) if b.get("class") == "cue_ball"), None
        )
        moving = (
            cue_start is not None
            and cue_now is not None
            and math.dist(cue_start, cue_now) > config.get("ball_radius", 26.25) * 0.2
        )
        if code == "no supported contact" and cue_start is not None:
            threshold = 2 * resolution_motion(
                [b for row in samples for b in row.get("balls", [])],
                config.get("ball_radius", 26.25),
                config.get("motion_threshold", 0),
            )
            onset = next(
                (
                    row["t"]
                    for row in samples
                    if row["t"] - samples[0]["t"] > baseline
                    and any(
                        b.get("class") == "cue_ball" and math.dist(b["xy"], cue_start) > threshold
                        for b in row.get("balls", [])
                    )
                ),
                None,
            )
            if onset is not None and now - onset >= 3:
                self.state = {
                    "state": "INVALID",
                    "reason": "ลูกเคลื่อนแล้วแต่ยังไม่มีหลักฐานกระทบหรือพลาดที่ชัดเจนภายใน 3 วินาที กรุณาจัดลูกใหม่และให้เห็นลูกก่อนถึงเป้า",
                    "detected_events": 0,
                    "elapsed_s": elapsed,
                }
                return self.state
        self.state = {
            "state": "INVALID" if fatal else "WATCHING_CONTACT" if moving else "WAITING_SHOT",
            "reason": event.get("reason_th", "กำลังบันทึก รอหลักฐานการกระทบ")
            if fatal
            else "ลูกกำลังเคลื่อน กำลังตรวจหลักฐานการกระทบ"
            if moving
            else "แทงได้ กำลังบันทึกและรอตรวจการกระทบ",
            "detected_events": 0,
            "elapsed_s": elapsed,
        }
        return self.state
