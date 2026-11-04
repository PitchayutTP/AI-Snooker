"""M3 real OpenCV pixel-to-detection-to-contact tests; synthetic table, no devices/DB.
These verify software behavior, not accuracy on a real snooker table.
"""

import math
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.calibration_policy import M3_CALIBRATION_LIMIT_MM, m3_calibration_accepted
from app.cameras import PreviewSource
from app.colour import DEFAULT_BALL_COLOURS, M3_BALL_COLOURS, ColourTracker
from app.criteria_templates import training_template
from app.m3_monitor import M3Monitor
from app.m3_readiness import M3Preparation, position_tolerance
from app.metrics import evaluate
from app.vision import LiveSource, ball_metrics

COLOURS = {
    "cue_ball": [{"lower": [0, 0, 160], "upper": [179, 75, 255]}],
    "target_ball": [
        {"lower": [0, 110, 70], "upper": [10, 255, 255]},
        {"lower": [170, 110, 70], "upper": [179, 255, 255]},
    ],
}


def config():
    return {
        "exercise_id": 3,
        "required": ["top"],
        "top_source": "0",
        "ball_detector": "HSV",
        "ball_colours": COLOURS,
        "ball_min_area": 12,
        "ball_max_area": 5000,
        "ball_max_jump": 120,
        "max_frame_gap_s": 0.25,
        "homography": np.eye(3).tolist(),
        "table_size": [600, 280],
        "ball_radius": 10.0,
        "baseline_seconds": 1.0,
        "min_valid_frames": 5,
        "contact_tolerance": 0,
        "motion_threshold": 2.0,
        "calibration_image_size": [640, 320],
    }


def image(cue=(100, 160), target=(320, 160), glare=False):
    frame = np.full((320, 640, 3), (35, 110, 35), dtype=np.uint8)
    cv2.circle(frame, tuple(map(round, cue)), 10, (240, 240, 240), -1)
    cv2.circle(frame, tuple(map(round, target)), 10, (0, 0, 200), -1)
    if glare:
        cv2.circle(frame, tuple(map(round, target)), 2, (255, 255, 255), -1)
    return frame


class M3Checks(unittest.TestCase):
    def test_fast_exit_after_one_confirmed_outgoing_frame_all_fractions(self):
        for fraction in (1.0, 0.75, 0.5, 0.25):
            rows = self.sequence(fraction)[:18]
            last = rows[-1]
            rows += [
                {
                    "t": last["t"] + 0.1 * i,
                    "balls": [b for b in last["balls"] if b["class"] == "cue_ball"],
                }
                for i in range(1, 6)
            ]
            c = {**config(), "target_fraction": fraction}
            values, events = ball_metrics(rows, c, {"fraction": fraction})
            self.assertAlmostEqual(values["contact_fraction"], fraction, delta=0.06)
            self.assertEqual(events[0]["confirmation"], "single-departure-and-cue-impulse")
            self.assertEqual(M3Monitor().update(rows, c)["state"], "READY")
            self.assertEqual(
                evaluate(
                    values,
                    {**training_template(3, fraction), "approved": True},
                    events[0]["valid_active_seconds"],
                )[0],
                "PASS",
            )

    def test_disappearance_alone_or_single_unmatched_target_motion_cannot_confirm_contact(self):
        rows = self.sequence(0.5)[:17]
        rows += [{"t": rows[-1]["t"] + 0.1, "balls": []}]
        self.assertIsNone(ball_metrics(rows, config(), {"fraction": 0.5})[0]["contact_fraction"])
        rows = self.sequence(0.5)[:18]
        before = next(b["xy"] for b in rows[-2]["balls"] if b["class"] == "cue_ball")
        next(b for b in rows[-1]["balls"] if b["class"] == "cue_ball")["xy"] = [
            before[0] + 20,
            before[1],
        ]
        self.assertIsNone(ball_metrics(rows, config(), {"fraction": 0.5})[0]["contact_fraction"])

    def test_fast_exit_after_bounded_contact_gap_all_fractions(self):
        for fraction in (1.0, 0.75, 0.5, 0.25):
            rows = self.sequence(fraction, fast=True)[:19]
            rows[16]["balls"] = []
            rows[17]["balls"] = []
            rows.append({"t": rows[-1]["t"] + 0.04, "balls": []})
            c = {**config(), "m3_brief_loss_seconds": 0.35, "m3_max_missing_frames": 6}
            values, events = ball_metrics(rows, c, {"fraction": fraction})
            self.assertIsNotNone(values["contact_fraction"], events)
            self.assertAlmostEqual(values["contact_fraction"], fraction, delta=0.06)

    def test_covered_launch_can_resume_before_contact_for_thin_fractions(self):
        for fraction in (0.5, 0.25):
            rows = self.sequence(fraction)
            for index in (12, 13):
                rows[index]["balls"] = []
            c = {
                **config(),
                "max_frame_gap_s": 0.35,
                "m3_brief_loss_seconds": 0.35,
                "m3_max_missing_frames": 6,
                "m3_stationary_loss_seconds": 1.0,
            }
            values, events = ball_metrics(rows, c, {"fraction": fraction})
            self.assertAlmostEqual(values["contact_fraction"], fraction, delta=0.06)
            self.assertTrue(events[0]["brief_occlusions"][0]["covered_launch"])
            self.assertFalse(events[0]["brief_occlusions"][0]["interpolated"])
            self.assertEqual(
                M3Monitor().update(rows, {**c, "target_fraction": fraction})["state"], "READY"
            )

    def test_motion_without_supported_contact_times_out(self):
        rows = self.sequence()
        for i, row in enumerate(rows):
            row["t"] *= 2
            for b in row["balls"]:
                b["xy"] = (
                    [200.0 - max(0, i - 12) * 5, 160.0]
                    if b["class"] == "cue_ball"
                    else [320.0, 160.0]
                )
        last = rows[-1]
        rows += [{**last, "t": last["t"] + 0.2 * i} for i in range(1, 16)]
        state = M3Monitor().update(
            rows, {**config(), "max_frame_gap_s": 0.25, "target_fraction": 0.25}
        )
        self.assertEqual(state["state"], "INVALID")
        self.assertIn("3 วินาที", state["reason"])

    def test_all_detected_fractions_are_scored_against_every_target(self):
        for actual in (1.0, 0.75, 0.5, 0.25):
            rows = self.sequence(actual, blue=True, fast=True)
            for requested in (1.0, 0.75, 0.5, 0.25):
                values, events = ball_metrics(rows, config(), {"fraction": requested})
                self.assertIsNotNone(values["contact_fraction"], events)
                self.assertAlmostEqual(values["contact_fraction"], actual, delta=0.06)
                expected = "PASS" if actual == requested else "FAIL"
                self.assertEqual(
                    evaluate(values, {**training_template(3, requested), "approved": True}, 2)[0],
                    expected,
                )

    def test_partial_shape_requires_previous_ball_and_does_not_relabel_objects(self):
        tracker = ColourTracker(
            COLOURS, 12, 5000, 120, 0.25, 10, [600, 280], temporal_association=True
        )
        original = tracker.detect(image(), 0, np.eye(3))
        frame = image()
        cv2.rectangle(frame, (89, 156), (99, 164), (35, 110, 35), -1)
        found = tracker.detect(frame, 0.04, np.eye(3))
        cue = next(ball for ball in found if ball["class"] == "cue_ball")
        self.assertTrue(cue["partial_occlusion"])
        self.assertEqual(cue["id"], original[0]["id"])
        self.assertLess(math.dist(cue["image_xy"], [100, 160]), 1)
        fresh = ColourTracker(
            COLOURS, 12, 5000, 120, 0.25, 10, [600, 280], temporal_association=True
        )
        self.assertNotIn(
            "cue_ball", [ball["class"] for ball in fresh.detect(frame, 0.04, np.eye(3))]
        )

    def test_wrong_fraction_between_camera_frames_is_fail_against_full_ball(self):
        for fraction in (0.75, 0.5, 0.25):
            rows = self.sequence(fraction, fast=True)
            sparse = rows[:12] + rows[12::3]
            values, events = ball_metrics(sparse, config(), {"fraction": 1.0})
            self.assertIsNotNone(values["contact_fraction"], events)
            self.assertAlmostEqual(values["contact_fraction"], fraction, delta=0.06)
            self.assertEqual(
                evaluate(values, {**training_template(3, 1.0), "approved": True}, 2)[0], "FAIL"
            )

    def test_thin_hit_can_finish_after_confirmed_departure_before_target_leaves(self):
        rows = self.sequence(0.5)
        # Long pre-shot wait, then just two real outgoing observations.
        samples = rows[:12] + [{**row, "t": row["t"] + 1.0} for row in rows[12:19]]
        samples += [{"t": samples[-1]["t"] + 0.1, "balls": []}]
        monitor = M3Monitor()
        state = monitor.update(
            samples, {**config(), "max_frame_gap_s": 1.5, "target_fraction": 1.0}
        )
        self.assertEqual(state["state"], "READY")
        self.assertGreater(state["fraction_error"], 0.1)

    def test_stationary_cue_occlusion_recovers_before_shot(self):
        rows = self.sequence(0.5)
        c = {
            **config(),
            "m3_brief_loss_seconds": 0.25,
            "m3_max_missing_frames": 6,
            "m3_stationary_loss_seconds": 1.0,
        }
        hidden = [{"t": 1.15 + i * 0.1, "balls": []} for i in range(5)]
        later = [{**row, "t": row["t"] + 0.7} for row in rows[11:]]
        samples = rows[:11] + hidden + later
        pending = M3Monitor().update(samples[:16], {**c, "target_fraction": 0.5})
        self.assertEqual(pending["state"], "RECOVERING")
        values, events = ball_metrics(samples, c, {"fraction": 0.5})
        self.assertIsNotNone(values["contact_fraction"], events)
        self.assertTrue(events[0]["brief_occlusions"][0]["stationary"])
        self.assertFalse(events[0]["brief_occlusions"][0]["interpolated"])
        samples[16]["balls"][0]["xy"] = [260.0, 170.0]
        self.assertIsNone(ball_metrics(samples, c, {"fraction": 0.5})[0]["contact_fraction"])

    def test_tracker_keeps_identity_during_stationary_occlusion_without_emitting_positions(self):
        tracker = ColourTracker(
            COLOURS, 12, 5000, 120, 1.0, 10, [600, 280], temporal_association=True
        )
        original = tracker.detect(image(), 0, np.eye(3))
        blank = np.full((320, 640, 3), (35, 110, 35), dtype=np.uint8)
        self.assertEqual(tracker.detect(blank, 0.5, np.eye(3)), [])
        restored = tracker.detect(image(), 0.7, np.eye(3))
        self.assertEqual([b["id"] for b in restored], [b["id"] for b in original])

    def test_live_monitor_uses_same_contact_evidence_and_resets(self):
        items = self.sequence()
        monitor = M3Monitor()
        states = []
        c = {**config(), "target_fraction": 1.0}
        for n in range(1, len(items) + 1):
            states.append(dict(monitor.update(items[:n], c)))
        self.assertEqual(states[0]["state"], "BASELINE")
        self.assertEqual(states[-1]["state"], "READY")
        self.assertEqual(states[-1]["detected_events"], 1)
        self.assertIsNotNone(states[-1]["contact_fraction"])
        frozen = dict(states[-1])
        self.assertEqual(monitor.update(items + [{"t": 3.5, "balls": []}], c), frozen)
        monitor.reset()
        self.assertEqual(monitor.state["state"], "BASELINE")

    def test_monitor_never_calls_missing_or_static_balls_ready(self):
        c = {**config(), "target_fraction": 1.0}
        monitor = M3Monitor()
        items = self.sequence()
        for s in items:
            for b in s["balls"]:
                b["xy"] = [200.0, 160.0] if b["class"] == "cue_ball" else [320.0, 160.0]
        self.assertEqual(monitor.update(items, c)["state"], "WAITING_SHOT")
        items[13]["balls"] = []
        monitor.reset()
        self.assertEqual(monitor.update(items, c)["state"], "INVALID")

    def test_relaxed_calibration_limit_does_not_relax_contact_proximity(self):
        self.assertEqual(M3_CALIBRATION_LIMIT_MM, 50)
        for error in [0, 7, 25, 50]:
            self.assertTrue(m3_calibration_accepted(error))
        for error in [50.01, 66.9, float("nan"), -1]:
            self.assertFalse(m3_calibration_accepted(error))
        balls = [{"image_radius_px": 26.25}]
        self.assertEqual(
            position_tolerance(balls, 26.25, calibration_error=50),
            position_tolerance(balls, 26.25, calibration_error=6.5625),
        )

    def test_old_ivory_ball_under_brightness_and_saturation_changes(self):
        tracker = ColourTracker(DEFAULT_BALL_COLOURS, 12, 5000, 120, 0.25)
        for i, (hue, saturation, value) in enumerate(
            [(25, 80, 220), (28, 120, 170), (25, 140, 120), (0, 0, 240)]
        ):
            hsv = np.full((320, 640, 3), (60, 160, 140), dtype=np.uint8)
            cv2.circle(hsv, (100, 160), 10, (hue, saturation, value), -1)
            cv2.circle(hsv, (320, 160), 10, (0, 230, 200), -1)
            # A saturated yellow ball must not become the ivory cue ball.
            cv2.circle(hsv, (500, 160), 10, (28, 230, 210), -1)
            balls = tracker.detect(cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR), i * 0.1, np.eye(3))
            self.assertEqual({b["class"] for b in balls}, {"cue_ball", "target_ball"})
            cue = next(b for b in balls if b["class"] == "cue_ball")
            self.assertLess(math.dist(cue["image_xy"], [100, 160]), 1)
            self.assertEqual(cue["id"], 1)

    def test_uncalibrated_colour_preview_does_not_emit_table_measurements(self):
        settings = {**config(), "preview_camera": "top", "detect_ball_preview": True}
        for key in ["homography", "table_size", "ball_radius"]:
            settings.pop(key)
        cap = Mock()
        cap.read.return_value = (True, image())
        with patch("app.cameras.open_camera", return_value=cap):
            source = PreviewSource(settings)
        try:
            row = source.read()
            self.assertTrue(row["preview_only"])
            self.assertTrue(row["detection_preview"])
            self.assertFalse(row["ready"])
            self.assertEqual({b["class"] for b in row["balls"]}, {"cue_ball", "target_ball"})
            for ball in row["balls"]:
                self.assertIn("image_xy", ball)
                self.assertNotIn("xy", ball)
                self.assertNotIn("table_radius_estimate", ball)
            self.assertTrue(
                all(d["status"] == "OK" for d in row["ball_detection"]["roles"].values())
            )
        finally:
            source.close()
        cap.release.assert_called_once()

    def test_raw_preview_has_no_detection_overlay(self):
        original = image()
        settings = {**config(), "preview_camera": "top"}
        cap = Mock()
        cap.read.return_value = (True, original)
        with patch("app.cameras.open_camera", return_value=cap):
            source = PreviewSource(settings)
        try:
            row = source.read()
            self.assertFalse(row["detection_preview"])
            self.assertEqual(row["balls"], [])
            self.assertTrue(np.array_equal(original, image()))
        finally:
            source.close()

    def tracker(self, colours=COLOURS):
        return ColourTracker(colours, 12, 5000, 120, 0.25, 10, [600, 280])

    def sequence(self, fraction=1.0, miss=False, blue=False, drop_frames=(), fast=False):
        target = np.array([320.0, 160.0])
        offset = 35.0 if miss else 20 * (1 - fraction)
        frames = [image((200, 160 + offset)) for _ in range(12)]
        if miss:
            frames.extend(
                image((x, 160 + offset)) for x in [220, 240, 260, 280, 300, 320, 340, 360, 380, 400]
            )
        else:
            nx = math.sqrt(400 - offset * offset) / 20
            ny = -offset / 20
            contact = np.array([320 - 20 * nx, 160 + offset])
            frames.extend(image((x, 160 + offset), glare=True) for x in [220, 240, 260, 280])
            frames.append(image(contact, glare=True))
            for i in range(1, 8):
                cue = contact + np.array([1 - nx * nx, -nx * ny]) * 15 * i
                obj = target + np.array([nx, ny]) * 15 * i
                frames.append(image(cue, obj, glare=True))
        settings = config()
        if blue:
            settings.update(ball_colours=M3_BALL_COLOURS, cue_ball_colour="BLUE")
            for frame in frames:
                frame[np.all(frame > 220, axis=2)] = (200, 70, 20)
        for index in drop_frames:
            frames[index] = np.full_like(frames[index], (35, 110, 35))
        cap = Mock()
        cap.isOpened.return_value = True
        cap.grab.return_value = True
        cap.retrieve.side_effect = [(True, frame.copy()) for frame in frames]
        with patch("app.vision.open_camera", return_value=cap):
            source = LiveSource(settings)
        try:
            rows = []
            for i in range(len(frames)):
                stamp = 1.2 + (i - 12) * 0.04 if fast and i >= 12 else i * 0.1
                with patch("app.vision.time.monotonic", return_value=stamp):
                    rows.append(source.read())
        finally:
            source.close()
        return rows

    def test_blue_ball_through_live_source_all_four_fractions(self):
        for fraction in [1.0, 0.75, 0.5, 0.25]:
            rows = self.sequence(fraction, blue=True)
            self.assertTrue(all(len(s["balls"]) == 2 for s in rows))
            values, events = ball_metrics(rows, config(), {"fraction": fraction})
            self.assertIsNotNone(values["contact_fraction"], events)
            self.assertLess(abs(values["contact_fraction"] - fraction), 0.06)

    def test_brief_real_detection_loss_reacquires_same_ids_without_fabricated_points(self):
        for missing in [(16,), (16, 17)]:
            items = self.sequence(0.5, blue=True, drop_frames=missing, fast=True)
            for index in missing:
                self.assertEqual(items[index]["balls"], [])
            self.assertEqual(
                [b["id"] for b in items[15]["balls"]],
                [b["id"] for b in items[missing[-1] + 1]["balls"]],
            )
            c = {
                **config(),
                "m3_brief_loss_seconds": 0.12,
                "m3_max_missing_frames": 2,
                "cue_ball_colour": "BLUE",
            }
            values, events = ball_metrics(items, c, {"fraction": 0.5})
            self.assertIsNotNone(values["contact_fraction"], events)
            self.assertLess(abs(values["contact_fraction"] - 0.5), 0.06)
            self.assertEqual(events[0]["brief_occlusions"][0]["missing_frames"], len(missing))
            self.assertFalse(events[0]["brief_occlusions"][0]["interpolated"])

    def test_long_or_ambiguous_loss_still_invalid_in_brief_loss_mode(self):
        c = {**config(), "m3_brief_loss_seconds": 0.12, "m3_max_missing_frames": 2}
        items = self.sequence(0.5, blue=True, drop_frames=(16, 17, 18), fast=True)
        self.assertIsNone(ball_metrics(items, c, {"fraction": 0.5})[0]["contact_fraction"])

    def test_brief_loss_does_not_turn_static_or_wrongly_moving_target_into_contact(self):
        c = {**config(), "m3_brief_loss_seconds": 0.12, "m3_max_missing_frames": 2}
        for wrong_direction in [False, True]:
            items = self.sequence(0.5, blue=True, drop_frames=(16, 17), fast=True)
            for s in items:
                for ball in s["balls"]:
                    if ball["class"] == "target_ball":
                        ball["xy"] = (
                            [640 - ball["xy"][0], 320 - ball["xy"][1]]
                            if wrong_direction
                            else [320.0, 160.0]
                        )
            self.assertIsNone(ball_metrics(items, c, {"fraction": 0.5})[0]["contact_fraction"])
        items = self.sequence(0.5, blue=True, drop_frames=(16,), fast=False)
        self.assertIsNone(ball_metrics(items, c, {"fraction": 0.5})[0]["contact_fraction"])
        items = self.sequence(0.5, blue=True, fast=True)
        items[16]["balls"].append(dict(items[16]["balls"][0]))
        self.assertIsNone(ball_metrics(items, c, {"fraction": 0.5})[0]["contact_fraction"])

    def test_temporal_association_ignores_only_unique_far_distractor(self):
        tracker = ColourTracker(
            M3_BALL_COLOURS, 12, 5000, 120, 0.25, 10, [600, 280], temporal_association=True
        )
        frame = image()
        frame[np.all(frame > 220, axis=2)] = (200, 70, 20)
        before = tracker.detect(frame, 0, np.eye(3))
        identity = next(b["id"] for b in before if b["class"] == "cue_ball")
        cv2.circle(frame, (500, 160), 10, (200, 70, 20), -1)
        found = tracker.detect(frame, 0.04, np.eye(3))
        cue = next(b for b in found if b["class"] == "cue_ball")
        self.assertEqual(cue["id"], identity)
        self.assertLess(math.dist(cue["image_xy"], [100, 160]), 1)
        cv2.circle(frame, (150, 160), 10, (200, 70, 20), -1)
        self.assertNotIn("cue_ball", [b["class"] for b in tracker.detect(frame, 0.08, np.eye(3))])

    def test_pixels_through_live_source_all_four_fractions(self):
        for fraction in [1.0, 0.75, 0.5, 0.25]:
            with self.subTest(fraction=fraction):
                rows = self.sequence(fraction)
                self.assertTrue(all(len(s["balls"]) == 2 for s in rows))
                values, events = ball_metrics(rows, config(), {"fraction": fraction})
                self.assertIsNotNone(values["contact_fraction"], events)
                self.assertLess(abs(values["contact_fraction"] - fraction), 0.06)
                definition = {**training_template(3, fraction), "approved": True}
                self.assertEqual(evaluate(values, definition, rows[-1]["t"] - 1)[0], "PASS")
                self.assertEqual(events[0]["type"], "CONTACT_CANDIDATE")

    def test_clear_miss_is_fail_not_invalid(self):
        values, events = ball_metrics(self.sequence(miss=True), config(), {"fraction": 1.0})
        self.assertEqual(values["contact_fraction"], 0.0)
        self.assertEqual(events[0]["type"], "CLEAR_MISS")
        self.assertEqual(
            evaluate(values, {**training_template(3, 1.0), "approved": True}, 2)[0], "FAIL"
        )

    def test_wrong_fraction_is_fail(self):
        values, _ = ball_metrics(self.sequence(0.5), config(), {"fraction": 1.0})
        self.assertEqual(
            evaluate(values, {**training_template(3, 1.0), "approved": True}, 2)[0], "FAIL"
        )

    def test_stopping_before_target_does_not_prove_miss(self):
        rows = self.sequence(miss=True)[:16]
        self.assertIsNone(ball_metrics(rows, config(), {"fraction": 1.0})[0]["contact_fraction"])

    def test_static_target_proximity_does_not_prove_contact(self):
        rows = self.sequence()
        for row in rows:
            for ball in row["balls"]:
                if ball["class"] == "target_ball":
                    ball["xy"] = [320.0, 160.0]
        self.assertIsNone(ball_metrics(rows, config(), {"fraction": 1.0})[0]["contact_fraction"])

    def test_tail_loss_preserves_earlier_supported_contact(self):
        rows = self.sequence(0.5)
        rows.append({"t": rows[-1]["t"] + 0.1, "balls": []})
        self.assertIsNotNone(ball_metrics(rows, config(), {"fraction": 0.5})[0]["contact_fraction"])

    def test_loss_during_contact_is_invalid(self):
        rows = self.sequence(0.5)
        rows[16]["balls"] = []
        values, events = ball_metrics(rows, config(), {"fraction": 0.5})
        self.assertIsNone(values["contact_fraction"])
        self.assertIn("จุดตรวจจับ", events[0]["reason_th"])

    def test_track_switch_before_contact_is_invalid(self):
        rows = self.sequence()
        rows[14]["balls"][0]["id"] = 99
        self.assertIsNone(ball_metrics(rows, config(), {"fraction": 1.0})[0]["contact_fraction"])

    def test_large_gap_before_contact_is_invalid(self):
        rows = self.sequence()
        rows[14]["t"] += 1
        self.assertIsNone(ball_metrics(rows, config(), {"fraction": 1.0})[0]["contact_fraction"])

    def test_early_strike_is_not_valid_baseline(self):
        rows = self.sequence()[10:]
        self.assertIsNone(ball_metrics(rows, config(), {"fraction": 1.0})[0]["contact_fraction"])

    def test_no_incoming_line_cannot_infer_angle_from_deflection(self):
        rows = self.sequence()[16:]
        self.assertIsNone(
            ball_metrics(rows, {**config(), "baseline_seconds": 0}, {"fraction": 1.0})[0][
                "contact_fraction"
            ]
        )

    def test_detector_does_not_modify_input_and_rejects_glare(self):
        frame = image(glare=True)
        original = frame.copy()
        tracker = self.tracker()
        balls = tracker.detect(frame, 0, np.eye(3))
        self.assertTrue(np.array_equal(frame, original))
        self.assertEqual(len(balls), 2)
        self.assertEqual(tracker.diagnostics["cue_ball"]["candidates"], 1)

    def test_red_hue_wrap_shadows_and_noise(self):
        frame = image()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        cv2.circle(hsv, (320, 160), 10, (179, 220, 90), -1)
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        for x in range(30, 100, 5):
            frame[40, x] = (0, 0, 255)
        self.assertEqual(len(self.tracker().detect(frame, 0, np.eye(3))), 2)

    def test_ambiguity_and_missing_are_not_cached(self):
        tracker = self.tracker()
        first = tracker.detect(image(), 0, np.eye(3))
        frame = image()
        cv2.circle(frame, (200, 80), 10, (0, 0, 200), -1)
        balls = tracker.detect(frame, 0.1, np.eye(3))
        self.assertNotIn("target_ball", [b["class"] for b in balls])
        self.assertEqual(tracker.diagnostics["target_ball"]["status"], "AMBIGUOUS")
        reappeared = tracker.detect(image(), 0.2, np.eye(3))
        self.assertNotEqual(first[1]["id"], reappeared[1]["id"])

    def test_size_and_roi_filter(self):
        frame = image()
        cv2.circle(frame, (320, 160), 13, (35, 110, 35), -1)
        cv2.circle(frame, (320, 160), 3, (0, 0, 255), -1)
        self.assertNotIn(
            "target_ball", [b["class"] for b in self.tracker().detect(frame, 0, np.eye(3))]
        )
        frame = image()
        cv2.circle(frame, (620, 300), 10, (0, 0, 200), -1)
        self.assertEqual(len(self.tracker().detect(frame, 0, np.eye(3))), 2)

    def test_diagnostics_distinguish_colour_outside_roi_and_wrong_scale(self):
        frame = image()
        tracker = self.tracker()
        tracker.detect(frame, 0, np.eye(3), roi_mask=np.zeros(frame.shape[:2], np.uint8))
        for d in tracker.diagnostics.values():
            self.assertGreater(d["raw_mask_pixels"], 0)
            self.assertEqual(d["roi_mask_pixels"], 0)
            self.assertEqual(d["mask_pixels"], 0)
        wrong = ColourTracker(COLOURS, 12, 5000, 120, 0.25, 30, [600, 280])
        self.assertEqual(wrong.detect(frame, 0, np.eye(3)), [])
        d = wrong.diagnostics["cue_ball"]
        self.assertGreater(d["mask_pixels"], 0)
        self.assertGreater(d["rejected"]["size"], 0)
        self.assertEqual(d["size_examples"][0]["expected_diameter"], 60)
        self.assertLess(d["size_examples"][0]["equivalent_diameter"], 25)

    def test_colour_overlap_is_not_two_balls(self):
        tracker = self.tracker(
            {"cue_ball": COLOURS["cue_ball"], "target_ball": COLOURS["cue_ball"]}
        )
        self.assertEqual(tracker.detect(image(), 0, np.eye(3)), [])
        self.assertEqual(tracker.diagnostics["cue_ball"]["status"], "COLOUR_OVERLAP")

    def test_preparation_stationary_separated_and_not_required_during_recording(self):
        gate = M3Preparation(config())
        balls = [
            {"class": "cue_ball", "id": 1, "xy": [100.0, 100.0]},
            {"class": "target_ball", "id": 2, "xy": [200.0, 100.0]},
        ]
        for i in range(6):
            sample = {"t": i * 0.1, "ready": True, "balls": balls, "readiness_issues": []}
            gate.apply(sample)
        self.assertTrue(sample["ready"])
        moving = [{**balls[0], "xy": [180.0, 100.0]}, balls[1]]
        sample = {"t": 0.6, "ready": True, "balls": moving, "readiness_issues": []}
        gate.apply(sample)
        self.assertFalse(sample["ready"])
        self.assertEqual(sample["m3_preparation"]["state"], "TOUCHING")
        sample = {"t": 0.7, "ready": True, "balls": moving, "readiness_issues": []}
        gate.apply(sample, True)
        self.assertTrue(sample["ready"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
