"""Geometric and decision checks for M1; no camera or database required."""

import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.criteria_templates import m1_timed_template
from app.m1_assessment import apply_readiness, assess_m1
from app.pose import measure_pose


class Checks(unittest.TestCase):
    def definition(self):
        return {**m1_timed_template(), "approved": True}

    def rows(self):
        # 20 active frames, after a one-second baseline, over exactly 8 seconds.
        return [
            {"t": t, "forearm_tilt": 15.0, "forearm_down": True, "knee_shooting": 160.0}
            for t in [0.0, 1.0] + [1.0 + 7.0 * i / 20 for i in range(1, 21)]
        ]

    def result(self, rows):
        return assess_m1(rows, self.definition())

    def test_exact_boundaries(self):
        rows = self.rows()
        self.assertEqual(self.result(rows)[0], "PASS")
        for s in rows:
            s["knee_shooting"] = 180.0
        self.assertEqual(self.result(rows)[0], "PASS")

    def test_correct_80_percent_and_below(self):
        rows = self.rows()
        for s in rows[2:6]:
            s["forearm_tilt"] = 15.001
        result = self.result(rows)
        self.assertEqual(result[0], "PASS")
        self.assertEqual(result[3]["correct_ratio"], 0.8)
        rows[6]["knee_shooting"] = 159.999
        self.assertEqual(self.result(rows)[0], "FAIL")

    def test_valid_80_percent_and_below(self):
        rows = self.rows()
        for s in rows[2:6]:
            s["forearm_tilt"] = None
        self.assertEqual(self.result(rows)[0], "PASS")
        rows[6]["knee_shooting"] = None
        self.assertEqual(self.result(rows)[0], "INVALID")

    def test_joint_correctness_not_independent_pass_rates(self):
        rows = self.rows()
        for s in rows[2:6]:
            s["forearm_tilt"] = 20.0
        for s in rows[6:10]:
            s["knee_shooting"] = 150.0
        self.assertEqual(self.result(rows)[0], "FAIL")
        self.assertEqual(self.result(rows)[3]["correct_ratio"], 0.6)

    def test_wrist_above_elbow_is_failure_not_missing(self):
        rows = self.rows()
        for s in rows:
            s["forearm_down"] = False
        result = self.result(rows)
        self.assertEqual(result[0], "FAIL")
        self.assertEqual(result[3]["valid_ratio"], 1.0)

    def test_missing_nan_and_short_recording(self):
        self.assertEqual(self.result([])[0], "INVALID")
        rows = self.rows()
        for s in rows:
            s["forearm_tilt"] = math.nan
        self.assertEqual(self.result(rows)[0], "INVALID")
        self.assertEqual(self.result(self.rows()[:-1])[0], "INVALID")

    def test_baseline_display_and_lean_are_not_scored(self):
        rows = self.rows()
        rows[0]["forearm_tilt"] = 100
        for s in rows:
            s.update(torso_lean=0, angle_display={"forearm_tilt": 100})
        self.assertEqual(self.result(rows)[0], "PASS")

    def test_preparation_only_gate(self):
        s = {**self.rows()[0], "torso_lean": 29.9}
        apply_readiness(s)
        self.assertFalse(s["ready"])
        s["torso_lean"] = 30
        apply_readiness(s)
        self.assertTrue(s["ready"])
        s["torso_lean"] = None
        apply_readiness(s, True)
        self.assertTrue(s["ready"])
        s["knee_shooting"] = None
        apply_readiness(s, True)
        self.assertFalse(s["ready"])

    def test_missing_frame_definition_is_invalid(self):
        definition = self.definition()
        definition.pop("frame_rules")
        self.assertEqual(assess_m1(self.rows(), definition)[0], "INVALID")

    def test_runtime_applies_preparation_gate_then_records_without_shoulder(self):
        from unittest.mock import patch

        from app.runtime import Runtime

        class Source:
            def __init__(self, config):
                self.t = -1

            def read(self):
                self.t += 1
                return {
                    "t": self.t,
                    "forearm_tilt": 0.0,
                    "forearm_down": True,
                    "knee_shooting": 170.0,
                    "torso_lean": None,
                    "source": "LIVE",
                    "readiness_issues": [],
                    "error": "test end" if self.t == 20 else None,
                }

            def close(self):
                pass

        instance = Runtime()
        with patch("app.runtime.LiveSource", Source):
            with instance.lock:
                instance.start({"mode": "LIVE", "exercise_id": 1, "m1_auto_seconds": 8})
                instance.begin("test")
            instance.thread.join(timeout=3)
        self.assertFalse(instance.thread.is_alive())
        self.assertEqual(len(instance.samples), 9)
        self.assertTrue(all(s["ready"] and not s["preparation_ready"] for s in instance.samples))
        self.assertTrue(instance.recording_limit_reached)
        instance.stop()

    def test_projection_uses_pixels_and_both_hands(self):
        for hand, indices in [
            ("RIGHT", (12, 14, 16, 24, 26, 28)),
            ("LEFT", (11, 13, 15, 23, 25, 27)),
        ]:
            points = [SimpleNamespace(x=0, y=0, visibility=0, presence=0) for _ in range(33)]
            for i, xy in zip(
                indices, [(0.25, 0.2), (0.5, 0.3), (0.5, 0.5), (0.5, 0.6), (0.5, 0.75), (0.5, 0.9)]
            ):
                points[i] = SimpleNamespace(x=xy[0], y=xy[1], visibility=1.0, presence=1.0)
            measured, _, _ = measure_pose(points, 1280, 720, hand, 0.5, 1)
            self.assertEqual(measured["forearm_tilt"], 0.0)
            self.assertTrue(measured["forearm_down"])
            self.assertGreater(measured["torso_lean"], 30)
            wrist = indices[2]
            points[wrist].y = 0.1
            measured, _, _ = measure_pose(points, 1280, 720, hand, 0.5, 1)
            self.assertEqual(measured["forearm_tilt"], 180.0)
            self.assertFalse(measured["forearm_down"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
