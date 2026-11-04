"""White/red HSV detection for one ball per role on a calibrated table.
Shape/size diagnostics are engineering checks, not learned confidence scores.
No predictions or cached coordinates are emitted for missing/ambiguous balls.
"""

import math

DEFAULT_BALL_COLOURS = {
    "cue_ball": [
        {"lower": [0, 0, 100], "upper": [179, 85, 255]},
        {"lower": [10, 0, 100], "upper": [40, 150, 255]},
    ],
    "target_ball": [
        {"lower": [0, 110, 70], "upper": [10, 255, 255]},
        {"lower": [170, 110, 70], "upper": [179, 255, 255]},
    ],
}
M3_BALL_COLOURS = {
    **DEFAULT_BALL_COLOURS,
    "cue_ball": [{"lower": [95, 70, 45], "upper": [135, 255, 255]}],
}


class ColourTracker:
    def __init__(
        self,
        colours,
        min_area=50,
        max_area=5000,
        max_jump=120,
        max_gap=0.25,
        ball_radius=None,
        table_size=None,
        temporal_association=False,
    ):
        self.colours = colours
        self.min_area = min_area
        self.max_area = max_area
        self.max_jump = max_jump
        self.max_gap = max_gap
        self.previous = {}
        self.next_id = 1
        self.ball_radius = ball_radius
        self.table_size = table_size
        self.diagnostics = {}
        self.temporal_association = temporal_association

    def detect(self, frame, stamp, homography, roi_mask=None):
        import cv2
        import numpy as np

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h = np.asarray(homography, dtype=float)
        found = []
        self.diagnostics = {}
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        for role, ranges in self.colours.items():
            previous = self.previous.get(role)
            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for bounds in ranges:
                mask = cv2.bitwise_or(
                    mask,
                    cv2.inRange(
                        hsv,
                        np.array(bounds["lower"], dtype=np.uint8),
                        np.array(bounds["upper"], dtype=np.uint8),
                    ),
                )
            raw_pixels = int(cv2.countNonZero(mask))
            if roi_mask is not None:
                mask = cv2.bitwise_and(mask, roi_mask)
            roi_pixels = int(cv2.countNonZero(mask))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            if roi_mask is not None:
                mask = cv2.bitwise_and(mask, roi_mask)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            candidates = []
            rejected = {"area": 0, "shape": 0, "size": 0, "outside": 0}
            size_examples = []
            for contour in contours:
                area = cv2.contourArea(contour)
                perimeter = cv2.arcLength(contour, True)
                if not self.min_area <= area <= self.max_area or perimeter <= 0:
                    rejected["area"] += 1
                    continue
                left, top, width, height = cv2.boundingRect(contour)
                hull_area = cv2.contourArea(cv2.convexHull(contour))
                circularity = 4 * math.pi * area / perimeter**2
                aspect = min(width, height) / max(width, height)
                solidity = area / hull_area if hull_area > 0 else 0
                (circle_x, circle_y), radius_px = cv2.minEnclosingCircle(contour)
                # Accept a partly covered, already tracked stationary ball only
                # when its enclosing arc still matches the previous full circle.
                partial = bool(
                    self.temporal_association
                    and previous
                    and previous.get("radius")
                    and 0 < stamp - previous["t"] <= self.max_gap
                    and 0.8 <= radius_px / previous["radius"] <= 1.2
                    and math.dist([circle_x, circle_y], previous["xy"]) <= previous["radius"] * 0.6
                    and area >= 0.35 * math.pi * previous["radius"] ** 2
                    and circularity >= 0.35
                    and aspect >= 0.4
                    and solidity >= 0.5
                )
                shape_failed = circularity < 0.5 or aspect < 0.45 or solidity < 0.75
                if hull_area <= 0 or shape_failed and not partial:
                    rejected["shape"] += 1
                    continue
                moment = cv2.moments(contour)
                if not moment["m00"]:
                    continue
                centre = [moment["m10"] / moment["m00"], moment["m01"] / moment["m00"]]
                partial = partial and shape_failed
                if partial:
                    centre = [circle_x, circle_y]
                mapped = cv2.perspectiveTransform(np.array([[centre]], dtype=np.float32), h)[0, 0]
                if not np.isfinite(mapped).all():
                    rejected["outside"] += 1
                    continue
                if self.table_size and not (
                    0 <= mapped[0] <= self.table_size[0] and 0 <= mapped[1] <= self.table_size[1]
                ):
                    rejected["outside"] += 1
                    continue
                table_contour = cv2.perspectiveTransform(contour.astype(np.float32), h)
                table_area = abs(cv2.contourArea(table_contour))
                if not math.isfinite(table_area):
                    rejected["outside"] += 1
                    continue
                radius_px = float(radius_px)
                if self.ball_radius and (
                    radius_px < 4 or not 0.35 <= table_area / (math.pi * self.ball_radius**2) <= 2.3
                ):
                    if len(size_examples) < 3:
                        size_examples.append(
                            {
                                "equivalent_diameter": 2 * math.sqrt(table_area / math.pi),
                                "expected_diameter": 2 * self.ball_radius,
                                "image_radius_px": radius_px,
                                "area_ratio": table_area / (math.pi * self.ball_radius**2),
                            }
                        )
                    rejected["size"] += 1
                    continue
                candidates.append(
                    {
                        "image_xy": centre,
                        "xy": mapped.tolist(),
                        "box_xyxy": [left, top, left + width, top + height],
                        "image_radius_px": radius_px,
                        "table_radius_estimate": math.sqrt(table_area / math.pi),
                    }
                )
                if partial:
                    candidates[-1]["partial_occlusion"] = True
            diagnostic = {
                "mask_pixels": int(cv2.countNonZero(mask)),
                "raw_mask_pixels": raw_pixels,
                "roi_mask_pixels": roi_pixels,
                "size_examples": size_examples,
                "candidates": len(candidates),
                "rejected": rejected,
                "status": "OK"
                if len(candidates) == 1
                else "AMBIGUOUS"
                if candidates
                else "MISSING",
            }
            self.diagnostics[role] = diagnostic
            old = self.previous.get(role)
            if self.temporal_association and old and 0 < stamp - old["t"] <= self.max_gap:
                if len(candidates) > 1:
                    nearby = [
                        b
                        for b in candidates
                        if math.dist(b["image_xy"], old["xy"]) <= self.max_jump
                    ]
                    if len(nearby) == 1:
                        candidates = nearby
                        diagnostic.update(status="OK", association="UNIQUE_NEAR_PREVIOUS")
                if not candidates:
                    # Keep identity briefly, but emit no predicted/cached ball position.
                    diagnostic["association"] = "WAITING_FOR_REOBSERVATION"
                    continue
            if len(candidates) != 1:
                self.previous.pop(role, None)
                continue
            ball = candidates[0]
            x, y = ball["image_xy"]
            old = self.previous.get(role)
            same = (
                old
                and 0 < stamp - old["t"] <= self.max_gap
                and math.hypot(x - old["xy"][0], y - old["xy"][1]) <= self.max_jump
            )
            track_id = old["id"] if same else self.next_id
            if not same:
                self.next_id += 1
            self.previous[role] = {
                "t": stamp,
                "xy": [x, y],
                "id": track_id,
                "radius": old["radius"]
                if same and ball.get("partial_occlusion")
                else ball["image_radius_px"],
            }
            found.append(
                {**ball, "class": role, "detected_class": role, "id": track_id, "detector": "HSV"}
            )
        # Overlapping colour ranges must not identify the same object as both balls.
        if len(found) == 2 and math.dist(found[0]["image_xy"], found[1]["image_xy"]) < 0.8 * min(
            b["image_radius_px"] for b in found
        ):
            for ball in found:
                self.previous.pop(ball["class"], None)
                self.diagnostics[ball["class"]]["status"] = "COLOUR_OVERLAP"
            found = []
        return found
