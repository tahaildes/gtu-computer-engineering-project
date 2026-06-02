"""
MOD-05 — Commands router
ESP32s poll for pending commands and send acknowledgements.
"""

import logging

from fastapi import APIRouter

from models import ZoneId, CmdAck
import database as db
import state

logger = logging.getLogger("mod05.commands")
router = APIRouter(prefix="/cmd", tags=["commands"])


@router.get("/{zone_id}")
async def get_pending_command(zone_id: ZoneId):
    """ESP32 polls for the oldest un-acked command for its zone."""
    result = await db.get_oldest_pending_command(zone_id.value)

    if result is None:
        return {"has_cmd": False}

    return {
        "has_cmd": True,
        "cmd": result["payload"],
    }


@router.post("/{zone_id}/ack")
async def ack_command(zone_id: ZoneId, ack: CmdAck):
    """ESP32 confirms it received and executed a command."""
    # 1. Remove from pending_commands
    found = await db.ack_command(ack.cmd_id)

    if not found:
        logger.warning(f"[Cmd] Ack for unknown cmd_id: {ack.cmd_id}")

    # 2. Broadcast ack event to dashboard
    await state.broadcast({
        "type": "ack",
        "cmd_id": ack.cmd_id,
        "status": ack.status,
    })

    logger.info(f"[Cmd] Acked: {ack.cmd_id} zone={zone_id.value} status={ack.status}")
    return {"status": "ok"}
