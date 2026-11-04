r"""Run M1-M3 checks without a database, HTTP server or camera.

From the project root: .venv\Scripts\python.exe backend/tests/test_trial.py
"""

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.colour import ColourTracker
from app.vision import ball_metrics


class GeometryChecks(unittest.TestCase):
    def trace(self, fraction):
        y = 10 * (1 - fraction)
        return [
            {
                "t": i * 0.05,
                "balls": [
                    {"id": 1, "class": "cue_ball", "xy": [x, y]},
                    {"id": 2, "class": "target_ball", "xy": [15 if i >= 4 else 0, 0]},
                ],
            }
            for i, x in enumerate([-30, -20, -10, 0, 10, 20])
        ]

    def measure(self, trace, fraction=1):
        return ball_metrics(
            trace,
            {"ball_radius": 5, "max_frame_gap_s": 0.25, "contact_tolerance": 0},
            {"fraction": fraction},
        )

    def test_m2_does_not_require_a_target_ball_or_evaluate_contact(self):
        rows = [{"t": 0, "balls": [{"id": 1, "class": "cue_ball", "xy": [0, 0]}]}]
        self.assertEqual(
            ball_metrics(rows, {"ball_radius": 5, "table_size": [3569, 1778]}, {}), ({}, [])
        )

    def test_four_fractions(self):
        for f in [1, 0.75, 0.5, 0.25]:
            with self.subTest(f=f):
                measured, events = self.measure(self.trace(f), f)
                self.assertAlmostEqual(measured["contact_fraction"], f)
                self.assertTrue(events[0]["estimated"])

    def test_static_target_is_not_contact(self):
        trace = self.trace(1)
        for row in trace:
            row["balls"][1]["xy"] = [0, 0]
        measured, _ = self.measure(trace)
        self.assertIsNone(measured["contact_fraction"])

    def test_fast_ball_contact_between_frames(self):
        trace = [
            {
                "t": 0,
                "balls": [
                    {"id": 1, "class": "cue_ball", "xy": [-60, 0]},
                    {"id": 2, "class": "target_ball", "xy": [0, 0]},
                ],
            },
            {
                "t": 0.05,
                "balls": [
                    {"id": 1, "class": "cue_ball", "xy": [-30, 0]},
                    {"id": 2, "class": "target_ball", "xy": [0, 0]},
                ],
            },
            {
                "t": 0.1,
                "balls": [
                    {"id": 1, "class": "cue_ball", "xy": [30, 0]},
                    {"id": 2, "class": "target_ball", "xy": [10, 0]},
                ],
            },
        ]
        # One outgoing target observation without a consistent cue impulse
        # cannot establish contact. A second real departure confirms it.
        measured, _ = self.measure(trace)
        self.assertIsNone(measured["contact_fraction"])
        trace.append(
            {
                "t": 0.15,
                "balls": [
                    {"id": 1, "class": "cue_ball", "xy": [40, 0]},
                    {"id": 2, "class": "target_ball", "xy": [20, 0]},
                ],
            }
        )
        measured, _ = self.measure(trace)
        self.assertEqual(measured["contact_fraction"], 1)

    def test_preview_and_recording_do_not_store_images(self):
        import numpy as np

        from app.cameras import PreviewSource
        from app.runtime import Runtime

        cap = Mock()
        cap.read.return_value = (True, np.zeros((240, 320, 3), dtype=np.uint8))
        with patch("app.cameras.open_camera", return_value=cap):
            source = PreviewSource({"preview_camera": "top", "top_source": "1"})
            preview = source.read()
            source.close()
        self.assertFalse(preview["ready"])
        self.assertTrue(preview["preview_only"])
        self.assertEqual(preview["image_size"], [320, 240])
        fake = Mock()
        fake.read.side_effect = lambda: {
            "t": time.monotonic(),
            "image": "jpeg",
            "images": {"side": "jpeg"},
            "elbow_preview": {"image": "jpeg"},
            "ready": True,
        }
        runtime = Runtime()
        with patch("app.runtime.LiveSource", return_value=fake):
            try:
                runtime.start({"mode": "LIVE"})
                runtime.begin("isolated-trial")
                for _ in range(100):
                    if len(runtime.samples) >= 3:
                        break
                    time.sleep(0.01)
            finally:
                runtime.stop()
        self.assertGreaterEqual(len(runtime.samples), 3)
        self.assertTrue(
            all(
                "image" not in row and "images" not in row and "elbow_preview" not in row
                for row in runtime.samples
            )
        )

    def test_missing_and_switched_ids_and_gap(self):
        for kind in ["missing", "switch", "gap"]:
            with self.subTest(kind=kind):
                trace = self.trace(0.5)
                if kind == "missing":
                    trace[2]["balls"] = []
                if kind == "switch":
                    trace[2]["balls"][0]["id"] = 99
                if kind == "gap":
                    trace[2]["t"] = 2
                measured, events = self.measure(trace)
                self.assertIsNone(measured["contact_fraction"])
                self.assertEqual(events[0]["type"], "INVALID")

    def test_colour_tracking_and_ambiguity(self):
        import cv2
        import numpy as np

        tracker = ColourTracker(
            {
                "cue_ball": [{"lower": [0, 0, 180], "upper": [179, 40, 255]}],
                "target_ball": [{"lower": [0, 150, 80], "upper": [10, 255, 255]}],
            },
            50,
            1000,
            120,
            0.25,
        )
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        cv2.circle(image, (50, 100), 10, (255, 255, 255), -1)
        cv2.circle(image, (200, 100), 10, (0, 0, 255), -1)
        a = tracker.detect(image.copy(), 0, np.eye(3))
        b = tracker.detect(image.copy(), 0.05, np.eye(3))
        self.assertEqual([x["id"] for x in a], [x["id"] for x in b])
        cv2.circle(image, (100, 100), 10, (255, 255, 255), -1)
        self.assertNotIn("cue_ball", [x["class"] for x in tracker.detect(image, 0.1, np.eye(3))])

    def test_calibration(self):
        from tools.calibrate import calibrate

        result = calibrate(
            {
                "image_points": [[0, 0], [200, 0], [200, 100], [0, 100]],
                "table_points": [[0, 0], [400, 0], [400, 200], [0, 200]],
                "check_image_points": [[100, 50]],
                "check_table_points": [[200, 100]],
            }
        )
        self.assertLess(result["check_max_error"], 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
