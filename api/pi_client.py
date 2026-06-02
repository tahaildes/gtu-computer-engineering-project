"""
MOD-05 — Async Pi HTTP client
Forwards sensor data to the Raspberry Pi (MOD-03/04) receiver.
All calls are fire-and-forget: errors are logged, never raised.
"""

import logging
import httpx

logger = logging.getLogger("mod05.pi_client")

# ── Configuration ────────────────────────────────────────────
# Change this to match your Pi's IP address and port.
PI_BASE_URL = "http://pi:8001"

# Shared httpx client — created lazily on first use
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=PI_BASE_URL,
            timeout=5.0,
        )
    return _client


async def close_client() -> None:
    """Close the shared HTTP client (call on app shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


# ── Forwarding functions ─────────────────────────────────────
# Each function posts the payload to the corresponding Pi endpoint.
# On any error (network, timeout, etc.) the error is logged and
# execution continues — the caller is never affected.

async def forward_ambient(payload: dict) -> None:
    """Forward an AmbientSnapshot to Pi."""
    try:
        client = _get_client()
        resp = await client.post("/feed/ambient", json=payload)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"[Pi] Failed to forward ambient data: {e}")


async def forward_machine(payload: dict) -> None:
    """Forward a MachineSnapshot to Pi."""
    try:
        client = _get_client()
        resp = await client.post("/feed/machine", json=payload)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"[Pi] Failed to forward machine data: {e}")


async def forward_alarm(payload: dict) -> None:
    """Forward an AlarmEvent to Pi."""
    try:
        client = _get_client()
        resp = await client.post("/feed/alarm", json=payload)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"[Pi] Failed to forward alarm data: {e}")


async def forward_machine_control(payload: dict) -> None:
    """Forward a MachineCmd to Pi for relay to ESP32 #3."""
    try:
        client = _get_client()
        resp = await client.post("/machine/control", json=payload)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"[Pi] Failed to forward machine control: {e}")


async def check_reachable() -> bool:
    """Check if Pi is reachable (for /health endpoint)."""
    try:
        client = _get_client()
        resp = await client.get("/", timeout=2.0)
        return resp.status_code < 500
    except Exception:
        return False
