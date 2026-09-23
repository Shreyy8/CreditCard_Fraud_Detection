"""FastAPI application entrypoint."""

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.cases import router as cases_router
from .api.health import router as health_router
from .api.investigations import router as investigations_router
from .api.policy import router as policy_router
from .config import get_settings

settings = get_settings()

# ── Structured logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "msg": %(message)s}',
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TigerGraph Fraud Investigation API",
    description="AI-powered fraud investigation agent — TigerGraph × Hacker House Goa",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(cases_router)
app.include_router(investigations_router)
app.include_router(policy_router)


@app.on_event("startup")
async def startup_event():
    logger.info('"Fraud Investigation API starting up"')
    # Pre-load data layer (runs in background — don't block startup)
    try:
        from .data_layer import get_data_layer
        dl = get_data_layer()
        logger.info('"Data layer loaded: %d transactions, %d cases"',
                    len(dl.transactions), len(dl.closed_cases))
    except Exception as exc:
        logger.warning('"Data layer preload failed: %s"', exc)


@app.on_event("shutdown")
async def shutdown_event():
    try:
        from .tigergraph.client import get_client
        await get_client().close()
    except Exception:
        pass
