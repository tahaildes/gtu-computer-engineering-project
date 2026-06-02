"""
MOD-05 — In-memory state cache & WebSocket manager
Holds the live twin state, latest LLM report, and connected WS clients.
"""

import json
import time
import logging
from fastapi import WebSocket

from models import TwinState, MaintenanceReport

logger = logging.getLogger("mod05.state")


# ── Twin state cache ─────────────────────────────────────────

twin_cache: TwinState = TwinState(
    version=0,
    updated_at=0,
    zones={
        "ZONE_A": {},
        "ZONE_B": {},
        "MACHINE": {"state": "NORMAL"},
    },
)

# ── Latest LLM report cache ─────────────────────────────────

report_cache: MaintenanceReport | None = None

# ── Last ingest timestamp (for /health) ──────────────────────

last_ingest_ms: int = 0


def update_last_ingest(timestamp_ms: int) -> None:
    global last_ingest_ms
    last_ingest_ms = timestamp_ms


# ── Twin cache helpers ───────────────────────────────────────

def update_ambient(zone_id: str, data: dict) -> None:
    """Merge ambient sensor data into the twin cache for a zone."""
    global twin_cache
    twin_cache.zones.setdefault(zone_id, {})
    twin_cache.zones[zone_id].update(data)
    twin_cache.version += 1
    twin_cache.updated_at = int(time.time() * 1000)


def update_machine(data: dict) -> None:
    """Merge machine telemetry into the MACHINE zone of the twin cache."""
    global twin_cache
    twin_cache.zones.setdefault("MACHINE", {})
    twin_cache.zones["MACHINE"].update(data)
    twin_cache.version += 1
    twin_cache.updated_at = int(time.time() * 1000)


def update_alarm(zone_id: str) -> None:
    """Mark a zone as having an active alarm."""
    global twin_cache
    twin_cache.zones.setdefault(zone_id, {})
    twin_cache.zones[zone_id]["alarm"] = "ALARM"
    twin_cache.version += 1
    twin_cache.updated_at = int(time.time() * 1000)


def set_report(report: MaintenanceReport) -> None:
    global report_cache
    report_cache = report


def reset_state() -> None:
    """Reset all in-memory caches back to defaults (used by /admin/reset-db)."""
    global twin_cache, report_cache, last_ingest_ms
    twin_cache = TwinState(
        version=0,
        updated_at=0,
        zones={
            "ZONE_A": {},
            "ZONE_B": {},
            "MACHINE": {"state": "NORMAL"},
        },
    )
    report_cache = None
    last_ingest_ms = 0


# ── WebSocket client management ──────────────────────────────

ws_clients: list[WebSocket] = []


async def ws_connect(ws: WebSocket) -> None:
    """Accept and register a new WebSocket client."""
    await ws.accept()
    ws_clients.append(ws)
    logger.info(f"[WS] Client connected. Total: {len(ws_clients)}")


def ws_disconnect(ws: WebSocket) -> None:
    """Remove a WebSocket client from the list."""
    if ws in ws_clients:
        ws_clients.remove(ws)
    logger.info(f"[WS] Client disconnected. Total: {len(ws_clients)}")


async def broadcast(data: dict) -> None:
    """Push a JSON message to all connected WebSocket clients.
    Silently removes clients that have disconnected mid-send.
    """
    if not ws_clients:
        return
    message = json.dumps(data)
    for ws in list(ws_clients):
        try:
            await ws.send_text(message)
        except Exception:
            # Client disconnected — remove silently
            if ws in ws_clients:
                ws_clients.remove(ws)
