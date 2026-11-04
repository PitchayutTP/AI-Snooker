"""Single-session deletion checks with mocked DB and generated evidence only."""

import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://check:unused@127.0.0.1:1/check"
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.api import reports as main
from app.runtime import Runtime
from app.training_reset import recording_cleanup_plan


class DeleteChecks(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).resolve().parents[2]
        self.temp = tempfile.TemporaryDirectory(dir=self.workspace / "data")
        self.root = Path(self.temp.name) / "recordings"
        self.sid = uuid4()
        self.other_sid = uuid4()
        self.files = []
        for profile, sid in ((1, self.sid), (1, self.other_sid), (2, self.sid)):
            for name in ("top.webm", "attempt/top/000001.jpg"):
                file = self.root / str(profile) / str(sid) / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(b"generated evidence")
                self.files.append(file)
        self.session = SimpleNamespace(id=str(self.sid), profile_id=1, status="COMPLETED")
        self.db = MagicMock()
        self.db.get.return_value = self.session
        self.db.execute.side_effect = [SimpleNamespace(rowcount=n) for n in (3, 2, 1)]
        self.database = MagicMock()
        self.database.begin.return_value.__enter__.return_value = self.db

    def tearDown(self):
        assert Path(self.temp.name).resolve().is_relative_to((self.workspace / "data").resolve())
        self.temp.cleanup()

    def call(self, runtime=None):
        with (
            patch.object(main, "DB", self.database),
            patch.object(main, "runtime", runtime or Runtime()),
            patch.object(main, "RECORDINGS", self.root),
        ):
            return main.delete_training_session(
                self.sid,
                main.DeleteSessionRequest(confirmation="DELETE_SESSION"),
                user={"profile_id": 1},
            )

    def test_only_selected_session_and_its_files_are_deleted(self):
        result = self.call()
        self.assertEqual(result["sessions_removed"], 1)
        self.assertEqual(result["images_removed"], 2)
        self.assertTrue(result["cleanup_complete"])
        for file in self.files:
            expected = not file.is_relative_to(self.root / "1" / str(self.sid))
            self.assertEqual(file.exists(), expected)
        for call in self.db.execute.call_args_list:
            sql = str(
                call.args[0].compile(
                    dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
                )
            )
            self.assertIn(str(self.sid), sql)
            self.assertIn("training_sessions.profile_id = 1", sql)

    def test_other_profile_cannot_delete_session(self):
        self.session.profile_id = 2
        with self.assertRaises(HTTPException) as error:
            self.call()
        self.assertEqual(error.exception.status_code, 404)
        self.db.execute.assert_not_called()
        self.assertTrue(all(file.exists() for file in self.files))

    def test_active_session_is_blocked(self):
        self.session.status = "IN_PROGRESS"
        with self.assertRaises(HTTPException) as error:
            self.call()
        self.assertEqual(error.exception.status_code, 409)
        self.db.execute.assert_not_called()

    def test_database_failure_preserves_files(self):
        self.db.execute.side_effect = RuntimeError("transaction failed")
        with self.assertRaises(RuntimeError):
            self.call()
        self.assertTrue(all(file.exists() for file in self.files))

    def test_locked_video_cleanup_can_retry_after_row_was_deleted(self):
        video = self.root / "1" / str(self.sid) / "top.webm"
        unlink = Path.unlink

        def locked(path, *args, **kwargs):
            if path == video:
                raise PermissionError("video open")
            return unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", locked):
            result = self.call()
        self.assertFalse(result["cleanup_complete"])
        self.assertTrue(video.exists())
        self.db.get.return_value = None
        result = self.call()
        self.assertEqual(result["sessions_removed"], 0)
        self.assertTrue(result["cleanup_complete"])
        self.assertFalse(video.exists())
        self.assertTrue((self.root / "1" / str(self.other_sid) / "top.webm").exists())

    def test_confirmation_and_bounded_session_path(self):
        with self.assertRaises(ValidationError):
            main.DeleteSessionRequest.model_validate({})
        with self.assertRaises(ValueError):
            recording_cleanup_plan(self.root, 1, "../../2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
