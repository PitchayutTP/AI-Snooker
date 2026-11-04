"""Current-frame pose measurements; never fill occluded joints from old frames."""

import math

from .metrics import angle, distance


def measure_pose(landmarks, width, height, hand, threshold, module_id):
    right = hand == "RIGHT"
    shoulder, elbow, wrist, hip = (12, 14, 16, 24) if right else (11, 13, 15, 23)
    bridge = 15 if right else 16
    required = {
        0: "ศีรษะ",
        shoulder: "ไหล่ฝั่งถือคิว",
        elbow: "ศอกฝั่งถือคิว",
        wrist: "ข้อมือฝั่งถือคิว",
        bridge: "ข้อมือสะพานมือ",
    }
    if module_id == 1:
        required = {shoulder: "ไหล่ฝั่งถือคิว", elbow: "ศอกฝั่งถือคิว", wrist: "ข้อมือฝั่งถือคิว"}
        required.update(
            {hip: "สะโพกฝั่งแทง", 26 if right else 25: "เข่าฝั่งแทง", 28 if right else 27: "ข้อเท้าฝั่งแทง"}
        )
    visible = {}
    for index in required:
        if index >= len(landmarks):
            continue
        point = landmarks[index]
        values = (point.x, point.y, point.visibility, point.presence)
        if any(value is None or not math.isfinite(value) for value in values):
            continue
        if min(point.visibility, point.presence) < threshold:
            continue
        if not (0 <= point.x <= 1 and 0 <= point.y <= 1):
            continue
        visible[index] = [point.x * width, point.y * height]
    measurements = dict.fromkeys(["elbow", "head", "bridge"])
    if module_id == 1:
        measurements.update(knee_shooting=None)
        for key, indices in [("knee_shooting", (24, 26, 28) if right else (23, 25, 27))]:
            if all(index in visible for index in indices):
                measurements[key] = angle(*(visible[index] for index in indices))
    measurements["head"] = visible.get(0)
    measurements["bridge"] = visible.get(bridge)
    if all(index in visible for index in (shoulder, elbow, wrist)):
        measurements["elbow"] = angle(visible[shoulder], visible[elbow], visible[wrist])
    elbow_issue = None
    leg_issue = None
    if module_id == 1:
        minimum_segment = max(20.0, min(width, height) * 0.03)
        measurements.update(forearm_tilt=None, forearm_down=None, torso_lean=None)
        detail = {
            "valid": False,
            "hand": hand,
            "minimum_segment_px": minimum_segment,
            "upper_arm_px": None,
            "forearm_px": None,
            "confidence": None,
        }
        if all(i in visible for i in (elbow, wrist)):
            dx = visible[wrist][0] - visible[elbow][0]
            dy = visible[wrist][1] - visible[elbow][1]
            detail.update(
                forearm_px=math.hypot(dx, dy),
                confidence=min(
                    min(landmarks[i].visibility, landmarks[i].presence) for i in (elbow, wrist)
                ),
            )
            if detail["forearm_px"] >= minimum_segment:
                measurements["forearm_tilt"] = math.degrees(math.atan2(abs(dx), dy))
                measurements["forearm_down"] = dy > 0
                detail["valid"] = True
            else:
                elbow_issue = "ท่อนแขนสั้นหรือซ้อนในภาพ ขยับกล้องให้เห็นศอก–ข้อมือแยกกัน"
        if all(i in visible for i in (shoulder, elbow)):
            detail["upper_arm_px"] = distance(visible[shoulder], visible[elbow])
        if all(i in visible for i in (shoulder, hip)):
            dx = visible[shoulder][0] - visible[hip][0]
            dy = visible[hip][1] - visible[shoulder][1]
            if dy > 0 and math.hypot(dx, dy) >= minimum_segment:
                measurements["torso_lean"] = math.degrees(math.atan2(abs(dx), dy))
        measurements["elbow_detail"] = detail
        knee, ankle = (26, 28) if right else (25, 27)
        leg_detail = {
            "valid": False,
            "minimum_segment_px": minimum_segment,
            "thigh_px": None,
            "shin_px": None,
            "confidence": None,
        }
        if all(i in visible for i in (hip, knee, ankle)):
            leg_detail.update(
                thigh_px=distance(visible[hip], visible[knee]),
                shin_px=distance(visible[knee], visible[ankle]),
                confidence=min(
                    min(landmarks[i].visibility, landmarks[i].presence) for i in (hip, knee, ankle)
                ),
            )
            if min(leg_detail["thigh_px"], leg_detail["shin_px"]) < minimum_segment:
                measurements["knee_shooting"] = None
                leg_issue = "ช่วงขาในภาพสั้นหรือซ้อนกันเกินไป ปรับกล้องให้เห็นสะโพก–เข่า–ข้อเท้าแยกกันชัดเจน"
            leg_detail["valid"] = measurements["knee_shooting"] is not None
        measurements["knee_detail"] = leg_detail
    issues = [
        f"ยังตรวจไม่พบ{label}ชัดเจน"
        for index, label in required.items()
        if index not in visible
        and not (module_id == 1 and index == shoulder)
        and not (module_id == 2 and index not in (0, bridge))
    ]
    if elbow_issue:
        issues.append(elbow_issue)
    if leg_issue:
        issues.append(leg_issue)
    return measurements, visible, issues
