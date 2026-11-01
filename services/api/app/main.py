"""DRISHTI Ganjam API — FastAPI app. Run: uvicorn app.main:app --reload"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import areas, errors, health, risk, sim, ws
from app.config import get_settings
from app.sim.state import sim_clock
from app.ws.hub import hub

API_PREFIX = "/api/v1"
logging.basicConfig(
    level=logging.INFO, format='{"level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    await hub.start(settings.redis_url)
    if settings.is_demo:
        sim_clock.restore()
        sim_clock.start()
    yield
    await sim_clock.stop()
    await hub.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="DRISHTI Ganjam API",
        version="0.1.0",
        description="AI-based hyperlocal disaster intelligence for Ganjam district, Odisha "
        "(OSFIC 2026 PS-074).",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    errors.install(app)
    app.include_router(health.router)
    for r in (areas.router, risk.router, sim.router, ws.router):
        app.include_router(r, prefix=API_PREFIX)
    return app


app = create_app()
