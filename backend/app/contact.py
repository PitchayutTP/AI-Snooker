"""M3 approximate projected contact fraction from real track observations.
No missing coordinates are interpolated. Trailing loss cannot erase an earlier
verified candidate. Optional brief gaps require bounded same-ID reobservation.
Results remain estimates requiring real-video validation.
"""

import math

from .m3_readiness import position_tolerance, resolution_motion
from .metrics import distance, line_distance


def incoming_line(rows, motion):
    points = []
    for row in rows:
        p = row[1]
        if not points or distance(points[-1], p) >= motion * 0.5:
            points.append(p)
    points = points[-5:]
    if len(points) < 2 or distance(points[0], points[-1]) < motion:
        return None
    x = sum(p[0] for p in points) / len(points)
    y = sum(p[1] for p in points) / len(points)
    xx = sum((p[0] - x) ** 2 for p in points)
    yy = sum((p[1] - y) ** 2 for p in points)
    xy = sum((p[0] - x) * (p[1] - y) for p in points)
    theta = 0.5 * math.atan2(2 * xy, xx - yy)
    a = [x, y]
    b = [x + math.cos(theta), y + math.sin(theta)]
    if max(line_distance(p, a, b) for p in points) > motion:
        return None
    return a, b


def contact_metrics(samples, config, setup):
    result = {"contact_fraction": None, "fraction_error": None}

    def invalid(code, text):
        return result, [{"type": "INVALID", "reason": code, "reason_th": text}]

    radius = config.get("ball_radius", 0)
    if not radius or not samples:
        return invalid("no radius or samples", "ไม่มีรัศมีลูกที่สอบเทียบหรือไม่มีเฟรมบันทึก")
    trace = []
    ids = None
    problem = None
    observed = []
    pending = []
    occlusions = []
    previous_sample_t = None
    gap = config.get("max_frame_gap_s", 0.25)
    tolerance = config.get("contact_tolerance", 0)
    brief = min(0.35, max(0.0, config.get("m3_brief_loss_seconds", 0)))
    maximum_missing = min(6, max(0, config.get("m3_max_missing_frames", 0)))
    stationary_limit = min(1.0, max(0.0, config.get("m3_stationary_loss_seconds", 0)))
    stationary_pending = False
    baseline = config.get("baseline_seconds", 0)
    for sample in samples:
        if previous_sample_t is not None and sample["t"] <= previous_sample_t:
            problem = ("frame gap or unordered timestamp", "เวลาเฟรมไม่เรียง กรุณาตรวจกล้อง")
            break
        previous_sample_t = sample["t"]
        roles = [
            [b for b in sample.get("balls", []) if b.get("class") == role]
            for role in ("cue_ball", "target_ball")
        ]
        if any(len(items) != 1 or items[0].get("id") is None for items in roles):
            details = sample.get("ball_detection", {}).get("roles", {})
            ambiguous = any(len(items) > 1 for items in roles) or any(
                d.get("status") in ("AMBIGUOUS", "COLOUR_OVERLAP") for d in details.values()
            )
            if not pending and trace and trace[-1][0] - trace[0][0] >= baseline:
                threshold = resolution_motion(observed, radius, config.get("motion_threshold", 0))
                stationary_pending = all(
                    distance(row[1], trace[0][1]) <= threshold
                    and distance(row[2], trace[0][2]) <= threshold
                    for row in trace
                )
            if (
                not ambiguous
                and stationary_pending
                and stationary_limit
                and sample["t"] - trace[-1][0] <= stationary_limit
            ):
                pending.append(sample["t"])
                continue
            if (
                not ambiguous
                and trace
                and sample["t"] - trace[0][0] > baseline
                and len(pending) < maximum_missing
                and sample["t"] - trace[-1][0] <= brief
            ):
                pending.append(sample["t"])
                continue
            detail = []
            for role, items in zip(("cue_ball", "target_ball"), roles):
                if len(items) == 1 and items[0].get("id") is not None:
                    continue
                label = (
                    ("ลูกน้ำเงิน" if config.get("cue_ball_colour") == "BLUE" else "ลูกที่ใช้แทง")
                    if role == "cue_ball"
                    else "ลูกแดง"
                )
                d = details.get(role, {})
                why = (
                    "พบวัตถุสีซ้ำหลายชิ้น"
                    if d.get("status") == "AMBIGUOUS" or len(items) > 1
                    else "ช่วงสีซ้อนกัน"
                    if d.get("status") == "COLOUR_OVERLAP"
                    else "พบสีแต่ขนาดไม่ผ่าน"
                    if d.get("rejected", {}).get("size")
                    else "พบสีแต่รูปร่างไม่ผ่าน"
                    if d.get("rejected", {}).get("shape")
                    else "ตรวจจับไม่ได้ชั่วคราว"
                )
                detail.append(f"{label}: {why}")
            problem = (
                "missing or ambiguous ball/track",
                "จุดตรวจจับไม่ครบ ไม่ได้หมายความว่าลูกออกจากภาพเสมอไป — " + " · ".join(detail),
            )
            break
        cue, target = [items[0] for items in roles]
        current = (cue["id"], target["id"])
        if any(
            len(b.get("xy", [])) != 2 or not all(math.isfinite(v) for v in b["xy"])
            for b in (cue, target)
        ):
            problem = ("invalid coordinates", "พิกัดลูกไม่ถูกต้อง")
            break
        if ids is not None and current != ids:
            problem = ("track ID changed", "รหัสติดตามลูกเปลี่ยนก่อนเก็บหลักฐานครบ ห้ามต่อเส้นทางข้ามรหัส")
            break
        if trace and not 0 < sample["t"] - trace[-1][0] <= max(
            gap, stationary_limit if pending and stationary_pending else 0
        ):
            problem = (
                "frame gap or unordered timestamp",
                "ช่วงห่างระหว่างเฟรมมากเกินไปหรือเวลาไม่เรียง กรุณาตรวจ FPS",
            )
            break
        if pending:
            limit = stationary_limit if stationary_pending and stationary_limit else brief
            if sample["t"] - trace[-1][0] > limit + 1e-9:
                problem = ("brief loss gap exceeded", "ลูกกลับมาช้าเกินช่วงรอติดตาม กรุณาเริ่มครั้งใหม่")
                break
            if stationary_pending and stationary_limit:
                threshold = resolution_motion(observed, radius, config.get("motion_threshold", 0))
                changed = (
                    distance(cue["xy"], trace[-1][1]) > threshold
                    or distance(target["xy"], trace[-1][2]) > threshold
                )
                if changed:
                    # A covered launch can resume only while the target is still
                    # stationary and the cue ball has not reached the contact zone.
                    safe_launch = (
                        sample["t"] - trace[-1][0] <= brief + 1e-9
                        and distance(target["xy"], trace[-1][2]) <= threshold
                        and distance(cue["xy"], target["xy"])
                        > 2 * radius
                        + position_tolerance(
                            observed, radius, tolerance, config.get("calibration_check_error")
                        )
                    )
                    if not safe_launch:
                        problem = (
                            "movement during occlusion",
                            "ลูกเคลื่อนขณะถูกบังจนขาดแนวก่อนชน กรุณาเริ่มใหม่และให้เห็นลูกก่อนถึงเป้า",
                        )
                        break
            else:
                changed = False
            occlusions.append(
                {
                    "from_t": trace[-1][0],
                    "to_t": sample["t"],
                    "missing_frames": len(pending),
                    "interpolated": False,
                    "stationary": bool(stationary_pending and stationary_limit and not changed),
                    "covered_launch": bool(stationary_pending and stationary_limit and changed),
                }
            )
            pending = []
            stationary_pending = False
        ids = current
        observed.extend([cue, target])
        trace.append((sample["t"], cue["xy"], target["xy"]))
    if not trace:
        return invalid(*(problem or ("no trace", "ไม่มีข้อมูลลูกที่ใช้ได้")))
    motion = resolution_motion(observed, radius, config.get("motion_threshold", 0))
    # Pixel resolution plus a capped pilot proximity budget; this is not an
    # accuracy bound. Relaxed calibration acceptance must not widen contact to 50 mm.
    tolerance = position_tolerance(
        observed, radius, tolerance, config.get("calibration_check_error")
    )
    base = [row for row in trace if row[0] - trace[0][0] <= baseline]
    if baseline and (
        len(base) < config.get("min_valid_frames", 5) or trace[-1][0] - trace[0][0] < baseline
    ):
        return invalid(
            "insufficient baseline", "บันทึกลูกนิ่งช่วงฐาน 1 วินาทีก่อนแทง และรอให้เก็บข้อมูลได้เพียงพอ"
        )
    if any(
        distance(row[1], trace[0][1]) > motion or distance(row[2], trace[0][2]) > motion
        for row in base
    ):
        return invalid("movement during baseline", "ลูกเคลื่อนในช่วงเก็บฐาน กรุณารอให้ครบช่วงฐานก่อนแทง")
    if distance(trace[0][1], trace[0][2]) <= 2 * radius + tolerance:
        return invalid("start touching", "เริ่มด้วยลูกที่แยกจากกันก่อนแทง")
    minimum_distance = math.inf
    for index in range(1, len(trace)):
        t0, c0, o0 = trace[index - 1]
        t1, c1, o1 = trace[index]
        # Never infer contact or fit an incoming line through the unseen launch.
        launch = max(
            (g["to_t"] for g in occlusions if g.get("covered_launch") and g["to_t"] <= t1),
            default=None,
        )
        if any(
            g.get("covered_launch") and g["from_t"] == t0 and g["to_t"] == t1 for g in occlusions
        ):
            continue
        incoming = [row for row in trace[:index] if launch is None or row[0] >= launch]
        relative = [c0[i] - o0[i] for i in (0, 1)]
        delta = [(c1[i] - o1[i]) - relative[i] for i in (0, 1)]
        squared = sum(v * v for v in delta)
        if squared <= 1e-12:
            continue
        dot = sum(relative[i] * delta[i] for i in (0, 1))
        u = max(0.0, min(1.0, -dot / squared))
        closest = math.hypot(*(relative[i] + u * delta[i] for i in (0, 1)))
        minimum_distance = min(minimum_distance, closest)
        if distance(c0, c1) < motion:
            continue
        hidden = any(
            g["from_t"] == t0 and g["to_t"] == t1 and not g.get("stationary") for g in occlusions
        )
        inferred = False
        line = None
        normal = None
        entry = None
        if dot >= 0 or closest > 2 * radius + tolerance:
            # Impact may occur between two captured frames, even with no detection
            # loss. The outgoing cue path is not the incoming contact trajectory.
            # Infer an event from the real incoming line and real target motion;
            # never insert a contact point into the recorded ball observations.
            line = incoming_line(incoming, motion)
            if line is None:
                continue
            direction = [line[1][i] - line[0][i] for i in (0, 1)]
            if sum((c0[i] - trace[0][1][i]) * direction[i] for i in (0, 1)) < 0:
                direction = [-v for v in direction]
            projection = sum((o0[i] - line[0][i]) * direction[i] for i in (0, 1))
            foot = [line[0][i] + projection * direction[i] for i in (0, 1)]
            offset = distance(foot, o0)
            if offset >= 2 * radius:
                continue
            advance = math.sqrt((2 * radius) ** 2 - offset**2)
            touch = [foot[i] - advance * direction[i] for i in (0, 1)]
            before = sum((touch[i] - c0[i]) * direction[i] for i in (0, 1))
            travel = sum((c1[i] - c0[i]) * direction[i] for i in (0, 1))
            if before < 0 or travel <= 0 or before > travel + motion:
                continue
            normal = [o0[i] - touch[i] for i in (0, 1)]
            entry = max(0.0, min(1.0, before / travel))
            inferred = True
        if any(distance(row[2], trace[0][2]) > motion for row in trace[:index]):
            return invalid(
                "target moved before contact", "ลูกแดงเคลื่อนก่อนช่วงที่พบการเข้าใกล้ กรุณาจัดลูกให้นิ่งแล้วเริ่มใหม่"
            )
        line = line or incoming_line(incoming, motion)
        if line is None:
            continue
        # First entry into the contact circle, rather than time of closest approach.
        if not inferred:
            discriminant = dot * dot - squared * (
                sum(v * v for v in relative) - (2 * radius + tolerance) ** 2
            )
            entry = max(0.0, min(1.0, (-dot - math.sqrt(max(0.0, discriminant))) / squared))
            normal = [-(relative[i] + entry * delta[i]) for i in (0, 1)]
        after = [row for row in trace[index:] if row[0] - t1 <= 0.5]
        departures = [
            row
            for row in after
            if distance(o0, row[2]) >= motion
            and sum((row[2][i] - o0[i]) * normal[i] for i in (0, 1)) > 0
        ]
        if not departures:
            continue
        departure_frames = len(departures)
        departure = departures[min(1, departure_frames - 1)]
        # A fast target may leave the calibrated image after one outgoing frame.
        # Require both its observed departure and a matching impulse on the cue
        # ball, estimated from actual incoming velocity, to accept that case.
        impulse_confirmed = False
        if departure_frames == 1 and len(incoming) >= 2:
            previous, last = incoming[-2:]
            dt = last[0] - previous[0]
            if 0 < dt <= gap:
                impulse = [
                    c0[i]
                    + (last[1][i] - previous[1][i]) * (departure[0] - t0) / dt
                    - departure[1][i]
                    for i in (0, 1)
                ]
                target_delta = [departure[2][i] - o0[i] for i in (0, 1)]
                strength = math.hypot(*impulse)
                travel = math.hypot(*target_delta)
                impulse_confirmed = (
                    strength >= motion
                    and travel >= motion
                    and sum(impulse[i] * target_delta[i] for i in (0, 1)) >= 0.9 * strength * travel
                    and sum(target_delta[i] * normal[i] for i in (0, 1))
                    >= 0.85 * travel * math.hypot(*normal)
                )
        if departure_frames < 2 and not impulse_confirmed:
            continue
        if inferred:
            outward = [
                row
                for row in after
                if distance(o0, row[2]) >= motion
                and sum((row[2][i] - o0[i]) * normal[i] for i in (0, 1))
                >= 0.7 * distance(o0, row[2]) * math.hypot(*normal)
            ]
            if len(outward) < 2 and not impulse_confirmed:
                continue
            if len(outward) >= 2:
                departure = outward[1]
        offset = line_distance(o0, *line)
        if offset is None or offset > 2 * radius + tolerance:
            continue
        value = max(0.0, min(1.0, 1 - offset / (2 * radius)))
        result.update(contact_fraction=value, fraction_error=abs(value - setup["fraction"]))
        return result, [
            {
                "type": "CONTACT_CANDIDATE",
                "t": t0 + (t1 - t0) * entry,
                "method": (
                    "pre-impact-line-and-target-departure-across-brief-loss"
                    if hidden
                    else "pre-impact-line-and-target-departure-between-frames"
                )
                if inferred
                else "pre-impact-line-and-swept-contact-with-target-departure",
                "estimated": True,
                "contact_interval": [t0, t1],
                "closest_distance": closest,
                "incoming_offset": offset,
                "motion_threshold": motion,
                "contact_tolerance": tolerance,
                "valid_active_seconds": max(0.0, trace[-1][0] - trace[0][0] - baseline),
                "evidence_until_t": departure[0],
                "brief_occlusions": occlusions,
                "departure_frames": departure_frames,
                "confirmation": "single-departure-and-cue-impulse"
                if impulse_confirmed
                else "two-departure-observations",
                "reason_th": "พบแนวลูกที่ใช้แทงก่อนกระทบและการเคลื่อนออกของลูกแดง เป็นค่าประมาณจากภาพ",
            }
        ]
    # A clear miss requires a complete continuous pass beyond a stationary target.
    # A path through a stationary target is inconsistent, not proof of a miss.
    line = incoming_line(trace, motion)
    if (
        problem is None
        and not pending
        and not any(not g.get("stationary") for g in occlusions)
        and line
        and minimum_distance > 2 * radius + tolerance
        and all(distance(row[2], trace[0][2]) <= motion for row in trace)
    ):
        start, end = trace[0][1], trace[-1][1]
        direction = [end[i] - start[i] for i in (0, 1)]
        length = sum(v * v for v in direction)
        target = trace[0][2]
        projection = (
            sum((target[i] - start[i]) * direction[i] for i in (0, 1)) / length if length else 0
        )
        if distance(start, end) > 4 * radius and 0 < projection < 1:
            result.update(contact_fraction=0.0, fraction_error=abs(setup["fraction"]))
            return result, [
                {
                    "type": "CLEAR_MISS",
                    "estimated": True,
                    "closest_distance": minimum_distance,
                    "motion_threshold": motion,
                    "valid_active_seconds": max(0.0, trace[-1][0] - trace[0][0] - baseline),
                    "reason_th": "ลูกที่ใช้แทงผ่านเลยลูกแดงโดยมีระยะห่างชัดเจน ลูกแดงยังนิ่ง ประเมินเหลี่ยมเป็น 0",
                }
            ]
    if pending and problem is None:
        return invalid("brief reacquisition pending", "ไม้คิวอาจบังลูกชั่วคราว กำลังรอเห็นลูกอีกครั้ง")
    return invalid(
        *(
            problem
            or (
                "no supported contact",
                "ไม่พบหลักฐานกระทบหรือการพลาดที่ชัดเจน ตรวจ FPS การสอบเทียบ และให้เห็นลูกต่อเนื่องจนลูกแดงเคลื่อน",
            )
        )
    )
