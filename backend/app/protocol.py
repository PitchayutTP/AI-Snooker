"""Round-level decisions, independent of database and camera implementations."""

from .criteria_templates import M1_TEMPLATE_VERSION, m1_timed_template


def assessment_problem(definition, configuration):
    if configuration.get("mode") != "LIVE":
        return "รอบประเมินต้องใช้ข้อมูล LIVE เท่านั้น"
    if (
        not definition.get("approved")
        or not definition.get("rules")
        or not definition.get("protocol")
    ):
        return "รอบประเมินต้องมีเกณฑ์ยืนยัน จำนวนครั้ง และเงื่อนไขผ่านพร้อมที่มา"
    if "top" in configuration.get("required", []):
        if configuration.get("ball_detector") != "HSV":
            return "รุ่นปัจจุบันตรวจจับลูกด้วย HSV เท่านั้น"
        if definition.get("validation_scope") != "PROTOTYPE":
            return "รุ่นปัจจุบันใช้ HSV กรุณาใช้เกณฑ์ขอบเขต PROTOTYPE"
        if not configuration.get("calibration_image_size"):
            return "สอบเทียบจากภาพและบันทึกขนาดภาพก่อนรอบประเมิน"
    version = definition.get("template_version") or ""
    if version.startswith("m2-") and version != "m2-red-gate-single-v3":
        return "เกณฑ์ M2 รุ่นเดิมเลิกใช้กับรอบใหม่ กรุณาตรวจความพร้อมเพื่อสร้างเกณฑ์ปัจจุบัน"
    if version == "m2-red-gate-single-v3":
        from .criteria_templates import training_template

        canonical = training_template(2)
        if any(
            definition["protocol"].get(k) != canonical["protocol"][k]
            for k in ("required_valid_attempts", "minimum_pass_rate")
        ):
            return "M2 ใช้หนึ่งครั้งที่ประเมินได้ต่อรอบ กรุณาเติมเกณฑ์ตั้งต้นใหม่"
        if (
            definition.get("rules") != canonical["rules"]
            or definition.get("minimum_active_seconds") != 1.5
        ):
            return "ใช้เกณฑ์ M2 ปัจจุบัน: หัวคิวถึงแดงลูกที่ 3 ภายใน 1.5 วินาที"
        if (
            configuration.get("m2_mode") != "RED_GATE3"
            or configuration.get("required") != ["top"]
            or configuration.get("baseline_seconds") != 1
        ):
            return "M2 แดงลูกที่ 3 ใช้กล้องบนและนิ่งฐาน 1 วินาที"
        if (
            configuration.get("m2_tip_offset_mm") is None
            or len(configuration.get("m2_red_points", [])) != 6
        ):
            return "เลือกแดงสองแถว 6 จุด และกรอกระยะมาร์กเกอร์ถึงหัวคิวก่อน"
    if version.startswith("m3-") and version != "m3-contact-v4":
        return "เกณฑ์ M3 รุ่นเดิมเลิกใช้กับรอบใหม่แล้ว กรุณาตรวจความพร้อมเพื่อสร้างเกณฑ์ปัจจุบัน"
    if version == "m3-contact-v4" and (
        definition["protocol"].get("required_valid_attempts") != 1
        or definition["protocol"].get("minimum_pass_rate") != 1
        or definition.get("minimum_active_seconds") != 0
    ):
        return "M3 ใช้หนึ่งครั้งที่ประเมินได้ต่อเหลี่ยม กรุณาเติมเกณฑ์ตั้งต้นใหม่"
    if version.startswith("m1-"):
        if version != M1_TEMPLATE_VERSION:
            return "เกณฑ์ M1 รุ่นนี้เลิกใช้แล้ว กรุณาเริ่มด้วยเกณฑ์ปัจจุบันจากหน้าเตรียมฝึก"
        canonical = m1_timed_template()
        if any(
            definition.get(k) != canonical[k]
            for k in (
                "validation_scope",
                "rules",
                "frame_rules",
                "minimum_valid_frame_ratio",
                "preparation_lean_min",
                "minimum_active_seconds",
            )
        ):
            return "เกณฑ์ M1 ไม่ครบตามรุ่นปัจจุบัน กรุณาเติมเกณฑ์ตั้งต้นใหม่"
        if any(
            definition["protocol"].get(k) != canonical["protocol"][k]
            for k in ("required_valid_attempts", "minimum_pass_rate")
        ):
            return "M1 ใช้หนึ่งครั้งต่อรอบ กรุณาเติมเกณฑ์ตั้งต้นใหม่"
        if (
            configuration.get("m1_auto_seconds") != 8
            or configuration.get("baseline_seconds") != 1
            or configuration.get("smoothing_window") != 15
            or configuration.get("smoothing_method") != "MEDIAN_EMA"
            or configuration.get("smoothing_tau_seconds") != 0.8
            or configuration.get("smoothing_max_gap_s") != 0.75
            or not configuration.get("smoothing_for_evaluation")
        ):
            return (
                "เกณฑ์ M1 ใช้ Median 15 เฟรม + EMA 0.8 วินาที ช่วงรีเซ็ต 0.75 วินาที บันทึก 8 วินาที ฐาน 1 วินาที"
            )
    return None


def protocol_result(counts, definition, configuration, session_status):
    valid = counts.get("PASS", 0) + counts.get("FAIL", 0)
    rate = counts.get("PASS", 0) / valid if valid else None
    plan = definition.get("protocol")
    result = {
        "purpose": configuration.get("purpose", "PILOT"),
        "valid_attempts": valid,
        "validation_scope": definition.get("validation_scope", "REPORT"),
        "invalid_attempts": counts.get("INVALID", 0),
        "pass_rate": rate,
        "required_valid_attempts": plan.get("required_valid_attempts") if plan else None,
        "minimum_pass_rate": plan.get("minimum_pass_rate") if plan else None,
        "remaining": None,
        "status": "PILOT",
    }
    if result["purpose"] != "ASSESSMENT":
        return result
    if not plan or not definition.get("approved") or configuration.get("mode") != "LIVE":
        result["status"] = "INVALID"
        return result
    result["remaining"] = max(0, plan["required_valid_attempts"] - valid)
    if session_status == "ABORTED":
        result["status"] = "ABORTED"
    elif result["remaining"]:
        result["status"] = "IN_PROGRESS" if session_status == "IN_PROGRESS" else "INCOMPLETE"
    elif session_status == "IN_PROGRESS":
        result["status"] = "READY_TO_FINISH"
    else:
        result["status"] = "PASS" if rate >= plan["minimum_pass_rate"] else "FAIL"
    return result
