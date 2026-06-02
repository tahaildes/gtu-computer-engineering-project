"""
MOD-05 — Decision router
Pi (MOD-03/04) sends actuator commands and LLM reports here.
"""

import json
import uuid
import logging

from fastapi import APIRouter

from models import ActuatorCmd, MaintenanceReport
import database as db
import state

logger = logging.getLogger("mod05.decision")
router = APIRouter(prefix="/decision", tags=["decision"])


@router.post("/actuator")
async def decision_actuator(cmd: ActuatorCmd):
    """Pi sends an actuator command. Server queues it for the target ESP32."""
    # 1. Assign a unique command ID
    cmd_id = str(uuid.uuid4())
    cmd.cmd_id = cmd_id

    # 2. Write to pending_commands table
    payload_json = cmd.model_dump_json()
    await db.insert_pending_command(
        cmd_id=cmd_id,
        zone_id=cmd.zone_id.value,
        payload_json=payload_json,
    )

    # 3. Broadcast command issued event to dashboard
    await state.broadcast({
        "type": "ack",
        "cmd_id": cmd_id,
        "status": "QUEUED",
    })

    logger.info(f"[Decision] Actuator cmd queued: {cmd_id} → {cmd.zone_id.value}")
    return {"status": "ok", "cmd_id": cmd_id}


@router.post("/report")
async def decision_report(report: MaintenanceReport):
    """Pi sends an LLM maintenance report after MOD-04 analysis."""
    # 1. Write to DB
    report_json = report.model_dump_json()
    await db.insert_report(report_json, created_at=report.timestamp_ms)

    # 2. Update in-memory cache
    state.set_report(report)

    # 3. Immediately broadcast to WS clients
    await state.broadcast({
        "type": "report",
        "report": report.model_dump(),
    })

    logger.info(f"[Decision] LLM report received: risk={report.risk_level.value}")
    return {"status": "ok"}
