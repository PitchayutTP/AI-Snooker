"""Finish-attempt persistence contract using mocked PostgreSQL sessions, no real DB."""

import json
import os
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

os.environ["DATABASE_URL"] = "postgresql+psycopg://check:unused@127.0.0.1:1/check"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_m3 as fixtures

from app.api import training as main
from app.api.schemas import CriteriaRequest
from app.criteria_templates import training_template


class StorageChecks(unittest.TestCase):
    def test_current_m3_templates_pass_api_request_validation(self):
        from pydantic import ValidationError

        for fraction in (1.0, 0.75, 0.5, 0.25):
            template = {**training_template(3, fraction), "approved": True}
            request = CriteriaRequest.model_validate(template)
            self.assertEqual(request.minimum_active_seconds, 0.0)
            with self.assertRaises(ValidationError):
                CriteriaRequest.model_validate({**template, "minimum_active_seconds": -1})

    def finish(self, rows, aborted=False, videos=None):
        attempt = SimpleNamespace(id="a", session_id="s", result_status="IN_PROGRESS")
        session = SimpleNamespace(
            id="s",
            profile_id=1,
            criteria_id=1,
            configuration_snapshot={
                **fixtures.config(),
                "mode": "LIVE",
                "record_frames": videos is not None,
            },
        )
        criteria = SimpleNamespace(
            id=1, exercise_id=3, definition={**training_template(3, 0.5), "approved": True}
        )
        exercise = SimpleNamespace(id=3, module_id=3, setup_definition={"fraction": 0.5})
        entities = {
            (main.Attempt, "a"): attempt,
            (main.TrainingSession, "s"): session,
            (main.Criteria, 1): criteria,
            (main.Exercise, 3): exercise,
        }
        db = MagicMock()
        db.get.side_effect = lambda model, key: entities.get((model, key))
        db.scalars.return_value = [
            SimpleNamespace(id=1, code="contact_fraction"),
            SimpleNamespace(id=2, code="fraction_error"),
        ]
        factory = MagicMock()
        factory.begin.return_value.__enter__.return_value = db
        runtime = SimpleNamespace(
            lock=threading.RLock(),
            attempt_id="a",
            samples=rows,
            collecting=True,
            error=None,
            finish_recording=Mock(return_value=videos or {}),
            recording_error=None,
        )
        with patch.object(main, "DB", factory), patch.object(main, "runtime", runtime):
            result = main.finish_attempt(
                "a", main.FinishRequest(aborted=aborted), user={"profile_id": 1}
            )
        records = [call.args[0] for call in db.add.call_args_list]
        self.assertEqual(len(records), 2)
        json.dumps(attempt.evidence, allow_nan=False)
        self.assertIsNone(runtime.attempt_id)
        self.assertEqual(runtime.samples, [])
        return result, attempt, records

    def test_supported_contact_persists_values_and_evidence(self):
        result, attempt, records = self.finish(fixtures.M3Checks().sequence(0.5))
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(r.validity_status == "VALID" for r in records))
        self.assertEqual(attempt.evidence["quality"]["m3_events"][0]["type"], "CONTACT_CANDIDATE")
        self.assertAlmostEqual(records[0].value, 0.5, delta=0.06)

    def test_finished_video_is_linked_to_the_attempt(self):
        videos = {
            "top": {"path": "data/recordings/1/session/attempt/top.webm", "captured_frames": 18}
        }
        result, attempt, _ = self.finish(fixtures.M3Checks().sequence(0.5), videos=videos)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(attempt.evidence["videos"], videos)
        self.assertEqual(attempt.evidence["quality"]["recorded_frames"], 18)

    def test_missing_contact_persists_invalid_without_fake_zero(self):
        rows = fixtures.M3Checks().sequence(0.5)
        rows[16]["balls"] = []
        result, _, records = self.finish(rows)
        self.assertEqual(result["status"], "INVALID")
        self.assertIn("จุดตรวจจับ", result["reason"])
        self.assertTrue(all(r.value is None and r.validity_status == "INVALID" for r in records))

    def test_aborted_attempt_is_not_pass(self):
        self.assertEqual(
            self.finish(fixtures.M3Checks().sequence(0.5), True)[0]["status"], "ABORTED"
        )

    def test_confirmed_contact_survives_tail_gap_without_inflating_duration(self):
        rows = fixtures.M3Checks().sequence(0.5)[:19]
        rows.append({"t": 10.0, "balls": []})
        result, attempt, _ = self.finish(rows)
        self.assertEqual(result["status"], "PASS")
        self.assertLess(attempt.evidence["events"][0]["valid_active_seconds"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
