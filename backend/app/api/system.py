"""System API routes; public URLs remain unchanged."""

import asyncio

from fastapi import (
    APIRouter,
    Depends,
    WebSocket,
    WebSocketDisconnect,
)
from starlette.concurrency import run_in_threadpool

from ..auth import COOKIE, ORIGINS, identity
from .dependencies import (
    current_user,
    private_snapshot,
)

router = APIRouter()


@router.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "0.4.0",
        "scope": "M1-M3 table trial; local accounts, one training device",
    }


@router.get("/api/status")
def status(user=Depends(current_user)):
    return private_snapshot(user)


@router.get("/api/clock")
def server_clock():
    import time

    return {"epoch_ms": time.time() * 1000}


@router.websocket("/ws")
async def websocket(ws: WebSocket):
    origin = ws.headers.get("origin")
    token = ws.cookies.get(COOKIE)
    if origin not in ORIGINS or not await run_in_threadpool(identity, token):
        await ws.close(code=1008)
        return
    await ws.accept()
    try:
        while True:
            user = await run_in_threadpool(identity, token)
            if not user:
                await ws.close(code=1008)
                return
            await ws.send_json(await run_in_threadpool(private_snapshot, user))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
