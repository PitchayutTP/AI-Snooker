"""M1 projected posture: simultaneous frame scoring, no missing-point imputation."""

import math

from .metrics import evaluate, stats


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def measurable(sample):
    return all(finite(sample.get(k)) for k in ("forearm_tilt", "knee_shooting")) and isinstance(
        sample.get("forearm_down"), bool
    )


def apply_readiness(sample, attempt_active=False):
    sample["pose_ready"] = measurable(sample)
    lean = sample.get("torso_lean")
    sample["preparation_ready"] = sample["pose_ready"] and finite(lean) and lean >= 30
    sample["ready"] = sample["pose_ready"] if attempt_active else sample["preparation_ready"]
    if not attempt_active and not sample["preparation_ready"] and sample["pose_ready"]:
        sample.setdefault("readiness_issues", []).append(
            "ให้เห็นไหล่และสะโพก แล้วก้มลำตัวอย่างน้อย 30° จากแนวดิ่งก่อนเริ่ม"
        )


def assess_m1(samples, definition, baseline_seconds=1.0, min_valid=5):
    active = [s for s in samples if s["t"] - samples[0]["t"] > baseline_seconds] if samples else []
    valid = [s for s in active if measurable(s)]
    frame_rules = definition.get("frame_rules", {})

    def correct(s):
        return s["forearm_down"] and all(
            ("min" not in rule or s[key] >= rule["min"])
            and ("max" not in rule or s[key] <= rule["max"])
            for key, rule in frame_rules.items()
        )

    count = sum(correct(s) for s in valid) if frame_rules else 0
    coverage = len(valid) / len(active) if active else 0.0
    ratio = count / len(valid) if valid else None
    measured = {"m1_valid_frame_ratio": coverage, "m1_correct_frame_ratio": ratio}
    for key in ("forearm_tilt", "knee_shooting"):
        summary = stats([s[key] for s in valid])
        measured.update({f"{key}_{p}": summary[p] for p in ("mean", "min", "max")})
    evidence = {
        "active_frames": len(active),
        "valid_frames": len(valid),
        "correct_frames": count,
        "valid_ratio": coverage,
        "correct_ratio": ratio,
        "minimum_valid_ratio": definition.get("minimum_valid_frame_ratio", 0.8),
        "frame_rules": frame_rules,
        "minimum_valid_frames": min_valid,
    }
    duration = max(0, samples[-1]["t"] - samples[0]["t"] - baseline_seconds) if samples else 0
    if set(frame_rules) != {
        "forearm_tilt",
        "knee_shooting",
    } or "m1_correct_frame_ratio" not in definition.get("rules", {}):
        result = ("INVALID", "เกณฑ์ M1 ไม่ครบตามรุ่นปัจจุบัน กรุณาเริ่มด้วยเกณฑ์ตั้งต้นใหม่")
    elif len(valid) < min_valid or coverage < evidence["minimum_valid_ratio"]:
        result = (
            "INVALID",
            "ข้อมูลแขนและเข่าที่วัดพร้อมกันไม่ถึง 80% หรือมีเฟรมน้อยเกินไป กรุณาจัดกล้องและทดลองใหม่",
        )
    else:
        result = evaluate(measured, definition, duration)
    return (*result, measured, evidence)
