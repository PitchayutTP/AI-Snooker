"""Detect explicit colour markers on an untouched camera frame."""

import math


def detect_markers(frame, bounds):
    import cv2
    import numpy as np

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    points = []
    details = []
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    for item in bounds:
        mask = cv2.inRange(
            hsv, np.array(item["lower"], dtype=np.uint8), np.array(item["upper"], dtype=np.uint8)
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = [
            c
            for c in contours
            if max(10, item.get("min_area", 10))
            <= cv2.contourArea(c)
            <= frame.shape[0] * frame.shape[1] * 0.02
        ]
        details.append(
            {
                "candidates": len(contours),
                "status": "OK" if len(contours) == 1 else "AMBIGUOUS" if contours else "MISSING",
            }
        )
        if len(contours) != 1:
            points.append(None)
            continue
        m = cv2.moments(contours[0])
        points.append([m["m10"] / m["m00"], m["m01"] / m["m00"]] if m["m00"] else None)
    minimum = max(20.0, min(frame.shape[:2]) * 0.04)
    valid = len(points) in (1, 2) and all(p is not None for p in points)
    status = "OK" if valid else "MISSING_OR_AMBIGUOUS"
    if valid and len(points) == 2 and math.dist(*points) < minimum:
        valid = False
        status = "TOO_CLOSE_OR_OVERLAP"
    return points if valid else None, {
        "status": status,
        "markers": details,
        "minimum_span_px": minimum,
    }
