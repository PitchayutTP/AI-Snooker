"""Direct video recording checks using synthetic camera frames."""

import os
import sys
import tempfile
import threading
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import recordings


class VideoChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=recordings.ROOT / "data")
        self.folder = Path(self.directory.name)
        self.scope = patch.object(recordings, "RECORDINGS", self.folder)
        self.scope.start()

    def tearDown(self):
        self.scope.stop()
        assert self.folder.resolve().is_relative_to((recordings.ROOT / "data").resolve())
        self.directory.cleanup()

    def recorder(self):
        return recordings.VideoRecorder(1, str(uuid4()), str(uuid4()))

    def test_direct_webm_flushes_and_preserves_elapsed_time(self):
        recorder = self.recorder()
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        try:
            for stamp in (0.0, 0.1, 0.25):
                recorder.write({"top": frame.copy()}, stamp)
            videos = recorder.close()
            self.assertIsNone(recorder.error)
            path = recordings.recorded_video_path(videos["top"]["path"], 1)
            self.assertTrue(path.is_file())
            self.assertEqual(list(recorder.folder.rglob("*.jpg")), [])
            self.assertEqual(videos["top"]["captured_frames"], 3)
            self.assertAlmostEqual(videos["top"]["duration_s"], 0.25)
            capture = cv2.VideoCapture(str(path))
            try:
                self.assertTrue(capture.read()[0])
                self.assertEqual(int(capture.get(cv2.CAP_PROP_FRAME_COUNT)), 6)
                self.assertEqual(int(capture.get(cv2.CAP_PROP_FPS)), 20)
            finally:
                capture.release()
            self.assertEqual(recorder.close(), videos)
            with self.assertRaises(ValueError):
                recordings.recorded_video_path(videos["top"]["path"], 2)
        finally:
            recorder.close()

    def test_queue_overflow_is_reported_without_blocking_capture(self):
        release = threading.Event()
        with patch.object(recordings.VideoRecorder, "_run", lambda self: release.wait(2)):
            recorder = self.recorder()
            try:
                frame = np.zeros((20, 20, 3), dtype=np.uint8)
                for i in range(32):
                    recorder.write({"top": frame}, i * 0.05)
                with self.assertRaises(ValueError):
                    recorder.write({"top": frame}, 2.0)
                self.assertIsNotNone(recorder.error)
            finally:
                release.set()
                recorder.close()

    def test_encoder_failure_does_not_publish_a_video(self):
        writer = Mock()
        writer.isOpened.return_value = False
        with patch("cv2.VideoWriter", return_value=writer):
            recorder = self.recorder()
            try:
                recorder.write({"side": np.zeros((20, 20, 3), dtype=np.uint8)}, 0.0)
                self.assertEqual(recorder.close(), {})
                self.assertIsNotNone(recorder.error)
            finally:
                recorder.close()

    def test_reset_cleans_generated_video_files(self):
        from app.training_reset import cleanup_recordings

        recorder = self.recorder()
        try:
            recorder.write({"side": np.zeros((20, 20, 3), dtype=np.uint8)}, 0.0)
            videos = recorder.close()
            path = recordings.recorded_video_path(videos["side"]["path"], 1)
            result = cleanup_recordings(self.folder, 1)
            self.assertTrue(result["cleanup_complete"])
            self.assertFalse(path.exists())
        finally:
            recorder.close()

    def test_clip_route_serves_the_saved_file_without_transcoding_or_deleting(self):
        os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://check:unused@127.0.0.1:1/check")
        from app.api import reports as main

        recorder = self.recorder()
        try:
            recorder.write({"top": np.zeros((20, 20, 3), dtype=np.uint8)}, 0.0)
            videos = recorder.close()
            attempt = SimpleNamespace(session_id="session", evidence={"videos": videos})
            session = SimpleNamespace(configuration_snapshot={"exercise_id": 2})
            with (
                patch.object(main, "DB", return_value=nullcontext()),
                patch.object(main, "require", return_value=attempt),
                patch.object(main, "owned_session", return_value=session),
                patch.object(recordings, "render_clip") as render,
            ):
                response = main.attempt_clip("attempt", {"profile_id": 1})
            self.assertEqual(response.media_type, "video/webm")
            self.assertIsNone(response.background)
            self.assertTrue(response.path.is_file())
            render.assert_not_called()
        finally:
            recorder.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
