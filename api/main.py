"""
MOD-05 — Dark Factory API  ·  Main Application
Central hub between ESP32 sensor nodes, Raspberry Pi (MOD-03/04),
and the React dashboard frontend.

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database as db
import pi_client

from routers import ingest, decision, commands, dashboard, control, websocket, admin

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-22s  %(levelname)-5s  %(message)s",
)
logger = logging.getLogger("mod05")


# ── Lifespan (startup / shutdown) ────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await db.init_db()
    logger.info("Database ready  ✓")
    logger.info("Dark Factory API (MOD-05) is running")
    yield
    # Shutdown
    logger.info("Shutting down...")
    await pi_client.close_client()
    await db.close_db()
    logger.info("Cleanup complete  ✓")


# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="Dark Factory API — MOD-05",
    description="Central IIoT hub for the GTU CSE 396 Dark Factory project",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (allow all origins for development) ─────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ─────────────────────────────────────────

app.include_router(ingest.router)
app.include_router(decision.router)
app.include_router(commands.router)
app.include_router(dashboard.router)
app.include_router(control.router)
app.include_router(websocket.router)
app.include_router(admin.router)


# ── Root endpoint ────────────────────────────────────────────

@app.get("/", tags=["root"])
async def root():
    return {
        "service": "Dark Factory API — MOD-05",
        "version": "1.0.0",
        "docs": "/docs",
    }
