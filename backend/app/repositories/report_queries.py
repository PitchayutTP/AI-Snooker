"""List/progress queries never load frame evidence or per-attempt measurements."""

from collections import defaultdict

from sqlalchemy import func, select

from ..completion import latest_assessment
from ..database import Attempt, Criteria, Exercise, Module, TrainingSession
from ..protocol import protocol_result


def exercise_catalog(db, lessons):
    criteria = defaultdict(list)
    for item in db.scalars(
        select(Criteria)
        .join(Exercise, Exercise.id == Criteria.exercise_id)
        .where(Exercise.module_id <= 3)
        .order_by(Criteria.version_no.desc())
    ):
        criteria[item.exercise_id].append(
            {"id": item.id, "version": item.version_no, **item.definition}
        )
    return [
        {
            "id": exercise.id,
            "module_id": exercise.module_id,
            "module": module.name,
            "name": exercise.name,
            "instructions": exercise.instructions,
            "setup": exercise.setup_definition,
            "lesson": lessons.get(exercise.module_id, {}),
            "criteria": criteria[exercise.id],
        }
        for exercise, module in db.execute(
            select(Exercise, Module)
            .join(Module, Module.id == Exercise.module_id)
            .where(Exercise.module_id <= 3)
            .order_by(Exercise.id)
        )
    ]


def compact_sessions(db, profile_id):
    query = (
        select(
            TrainingSession.id,
            Exercise.name,
            Exercise.id.label("exercise_id"),
            TrainingSession.criteria_id,
            TrainingSession.started_at,
            TrainingSession.ended_at,
            TrainingSession.status,
            TrainingSession.configuration_snapshot["mode"].as_string().label("mode"),
        )
        .join(Criteria, Criteria.id == TrainingSession.criteria_id)
        .join(Exercise, Exercise.id == Criteria.exercise_id)
        .where(TrainingSession.profile_id == profile_id)
        .order_by(TrainingSession.started_at.desc())
        .limit(100)
    )
    return [dict(row) for row in db.execute(query).mappings()]


def practice_progress(db, profile_id):
    exercises = list(
        db.scalars(select(Exercise).where(Exercise.module_id <= 3).order_by(Exercise.id))
    )
    # One metadata query and one grouped count query, independent of frame volume.
    completed = db.execute(
        select(TrainingSession, Criteria)
        .join(Criteria, Criteria.id == TrainingSession.criteria_id)
        .where(TrainingSession.profile_id == profile_id, TrainingSession.status == "COMPLETED")
    ).all()
    counts = defaultdict(
        lambda: {key: 0 for key in ("PASS", "FAIL", "INVALID", "ABORTED", "IN_PROGRESS")}
    )
    grouped = db.execute(
        select(Attempt.session_id, Attempt.result_status, func.count(Attempt.id))
        .join(TrainingSession, TrainingSession.id == Attempt.session_id)
        .where(TrainingSession.profile_id == profile_id, TrainingSession.status == "COMPLETED")
        .group_by(Attempt.session_id, Attempt.result_status)
    )
    for sid, status, count in grouped:
        counts[sid][status] = count
    by_exercise = defaultdict(list)
    for session, criteria in completed:
        config = session.configuration_snapshot
        count = counts[session.id]
        by_exercise[criteria.exercise_id].append(
            {
                "id": session.id,
                "exercise_id": criteria.exercise_id,
                "status": session.status,
                "started_at": session.started_at,
                "mode": config["mode"],
                "config": config,
                "criteria": criteria.definition,
                "counts": count,
                "attempts": sum(count.values()),
                "protocol_result": protocol_result(
                    count, criteria.definition, config, session.status
                ),
            }
        )
    output = []
    for exercise in exercises:
        rows = by_exercise[exercise.id]
        output.append(
            {
                "exercise_id": exercise.id,
                "module_id": exercise.module_id,
                "sessions": len(rows),
                **latest_assessment(rows),
                "attempts": sum(row["attempts"] for row in rows),
                "live_pass": sum(row["counts"]["PASS"] for row in rows if row["mode"] == "LIVE"),
                "assessments_completed": sum(
                    row["protocol_result"]["purpose"] == "ASSESSMENT" for row in rows
                ),
                "assessments_passed": sum(
                    row["protocol_result"]["status"] == "PASS" for row in rows
                ),
                "demo_sessions": sum(row["mode"] == "DEMO" for row in rows),
            }
        )
    return output
