"""Comparable round signatures for reporting completion, not skill certification."""

import hashlib
import json


def completion_signature(report):
    config = {
        key: value
        for key, value in report["config"].items()
        if key not in ("exercise_id", "purpose", "setup_notes")
    }
    definition = report["criteria"]
    criteria = {
        key: definition.get(key)
        for key in (
            "rules",
            "protocol",
            "minimum_active_seconds",
            "validation_scope",
            "template_version",
        )
    }
    return hashlib.sha256(
        json.dumps(
            {"config": config, "criteria": criteria}, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def latest_assessment(sessions):
    eligible = [
        row
        for row in sessions
        if row["status"] == "COMPLETED"
        and row["mode"] == "LIVE"
        and row["protocol_result"]["purpose"] == "ASSESSMENT"
    ]
    if not eligible:
        return {}
    latest = max(eligible, key=lambda row: row["started_at"])
    return {
        "latest_assessment_status": latest["protocol_result"]["status"],
        "latest_assessment_scope": latest["criteria"].get("validation_scope", "REPORT"),
        "completion_signature": completion_signature(latest),
    }
