"""Read-path checks in a disposable in-memory database, never the user's PostgreSQL."""

import os
import sys
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://check:unused@127.0.0.1:1/check")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import auth
from app.completion import latest_assessment
from app.criteria_templates import training_template
from app.database import (
    Attempt,
    Base,
    Criteria,
    Exercise,
    Measurement,
    MetricDefinition,
    Module,
    Profile,
    TrainingSession,
)
from app.lessons import LESSONS
from app.repositories.report_queries import compact_sessions, exercise_catalog, practice_progress
from app.services.reporting import detail


class LoadingChecks(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all([Profile(id=i, display_name=f"P{i}") for i in (1, 2)])
        self.db.add(Module(id=2, name="M2"))
        self.db.add(
            Exercise(id=2, module_id=2, name="Delivery", instructions="test", setup_definition={})
        )
        self.db.add(
            Criteria(
                id=1,
                exercise_id=2,
                version_no=1,
                definition={**training_template(2), "approved": True},
            )
        )
        self.db.add(MetricDefinition(id=1, code="m2_gate_clear", unit="boolean", definition="test"))
        self.db.flush()
        cases = [
            ("old", 1, "COMPLETED", "LIVE", "ASSESSMENT", ["PASS", "INVALID"]),
            ("latest", 1, "COMPLETED", "LIVE", "ASSESSMENT", ["FAIL"]),
            ("pilot", 1, "COMPLETED", "LIVE", "PILOT", ["PASS"]),
            ("demo", 1, "COMPLETED", "DEMO", "ASSESSMENT", ["PASS"]),
            ("active", 1, "IN_PROGRESS", "LIVE", "ASSESSMENT", ["IN_PROGRESS"]),
            ("aborted", 1, "ABORTED", "LIVE", "ASSESSMENT", ["ABORTED"]),
            ("other-owner", 2, "COMPLETED", "LIVE", "ASSESSMENT", ["PASS"]),
        ]
        for index, (sid, owner, status, mode, purpose, outcomes) in enumerate(cases):
            self.db.add(
                TrainingSession(
                    id=sid,
                    profile_id=owner,
                    criteria_id=1,
                    status=status,
                    started_at=f"2026-01-0{index + 1}",
                    configuration_snapshot={"mode": mode, "purpose": purpose},
                )
            )
            for n, outcome in enumerate(outcomes, 1):
                aid = f"{sid}-{n}"
                self.db.add(
                    Attempt(
                        id=aid,
                        session_id=sid,
                        attempt_number=n,
                        result_status=outcome,
                        evidence={"samples": [{"padding": "x" * 1000}] * 100, "quality": {}},
                    )
                )
                self.db.add(
                    Measurement(attempt_id=aid, metric_id=1, value=1.0, validity_status="VALID")
                )
        self.db.commit()
        self.db.expunge_all()
        self.sql = []
        event.listen(
            self.engine,
            "before_cursor_execute",
            lambda c, u, statement, *args: self.sql.append(statement),
        )

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_progress_matches_previous_full_detail_without_reading_evidence(self):
        rows = [detail(self.db, s) for s in self.db.query(TrainingSession).filter_by(profile_id=1)]
        completed = [
            row for row in rows if row["exercise_id"] == 2 and row["status"] == "COMPLETED"
        ]
        expected = {
            "exercise_id": 2,
            "module_id": 2,
            "sessions": len(completed),
            **latest_assessment(completed),
            "attempts": sum(len(row["attempts"]) for row in completed),
            "live_pass": sum(row["counts"]["PASS"] for row in completed if row["mode"] == "LIVE"),
            "assessments_completed": sum(
                row["protocol_result"]["purpose"] == "ASSESSMENT" for row in completed
            ),
            "assessments_passed": sum(
                row["protocol_result"]["status"] == "PASS" for row in completed
            ),
            "demo_sessions": sum(row["mode"] == "DEMO" for row in completed),
        }
        previous_queries = len(self.sql)
        self.sql.clear()
        self.db.expunge_all()
        self.assertEqual(practice_progress(self.db, 1), [expected])
        self.assertEqual(len(self.sql), 3)
        self.assertFalse(any("evidence" in query or "measurements" in query for query in self.sql))
        print(f"Progress SQL calls: previous={previous_queries}, current={len(self.sql)}")

    def test_compact_history_is_private_single_query_and_detail_still_exists(self):
        rows = compact_sessions(self.db, 1)
        self.assertEqual(len(self.sql), 1)
        self.assertEqual(len(rows), 6)
        self.assertNotIn("other-owner", [row["id"] for row in rows])
        self.assertEqual(rows[0]["id"], "aborted")
        self.assertFalse(any("evidence" in query or "measurements" in query for query in self.sql))
        self.assertNotIn("attempts", rows[0])
        report = detail(self.db, self.db.get(TrainingSession, "old"))
        self.assertEqual(len(report["attempts"]), 2)
        self.assertIn("m2_gate_clear", report["attempts"][0]["metrics"])

    def test_catalog_uses_two_queries(self):
        rows = exercise_catalog(self.db, LESSONS)
        self.assertEqual(len(self.sql), 2)
        self.assertEqual(rows[0]["criteria"][0]["id"], 1)
        self.assertEqual(rows[0]["module"], "M2")

    def test_auth_single_query_keeps_expiry_and_invalid_token_checks(self):
        self.db.add(auth.Account(id=1, username="test", password_hash="unused", profile_id=1))
        self.db.add_all(
            [
                auth.AuthSession(
                    token_hash=auth.token_digest("valid"),
                    account_id=1,
                    expires_at=int(time.time()) + 60,
                ),
                auth.AuthSession(
                    token_hash=auth.token_digest("expired"),
                    account_id=1,
                    expires_at=int(time.time()) - 60,
                ),
            ]
        )
        self.db.commit()
        self.sql.clear()

        @contextmanager
        def connection():
            yield self.db

        with patch.object(auth, "DB", connection):
            self.assertEqual(auth.identity("valid")["profile_id"], 1)
            self.assertEqual(len(self.sql), 1)
            self.assertIsNone(auth.identity("expired"))
            self.assertIsNone(auth.identity("unknown"))
            self.assertIsNone(auth.identity(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
