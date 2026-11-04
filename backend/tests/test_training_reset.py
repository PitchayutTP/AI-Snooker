"""Reset regression checks: mocked DB, generated temporary files only. No cameras/server."""

import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://check:unused@127.0.0.1:1/check"
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.api import reports as main
from app.runtime import Runtime
from app.training_reset import cleanup_recordings, recording_cleanup_plan


class ResetChecks(unittest.TestCase):
    def setUp(self):
        folder = Path(__file__).resolve().parents[2] / "data/offline-checks"
        folder.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=folder)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "recordings"
        self.photos = {}
        for profile in (1, 2):
            photo = self.root / str(profile) / "session/attempt/side/000000.jpg"
            photo.parent.mkdir(parents=True)
            photo.write_bytes(b"test evidence")
            self.photos[profile] = photo
        self.db = MagicMock()
        self.db.execute.side_effect = [SimpleNamespace(rowcount=n) for n in (3, 2, 1)]
        self.database = MagicMock()
        self.database.begin.return_value.__enter__.return_value = self.db

    def call(self, runtime=None):
        with (
            patch.object(main, "DB", self.database),
            patch.object(main, "runtime", runtime or Runtime()),
            patch.object(main, "RECORDINGS", self.root),
        ):
            return main.reset_training(
                main.ResetTrainingRequest(confirmation="RESET_TRAINING"), user={"profile_id": 2}
            )

    def test_own_rows_and_images_only(self):
        result = self.call()
        self.assertEqual(result["sessions_removed"], 1)
        self.assertEqual(result["images_removed"], 1)
        self.assertTrue(result["cleanup_complete"])
        self.assertTrue(self.photos[1].exists())
        self.assertFalse(self.photos[2].exists())
        statements = [
            str(
                call.args[0].compile(
                    dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
                )
            )
            for call in self.db.execute.call_args_list
        ]
        self.assertEqual(len(statements), 3)
        for statement in statements:
            self.assertIn("training_sessions.profile_id = 2", statement)
            self.assertNotIn("DELETE FROM accounts", statement)
            self.assertNotIn("DELETE FROM criteria_versions", statement)
        self.assertTrue(statements[0].startswith("DELETE FROM measurements"))
        self.assertTrue(statements[1].startswith("DELETE FROM attempts"))

    def test_active_round_blocks_everything(self):
        runtime = Runtime()
        runtime.session_id = "active"
        with self.assertRaises(HTTPException) as error:
            self.call(runtime)
        self.assertEqual(error.exception.status_code, 409)
        self.database.begin.assert_not_called()
        self.assertTrue(self.photos[2].exists())

    def test_database_failure_preserves_images(self):
        self.db.execute.side_effect = RuntimeError("mock transaction failure")
        with self.assertRaises(RuntimeError):
            self.call()
        self.assertTrue(self.photos[2].exists())

    def test_confirmation_required(self):
        for body in ({}, {"confirmation": "wrong"}):
            with self.assertRaises(ValidationError):
                main.ResetTrainingRequest.model_validate(body)

    def test_unexpected_file_blocks_deletion(self):
        extra = self.root / "2/keep.txt"
        extra.write_text("keep")
        with self.assertRaises(HTTPException):
            self.call()
        self.database.begin.assert_not_called()
        self.assertTrue(self.photos[2].exists())
        self.assertTrue(extra.exists())

    def test_cleanup_idempotent_and_bounded(self):
        self.assertTrue(cleanup_recordings(self.root, 2)["cleanup_complete"])
        self.assertEqual(cleanup_recordings(self.root, 2)["images_removed"], 0)
        self.assertTrue(self.photos[1].exists())
        for profile in (0, -1, "../1"):
            with self.assertRaises(ValueError):
                recording_cleanup_plan(self.root, profile)

    def test_owned_capture_memory_cleared(self):
        runtime = Runtime()
        runtime.owner_profile_id = 2
        runtime.samples = [{"old": True}]
        runtime.config = {"old": True}
        self.call(runtime)
        self.assertEqual(runtime.samples, [])
        self.assertEqual(runtime.config, {})
        self.assertIsNone(runtime.owner_profile_id)

    def test_locked_image_reports_incomplete_and_can_retry(self):
        original = Path.unlink

        def locked(path, *args, **kwargs):
            if path == self.photos[2]:
                raise PermissionError("mock image lock")
            return original(path, *args, **kwargs)

        with patch.object(Path, "unlink", locked):
            result = self.call()
        self.assertFalse(result["cleanup_complete"])
        self.assertTrue(self.photos[2].exists())
        self.assertTrue(cleanup_recordings(self.root, 2)["cleanup_complete"])
        self.assertTrue(self.photos[1].exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
