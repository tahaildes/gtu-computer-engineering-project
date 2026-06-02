"""
MOD-05 — Control router
Dashboard operator manual overrides — actuator commands & machine control.
"""

import asyncio
import uuid
import logging

from fastapi import APIRouter

from models import ManualActuatorCmd, MachineCmd, CommandSource
import database as db
import state
import pi_client

logger = logging.getLogger("mod05.control")
router = APIRouter(tags=["control"])


@router.post("/actuator/cmd")
async def manual_actuator_cmd(cmd: ManualActuatorCmd):
    """Operator manually controls a device from the dashboard.
    Goes into the same command queue as Pi decisions, tagged as MANUAL.
    """
    cmd_id = str(uuid.uuid4())

    # Build the full actuator command payload
    payload = {
        "zone_id":     cmd.zone_id.value,
        "device_type": cmd.device_type.value,
        "value_pct":   cmd.value_pct,
        "relay_state": cmd.relay_state,
        "source":      CommandSource.MANUAL.value,
        "cmd_id":      cmd_id,
    }

    import json
    await db.insert_pending_command(
        cmd_id=cmd_id,
        zone_id=cmd.zone_id.value,
        payload_json=json.dumps(payload),
    )

    # Broadcast to WS so operator sees the command was issued
    await state.broadcast({
        "type": "ack",
        "cmd_id": cmd_id,
        "status": "QUEUED",
    })

    logger.info(f"[Control] Manual actuator cmd: {cmd_id} → {cmd.zone_id.value}")
    return {"status": "ok", "cmd_id": cmd_id}


@router.post("/machine/control")
async def machine_control(cmd: MachineCmd):
    """Operator sends a control command to MOD-02 (reset or force state).
    Server forwards to Pi which relays to ESP32 #3 via MQTT.
    """
    payload = cmd.model_dump()

    # Forward to Pi (fire-and-forget)
    asyncio.create_task(_safe_forward(payload))

    logger.info(f"[Control] Machine control: cmd={cmd.cmd} state={cmd.state}")
    return {"status": "ok"}


async def _safe_forward(payload: dict) -> None:
    try:
        await pi_client.forward_machine_control(payload)
    except Exception as e:
        logger.error(f"[Control] Pi forward error: {e}")
