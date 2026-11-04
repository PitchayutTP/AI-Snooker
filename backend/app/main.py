"""ASGI composition root. Start with: uvicorn app.main:app."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import cameras, catalog, reports, system, training
from .api.middleware import authentication
from .auth import router as auth_router
from .lifecycle import lifespan


def create_app() -> FastAPI:
    app = FastAPI(title="Snooker Practice", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=True,
    )
    app.middleware("http")(authentication)
    app.include_router(auth_router)
    for router in (catalog.router, cameras.router, training.router, reports.router, system.router):
        app.include_router(router)
    return app


app = create_app()
