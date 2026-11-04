"""API wiring and validation are preserved when route implementation moves."""

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://check:unused@127.0.0.1:1/check")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pydantic import ValidationError

from app.api.schemas import CaptureConfig
from app.main import create_app
from app.paths import BACKEND_ROOT


class APIContractChecks(unittest.TestCase):
    def test_existing_public_urls_are_registered_once(self):
        paths = create_app().openapi()["paths"]
        expected = {
            "/api/health": {"get"},
            "/api/catalog": {"get"},
            "/api/metrics": {"get"},
            "/api/exercises/{eid}/criteria": {"post"},
            "/api/exercises/{eid}/criteria-template": {"get"},
            "/api/readiness": {"post"},
            "/api/sessions": {"get", "post"},
            "/api/sessions/{sid}/attempts": {"post"},
            "/api/attempts/{aid}/finish": {"post"},
            "/api/sessions/{sid}/finish": {"post"},
            "/api/sessions/{sid}": {"get"},
            "/api/sessions/{sid}/delete": {"post"},
            "/api/sessions/{sid}/evidence.zip": {"get"},
            "/api/attempts/{aid}/clip.webm": {"get"},
            "/api/sessions/{sid}/export": {"get"},
            "/api/compare": {"get"},
            "/api/status": {"get"},
            "/api/clock": {"get"},
            "/api/progress": {"get"},
            "/api/cameras/preview": {"post"},
            "/api/cameras/stop": {"post"},
            "/api/calibration": {"post"},
            "/api/training/reset-summary": {"get"},
            "/api/training/reset": {"post"},
        }
        for url, methods in expected.items():
            self.assertEqual(set(paths[url]), methods, url)
        operations = [v["operationId"] for p in paths.values() for v in p.values()]
        self.assertEqual(len(operations), len(set(operations)))
        self.assertIn("/api/auth/login", paths)
        self.assertIn("/api/auth/register", paths)

    def test_capture_contract_and_model_root_remain_stable(self):
        self.assertEqual(CaptureConfig().mode, "LIVE")
        with self.assertRaises(ValidationError):
            CaptureConfig(mode="DEMO")
        self.assertEqual(BACKEND_ROOT, Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
