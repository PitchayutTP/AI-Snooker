"""Shared ownership checks and serialization for the single training device."""

import threading
from functools import wraps

from fastapi import (
    HTTPException,
    Request,
)

from ..database import (
    TrainingSession,
)
from ..runtime import runtime

operation_lock = threading.RLock()


def current_user(request: Request):
    return request.state.user


def require(db, model, key):
    item = db.get(model, key)
    if not item:
        raise HTTPException(404, "ไม่พบข้อมูล")
    return item


def owned_session(db, sid, user):
    session = require(db, TrainingSession, sid)
    if session.profile_id != user["profile_id"]:
        raise HTTPException(404, "ไม่พบข้อมูล")
    return session


def private_snapshot(user):
    with runtime.lock:
        if runtime.owner_profile_id != user["profile_id"]:
            return {
                "ready": False,
                "frame": {},
                "session_id": None,
                "attempt_id": None,
                "samples": 0,
                "collecting": False,
                "busy": bool(runtime.session_id),
            }
        return runtime.snapshot()


def serialized(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        with operation_lock:
            return fn(*args, **kwargs)

    return call
