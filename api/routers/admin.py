"""
MOD-05 — Admin router (dev / testing)
Endpoints for DB management during development.
"""

import logging

from fastapi import APIRouter

import database as db
import state

logger = logging.getLogger("mod05.admin")
router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset-db")
async def reset_db():
    """Truncate all data tables and reset in-memory caches.
    Used by simulate.py to get a clean slate on every run.
    Does NOT drop tables — only deletes rows.
    """
    await db.truncate_all_tables()
    state.reset_state()
    logger.info("[Admin] Database truncated and state cache reset")
    return {"status": "ok", "message": "Database cleared"}


@router.post("/cleanup")
async def cleanup():
    """Delete sensor readings older than 2 hours.
    Called periodically by simulate.py to prevent unbounded growth.
    """
    rows_deleted = await db.cleanup_old_readings(max_age_hours=2)
    logger.info(f"[Admin] Cleaned up {rows_deleted} old sensor readings")
    return {"status": "ok", "rows_deleted": rows_deleted}
