"""
MOD-05 — WebSocket router
Browser connects here for live updates.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import state

logger = logging.getLogger("mod05.websocket")
router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Live data stream for the React dashboard.
    Server pushes snapshot, alarm, report, and ack events.
    Client can send keep-alive pings; they are simply consumed.
    """
    await state.ws_connect(websocket)
    try:
        # Send initial state on connect
        initial = {
            "type": "snapshot",
            "snapshot": state.twin_cache.model_dump(),
            "report": state.report_cache.model_dump() if state.report_cache else None,
        }
        await websocket.send_json(initial)

        # Keep connection alive — consume any client messages
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state.ws_disconnect(websocket)
    except Exception:
        state.ws_disconnect(websocket)
