"""Pose configuration and downloader integrity checks, without network/camera."""

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.download_pose import validate_bundle

from app.pose_settings import M1_POSE_MODEL, m1_capture_defaults, pose_options


class PoseModelChecks(unittest.TestCase):
    def test_m1_full_default_and_explicit_paths_preserved(self):
        config = {"pose_model": "models/pose_landmarker.task", "visibility": 0.7}
        selected = m1_capture_defaults(config, set())
        self.assertEqual(selected["pose_model"], M1_POSE_MODEL)
        self.assertEqual(selected["visibility"], 0.6)
        self.assertEqual(config["visibility"], 0.7)
        explicit = m1_capture_defaults(config, {"pose_model", "visibility"})
        self.assertEqual(explicit, config)

    def test_inference_options_m1_and_m2(self):
        fake = SimpleNamespace(
            tasks=SimpleNamespace(
                BaseOptions=lambda **kw: kw,
                vision=SimpleNamespace(
                    PoseLandmarkerOptions=lambda **kw: kw,
                    RunningMode=SimpleNamespace(VIDEO="VIDEO"),
                ),
            )
        )
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / "test.task"
            model.write_bytes(b"test")
            for module, confidence in [(1, 0.6), (2, 0.5)]:
                options = pose_options(fake, model, module)
                self.assertEqual(options["base_options"]["model_asset_buffer"], b"test")
                self.assertEqual(options["running_mode"], "VIDEO")
                self.assertEqual(options["num_poses"], 1)
                self.assertFalse(options["output_segmentation_masks"])
                for key in (
                    "min_pose_detection_confidence",
                    "min_pose_presence_confidence",
                    "min_tracking_confidence",
                ):
                    self.assertEqual(options[key], confidence)

    def test_download_bundle_rejects_wrong_content(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "model.task"
            target.write_bytes(b"not a task")
            with self.assertRaises(zipfile.BadZipFile):
                validate_bundle(target)
            with zipfile.ZipFile(target, "w") as z:
                z.writestr("wrong.tflite", b"x")
            with self.assertRaises(ValueError):
                validate_bundle(target)
            with zipfile.ZipFile(target, "w") as z:
                z.writestr("pose_detector.tflite", b"x")
                z.writestr("pose_landmarks_detector.tflite", b"y")
            validate_bundle(target)


if __name__ == "__main__":
    unittest.main(verbosity=2)
