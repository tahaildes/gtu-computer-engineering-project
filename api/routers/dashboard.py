"""
MOD-05 — Dashboard router
Serves data to the React frontend via REST.
Uses in-memory cache for /twin and /report, SQLite for history endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

import database as db
import state
import pi_client

logger = logging.getLogger("mod05.dashboard")
router = APIRouter(tags=["dashboard"])


@router.get("/twin")
async def get_twin():
    """Current factory state snapshot. Called on initial page load."""
    return state.twin_cache.model_dump()


@router.get("/report")
async def get_report():
    """Latest LLM maintenance report."""
    if state.report_cache is None:
        raise HTTPException(status_code=404, detail="No report available yet")
    return state.report_cache.model_dump()


@router.get("/history")
async def get_history(limit: int = Query(default=50, ge=1, le=500)):
    """Sensor reading history from SQLite. Seeds sparkline charts."""
    return await db.get_sensor_history(limit=limit)


@router.get("/reports")
async def get_reports(limit: int = Query(default=10, ge=1, le=100)):
    """LLM report history from SQLite. For the report stream panel."""
    return await db.get_report_history(limit=limit)


@router.get("/health")
async def get_health():
    """System health check. Dashboard uses this for connectivity status."""
    pi_reachable = await pi_client.check_reachable()
    pending_cmds = await db.count_pending_commands()
    db_size = await db.get_db_size_bytes()

    return {
        "status": "ok",
        "pi_reachable": pi_reachable,
        "last_ingest_ms": state.last_ingest_ms,
        "pending_cmds": pending_cmds,
        "db_size_bytes": db_size,
        "websocket_clients": len(state.ws_clients),
    }
