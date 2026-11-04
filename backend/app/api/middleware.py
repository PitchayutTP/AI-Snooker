"""HTTP authentication and response-cache policy."""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from ..auth import COOKIE, ORIGINS, identity


async def authentication(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if (origin and origin not in ORIGINS) or request.headers.get(
                "sec-fetch-site"
            ) == "cross-site":
                return JSONResponse({"detail": "ไม่อนุญาตคำขอจากเว็บไซต์อื่น"}, status_code=403)
        request.state.user = await run_in_threadpool(identity, request.cookies.get(COOKIE))
        public = {"/api/health", "/api/auth/login", "/api/auth/register", "/api/auth/logout"}
        if (
            request.method != "OPTIONS"
            and request.url.path not in public
            and not request.state.user
        ):
            return JSONResponse({"detail": "กรุณาเข้าสู่ระบบ"}, status_code=401)
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response
