"""Body/cue mean or median/EMA filters. Never fill missing observations.

Ball trajectories are deliberately excluded to preserve collision timing.
"""

import math
import statistics
from collections import deque
from copy import deepcopy

KEYS = ("elbow", "head", "bridge", "cue", "knee_shooting", "forearm_tilt", "torso_lean")


def average(values):
    if isinstance(values[0], (list, tuple)):
        return [average([v[i] for v in values]) for i in range(len(values[0]))]
    return statistics.mean(values)


def median(values):
    if isinstance(values[0], (list, tuple)):
        return [median([v[i] for v in values]) for i in range(len(values[0]))]
    return statistics.median(values)


def blend(previous, current, alpha):
    if isinstance(current, (list, tuple)):
        return [blend(a, b, alpha) for a, b in zip(previous, current)]
    return previous + alpha * (current - previous)


def smooth(queue, previous, dt, method, tau):
    if method != "MEDIAN_EMA":
        return average(list(queue))
    value = median(list(queue))
    if previous is None or dt is None:
        return value
    return blend(previous, value, 1 - math.exp(-dt / tau))


class LandmarkAverage:
    """Display-only point smoothing. Removed points never persist on the overlay."""

    def __init__(self, window=1, max_gap=0.25, method="MEAN", tau=0.35, display_deadband=0):
        self.window = window
        self.max_gap = max_gap
        self.last = None
        self.values = {}
        self.method = method
        self.tau = tau
        self.filtered = {}
        self.display_deadband = display_deadband
        self.shown = {}

    def apply(self, points, stamp):
        dt = stamp - self.last if self.last is not None else None
        if dt is not None and (dt <= 0 or dt > self.max_gap):
            self.values.clear()
            self.filtered.clear()
            self.shown.clear()
            dt = None
        self.last = stamp
        for key in list(self.values):
            if key not in points:
                del self.values[key]
                self.filtered.pop(key, None)
                self.shown.pop(key, None)
        result = {}
        for key, point in points.items():
            queue = self.values.setdefault(key, deque(maxlen=self.window))
            queue.append(point)
            result[key] = smooth(queue, self.filtered.get(key), dt, self.method, self.tau)
        self.filtered = deepcopy(result)
        for key, point in result.items():
            if key not in self.shown or math.dist(point, self.shown[key]) > self.display_deadband:
                self.shown[key] = list(point)
        return deepcopy(self.shown)


class MovingAverage:
    def __init__(self, window=1, max_gap=0.25, method="MEAN", tau=0.35, display_deadband=0):
        self.window = window
        self.max_gap = max_gap
        self.last = None
        self.method = method
        self.tau = tau
        self.filtered = {}
        self.display_deadband = display_deadband
        self.shown = {}
        self.values = {key: deque(maxlen=window) for key in KEYS}
        self.intervals = deque(maxlen=max(1, window))

    def reset(self):
        for queue in self.values.values():
            queue.clear()
        self.intervals.clear()
        self.last = None
        self.filtered.clear()
        self.shown.clear()

    def apply(self, sample):
        stamp = sample.get("t")
        if stamp is None:
            return sample
        dt = None
        if self.last is not None:
            dt = stamp - self.last
            if dt <= 0 or dt > self.max_gap:
                self.reset()
                dt = None
            else:
                self.intervals.append(dt)
        self.last = stamp
        raw = {key: deepcopy(sample.get(key)) for key in KEYS}
        filtered = {}
        for key, value in raw.items():
            queue = self.values[key]
            if value is None:
                queue.clear()
                filtered[key] = None
            else:
                queue.append(value)
                filtered[key] = smooth(queue, self.filtered.get(key), dt, self.method, self.tau)
        self.filtered = deepcopy(filtered)
        sample.update(filtered)
        sample["raw_measurements"] = raw
        sample["display_measurements"] = deepcopy(filtered)
        if self.display_deadband:
            for key in ["elbow", "knee_shooting", "forearm_tilt"]:
                value = filtered[key]
                if (
                    value is None
                    or self.shown.get(key) is None
                    or abs(value - self.shown[key]) > self.display_deadband
                ):
                    self.shown[key] = value
            # Readouts only. Evaluation still uses sample[key], not these held values.
            sample["angle_display"] = dict(self.shown)
            sample["angle_display_deadband_degrees"] = self.display_deadband
        sample["smoothing_window"] = self.window
        sample["smoothing_method"] = self.method
        sample["smoothing_reset_gap_s"] = self.max_gap
        sample["smoothing_time_constant_s"] = self.tau if self.method == "MEDIAN_EMA" else None
        sample["estimated_smoothing_delay_ms"] = (
            (
                (self.window - 1) / 2 * statistics.mean(self.intervals)
                + (self.tau if self.method == "MEDIAN_EMA" else 0)
            )
            * 1000
            if self.intervals
            else 0
        )
        return sample
