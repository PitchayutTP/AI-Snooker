"""Project pilot acceptance limits, separate from contact proximity tolerances."""

import math

M2_CALIBRATION_LIMIT_MM = 20.0
M3_CALIBRATION_LIMIT_MM = 50.0
PRACTICE_TABLE_SIZE = (1500.0, 750.0)
PRACTICE_BALL_RADIUS = 26.25


def m3_calibration_accepted(error):
    return error is None or (math.isfinite(error) and 0 <= error <= M3_CALIBRATION_LIMIT_MM)
