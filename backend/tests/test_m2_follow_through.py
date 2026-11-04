"""RED3 software checks: synthetic pixels and trajectories, no camera or database."""

import copy
import json
import math
import os
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.colour import DEFAULT_BALL_COLOURS, M3_BALL_COLOURS
from app.criteria_templates import training_template
from app.m2_follow_through import (
    FollowThroughMonitor,
    FollowThroughPreparation,
    FollowThroughSource,
    assess_follow_through,
    reference_geometry,
)
from app.metrics import evaluate


def config():
    return {
        "exercise_id": 2,
        "m2_mode": "RED_GATE3",
        "top_source": "0",
        "required": ["top"],
        "homography": np.eye(3).tolist(),
        "table_size": [640, 320],
        "ball_radius": 10.0,
        "calibration_image_size": [640, 320],
        "calibration_check_error": 0.0,
        "ball_colours": DEFAULT_BALL_COLOURS,
        "m2_red_points": [[150 + 20 * i, y] for y in (130, 190) for i in range(3)],
        "m2_tip_offset_mm": 20.0,
        "cue_markers": [
            {"lower": [95, 100, 40], "upper": [135, 255, 255]},
            {"lower": [18, 100, 40], "upper": [38, 255, 255]},
        ],
        "ball_max_area": 5000,
        "ball_max_jump": 120,
        "max_frame_gap_s": 0.25,
        "baseline_seconds": 1.0,
        "min_valid_frames": 5,
        "motion_threshold": 2.0,
        "mode": "LIVE",
        "ball_detector": "HSV",
    }


def red_frame():
    frame = np.full((320, 640, 3), (35, 110, 35), np.uint8)
    for x, y in config()["m2_red_points"]:
        cv2.circle(frame, (x, y), 10, (0, 0, 220), -1)
    return frame


def rows(reach=True, shot=True):
    result = []
    for i in range(34):
        t = i / 10
        move = min(80 if reach else 50, max(0, (t - 1.2) * 220))
        tip = [120 + move, 160]
        result.append(
            {
                "t": t,
                "ready": True,
                "m2_capture_valid": True,
                "m2_tip_xy": tip,
                "m2_tip_margin_mm": tip[0] - 190,
                "m2_red_visible": [True] * 6,
                "balls": [
                    {
                        "class": "cue_ball",
                        "id": 1,
                        "xy": [150 + (max(0, t - 1.2) * 200 if shot else 0), 160],
                        "image_radius_px": 10,
                    }
                ],
            }
        )
    return result


class Red4Checks(unittest.TestCase):
    def test_blue_striker_and_yellow_tip_marker_work_together(self):
        c = {
            **config(),
            "cue_ball_colour": "BLUE",
            "ball_colours": M3_BALL_COLOURS,
            "cue_markers": [{"lower": [18, 100, 40], "upper": [38, 255, 255]}],
        }
        frame = red_frame()
        cv2.circle(frame, (150, 160), 10, (200, 70, 20), -1)
        cv2.circle(frame, (100, 160), 5, (0, 220, 220), -1)
        cv2.circle(frame, (400, 160), 10, (240, 240, 240), -1)
        cap = Mock()
        cap.read.return_value = (True, frame)
        with patch("app.m2_follow_through.open_camera", return_value=cap):
            source = FollowThroughSource(c)
        try:
            sample = source.read()
        finally:
            source.close()
        self.assertTrue(sample["ready"], sample["readiness_issues"])
        self.assertEqual(len(sample["balls"]), 1)
        self.assertLess(math.dist(sample["balls"][0]["image_xy"], [150, 160]), 1)
        self.assertLess(math.dist(sample["m2_tip_xy"], [120, 160]), 1)

    def test_blue_tracker_reacquires_without_emitting_missing_positions(self):
        c = {
            **config(),
            "cue_ball_colour": "BLUE",
            "ball_colours": M3_BALL_COLOURS,
            "cue_markers": [{"lower": [18, 100, 40], "upper": [38, 255, 255]}],
        }
        visible = red_frame()
        cv2.circle(visible, (150, 160), 10, (200, 70, 20), -1)
        cv2.circle(visible, (100, 160), 5, (0, 220, 220), -1)
        hidden = visible.copy()
        cv2.circle(hidden, (150, 160), 13, (35, 110, 35), -1)
        cap = Mock()
        cap.read.side_effect = [(True, visible.copy()), (True, hidden), (True, visible.copy())]
        with patch("app.m2_follow_through.open_camera", return_value=cap):
            source = FollowThroughSource(c)
        try:
            samples = []
            for stamp in (0.0, 0.1, 0.2):
                with patch("app.m2_follow_through.time.monotonic", return_value=stamp):
                    samples.append(source.read())
        finally:
            source.close()
        self.assertEqual(samples[1]["balls"], [])
        self.assertEqual(samples[0]["balls"][0]["id"], samples[2]["balls"][0]["id"])

    def test_single_marker_capture_and_current_criteria_pass_api_validation(self):
        os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://check:unused@127.0.0.1:1/check")
        from app.api.schemas import CaptureConfig, CriteriaRequest

        settings = config()
        settings["cue_markers"] = settings["cue_markers"][:1]
        self.assertEqual(len(CaptureConfig.model_validate(settings).cue_markers), 1)
        request = CriteriaRequest.model_validate(training_template(2))
        self.assertEqual(request.template_version, "m2-red-gate-single-v3")

    def test_single_attempt_protocol(self):
        from app.protocol import assessment_problem, protocol_result

        definition = {**training_template(2), "approved": True}
        settings = {**config(), "purpose": "ASSESSMENT", "m2_tip_offset_mm": 20}
        self.assertIsNone(assessment_problem(definition, settings))
        for counts, expected in [
            ({"PASS": 1}, "PASS"),
            ({"FAIL": 1}, "FAIL"),
            ({"INVALID": 1}, "INCOMPLETE"),
        ]:
            result = protocol_result(counts, definition, settings, "COMPLETED")
            self.assertEqual(result["status"], expected)
        old = copy.deepcopy(definition)
        old["protocol"]["required_valid_attempts"] = 5
        self.assertIsNotNone(assessment_problem(old, settings))
        old["template_version"] = "m2-red3-follow-v1"
        self.assertIsNotNone(assessment_problem(old, settings))

    def test_current_monitor_matches_final_scoring_and_resets(self):
        monitor = FollowThroughMonitor()
        items = rows()
        for n in range(1, len(items) + 1):
            evidence = monitor.update(items[:n], config())
        self.assertEqual(evidence["state"], "READY")
        self.assertEqual(evidence["method"], "m2-red-gate-single-v3")
        self.assertEqual(evidence, monitor.update(items + [{"t": 4, "balls": []}], config()))
        monitor.reset()
        self.assertEqual(monitor.evidence["state"], "BASELINE")

    def decision(self, items):
        values, evidence = assess_follow_through(items, config())
        outcome = (
            evaluate(
                values,
                {**training_template(2), "approved": True},
                evidence.get("valid_active_seconds"),
            )[0]
            if evidence["state"] == "READY"
            else "INVALID"
        )
        return outcome, values, evidence

    def test_reach_passes(self):
        state, values, e = self.decision(rows())
        self.assertEqual(state, "PASS")
        self.assertEqual(values["m2_red4_reached"], 1)
        self.assertGreater(values["m2_tip_margin_mm"], 0)
        self.assertEqual(e["method"], "m2-red-gate-single-v3")

    def test_short_follow_is_fail(self):
        state, values, _ = self.decision(rows(False))
        self.assertEqual(state, "FAIL")
        self.assertEqual(values["m2_red4_reached"], 0)

    def test_blue_entering_red_envelope_fails_even_with_long_follow(self):
        items = rows()
        items[13]["balls"][0]["xy"] = [155, 145]
        state, values, _ = self.decision(items)
        self.assertEqual(state, "FAIL")
        self.assertEqual(values["m2_gate_clear"], 0)

    def test_blue_grazing_uncertainty_is_not_a_pass(self):
        items = rows()
        for index in (13, 14, 15):
            items[index]["balls"][0]["xy"][1] = 151
        self.assertEqual(self.decision(items)[0], "INVALID")

    def test_missing_blue_before_gate_exit_is_invalid(self):
        items = rows()
        items[14]["balls"] = []
        self.assertEqual(self.decision(items)[0], "INVALID")

    def test_identity_change_after_launch_is_invalid(self):
        items = rows()
        items[14]["balls"][0]["id"] = 2
        self.assertEqual(self.decision(items)[0], "INVALID")

    def test_fast_blue_cannot_pass_by_skipping_channel(self):
        items = rows()
        items[14]["balls"][0]["xy"][0] += 40
        self.assertEqual(self.decision(items)[0], "INVALID")

    def test_blue_start_must_align_first_pair(self):
        items = rows()
        for row in items:
            row["balls"][0]["xy"][0] += 20
        self.assertEqual(self.decision(items)[0], "INVALID")

    def test_red_visibility_required_until_exit(self):
        for index in (5, 14):
            items = rows()
            items[index]["m2_red_visible"][0] = False
            self.assertEqual(self.decision(items)[0], "INVALID")

    def test_touching_rows_and_narrow_channel_geometry(self):
        reference_geometry(config())
        c = config()
        c["m2_red_points"] = c["m2_red_points"][:3]
        with self.assertRaises(ValueError):
            reference_geometry(c)
        c = config()
        for p in c["m2_red_points"][3:]:
            p[1] = 170
        with self.assertRaises(ValueError):
            reference_geometry(c)

    def test_no_shot_cannot_pass_even_if_tip_reaches(self):
        self.assertEqual(self.decision(rows(shot=False))[0], "INVALID")

    def test_one_frame_crossing_cannot_pass(self):
        items = rows(False)
        items[19].update(m2_tip_xy=[200, 160], m2_tip_margin_mm=10)
        self.assertEqual(self.decision(items)[0], "FAIL")

    def test_missing_marker_or_red_is_invalid(self):
        for index in [5, 16, 23]:
            items = rows()
            items[index]["m2_capture_valid"] = False
            self.assertEqual(self.decision(items)[0], "INVALID")

    def test_ball_can_leave_view_after_confirmed_departure(self):
        items = rows()
        for s in items[17:]:
            s["balls"] = []
        self.assertEqual(self.decision(items)[0], "PASS")

    def test_ball_missing_before_departure_is_invalid(self):
        items = rows()
        items[13]["balls"] = []
        self.assertEqual(self.decision(items)[0], "INVALID")

    def test_gap_and_ball_id_change_invalid(self):
        items = rows()
        items[5]["balls"][0]["id"] = 2
        self.assertEqual(self.decision(items)[0], "INVALID")
        self.assertEqual(
            self.decision([s for i, s in enumerate(rows()) if i not in (16, 17)])[0], "INVALID"
        )

    def test_preexisting_target_crossing_is_invalid(self):
        items = rows()
        for s in items[:11]:
            s.update(m2_tip_margin_mm=1, m2_tip_xy=[241, 160])
        self.assertEqual(self.decision(items)[0], "INVALID")

    def test_noise_or_reaching_only_after_window_does_not_pass(self):
        items = rows(False)
        for s in items[30:]:
            s.update(m2_tip_xy=[250, 160], m2_tip_margin_mm=10)
        self.assertEqual(self.decision(items)[0], "FAIL")

    def test_target_order_and_spacing_checked(self):
        c = config()
        c["m2_red_points"][1], c["m2_red_points"][2] = c["m2_red_points"][2], c["m2_red_points"][1]
        with self.assertRaises(ValueError):
            reference_geometry(c)

    def test_preparation_needs_stable_points(self):
        prep = FollowThroughPreparation(config())
        for s in rows()[:8]:
            prep.apply(s)
        self.assertEqual(s["m2_preparation"]["state"], "READY")
        bad = rows()[0]
        bad["ready"] = False
        prep.apply(bad)
        self.assertFalse(bad["ready"])

    def test_actual_pixel_source_uses_only_tip_marker_and_fixed_red_references(self):
        c = config()
        frame = red_frame()
        cv2.circle(frame, (150, 160), 10, (240, 240, 240), -1)
        cv2.circle(frame, (100, 160), 5, (200, 70, 20), -1)
        cap = Mock()
        cap.read.return_value = (True, frame)
        with patch("app.m2_follow_through.open_camera", return_value=cap):
            source = FollowThroughSource(c)
        try:
            sample = source.read()
        finally:
            source.close()
        self.assertTrue(sample["ready"], sample["readiness_issues"])
        self.assertEqual(sample["m2_reference_points"], c["m2_red_points"])
        self.assertEqual(len(sample["marker_detection"]["markers"]), 1)
        self.assertLess(math.dist(sample["m2_tip_xy"], [120, 160]), 1)
        self.assertEqual(len(sample["balls"]), 1)
        self.assertAlmostEqual(sample["m2_tip_margin_mm"], -70, delta=1)

    def test_finish_persists_three_metrics_and_evidence(self):
        os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://check:unused@127.0.0.1:1/check")
        from app.api import training as main

        attempt = SimpleNamespace(id="a", session_id="s", result_status="IN_PROGRESS")
        session = SimpleNamespace(
            id="s", profile_id=1, criteria_id=1, configuration_snapshot=config()
        )
        criteria = SimpleNamespace(
            id=1, exercise_id=2, definition={**training_template(2), "approved": True}
        )
        exercise = SimpleNamespace(id=2, module_id=2, setup_definition={})
        entities = {
            (main.Attempt, "a"): attempt,
            (main.TrainingSession, "s"): session,
            (main.Criteria, 1): criteria,
            (main.Exercise, 2): exercise,
        }
        db = MagicMock()
        db.get.side_effect = lambda model, key: entities.get((model, key))
        db.scalars.return_value = [
            SimpleNamespace(id=i + 1, code=k)
            for i, k in enumerate(
                ["m2_red4_reached", "m2_tip_margin_mm", "m2_tip_advance_mm", "m2_gate_clear"]
            )
        ]
        factory = MagicMock()
        factory.begin.return_value.__enter__.return_value = db
        runtime = SimpleNamespace(
            lock=threading.RLock(), attempt_id="a", samples=rows(), collecting=True, error=None
        )
        with patch.object(main, "DB", factory), patch.object(main, "runtime", runtime):
            answer = main.finish_attempt("a", main.FinishRequest(), user={"profile_id": 1})
        self.assertEqual(answer["status"], "PASS")
        self.assertEqual(db.add.call_count, 4)
        self.assertEqual(
            attempt.evidence["quality"]["m2_assessment"]["method"], "m2-red-gate-single-v3"
        )
        json.dumps(attempt.evidence, allow_nan=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
