"""Assemble a full session report only when its detail is requested."""

from sqlalchemy import select

from ..database import (
    METRICS,
    Attempt,
    Criteria,
    Exercise,
    Measurement,
    MetricDefinition,
)
from ..lessons import feedback
from ..metrics import stats
from ..protocol import protocol_result


def detail(db, s):
    c = db.get(Criteria, s.criteria_id)
    e = db.get(Exercise, c.exercise_id)
    attempts = []
    counts = {key: 0 for key in ["PASS", "FAIL", "INVALID", "ABORTED", "IN_PROGRESS"]}
    for a in db.scalars(
        select(Attempt).where(Attempt.session_id == s.id).order_by(Attempt.attempt_number)
    ):
        counts[a.result_status] += 1
        measurements = {}
        for m in db.scalars(select(Measurement).where(Measurement.attempt_id == a.id)):
            d = db.get(MetricDefinition, m.metric_id)
            measurements[d.code] = {
                "value": m.value,
                "unit": d.unit,
                "status": m.validity_status,
                "reason": m.invalid_reason,
            }
        attempts.append(
            {
                "id": a.id,
                "number": a.attempt_number,
                "status": a.result_status,
                "reason": a.result_reason,
                "metrics": measurements,
                "quality": a.evidence.get("quality", {}),
                "videos": a.evidence.get("videos", {}),
                "display_timing": a.evidence.get("display_timing"),
                "feedback": feedback(
                    {k: v["value"] for k, v in measurements.items()}, c.definition.get("rules")
                ),
            }
        )
    total = counts["PASS"] + counts["FAIL"]
    summary = {
        code: stats(
            [a["metrics"].get(code, {}).get("value") for a in attempts if a["status"] != "ABORTED"]
        )
        for code in METRICS
    }
    return {
        "id": s.id,
        "name": e.name,
        "exercise_id": e.id,
        "criteria_id": s.criteria_id,
        "criteria": c.definition,
        "config": s.configuration_snapshot,
        "started_at": s.started_at,
        "ended_at": s.ended_at,
        "status": s.status,
        "counts": counts,
        "pass_rate": counts["PASS"] / total if total else None,
        "attempts": attempts,
        "summary": summary,
        "mode": s.configuration_snapshot["mode"],
        "protocol_result": protocol_result(
            counts, c.definition, s.configuration_snapshot, s.status
        ),
    }
