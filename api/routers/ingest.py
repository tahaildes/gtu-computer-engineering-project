"""
MOD-05 — Ingest router
ESP32s push sensor data here.  Each endpoint:
  1. Validates via Pydantic
  2. Writes to SQLite
  3. Updates in-memory twin cache
  4. Forwards to Pi (fire-and-forget background task)
  5. Broadcasts to WebSocket clients
"""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks

from models import AmbientSnapshot, MachineSnapshot, AlarmEvent
import database as db
import state
import pi_client

logger = logging.getLogger("mod05.ingest")
router = APIRouter(prefix="/ingest", tags=["ingest"])


# ── Sensor unit mapping ──────────────────────────────────────

AMBIENT_UNITS = {
    "temperature_c": "°C",
    "humidity_pct": "%",
    "co2_ppm": "ppm",
    "pm25": "µg/m³",
}

MACHINE_UNITS = {
    "rpm":         "rpm",
    "vibration_g": "g",
    "power_w":     "W",
    "temp_c":      "°C",
    "pressure_bar": "bar",
    "oil_temp_c":  "°C",
    "airflow_lpm": "L/min",
}


@router.post("/ambient")
async def ingest_ambient(snapshot: AmbientSnapshot):
    """Receive ambient sensor reading from ESP32 #1 or #2."""
    payload = snapshot.model_dump()
    zone = snapshot.zone_id.value

    # 1. Write to DB — one row per sensor field
    rows = [
        (zone, field, getattr(snapshot, field), unit, snapshot.timestamp_ms)
        for field, unit in AMBIENT_UNITS.items()
    ]
    await db.insert_sensor_readings_batch(rows)

    # 2. Update twin cache
    state.update_ambient(zone, {
        "temperature_c": snapshot.temperature_c,
        "humidity_pct":  snapshot.humidity_pct,
        "co2_ppm":       snapshot.co2_ppm,
        "pm25":          snapshot.pm25,
    })
    state.update_last_ingest(snapshot.timestamp_ms)

    # 3. Forward to Pi (fire-and-forget)
    asyncio.create_task(_safe_forward(pi_client.forward_ambient, payload))

    # 4. Broadcast snapshot to WS clients
    await state.broadcast({
        "type": "snapshot",
        "snapshot": state.twin_cache.model_dump(),
        "report": state.report_cache.model_dump() if state.report_cache else None,
    })

    return {"status": "ok"}


@router.post("/machine")
async def ingest_machine(snapshot: MachineSnapshot):
    """Receive machine telemetry from ESP32 #3."""
    payload = snapshot.model_dump()

    # 1. Write to DB
    rows = []
    for field, unit in MACHINE_UNITS.items():
        value = getattr(snapshot, field, None)
        if value is not None:
            rows.append(("MACHINE", field, value, unit, snapshot.ts_ms))
    await db.insert_sensor_readings_batch(rows)

    # 2. Update twin cache
    machine_data = {
        "state":          snapshot.state or "NORMAL",
        "rpm":            snapshot.rpm,
        "vibration_g":    snapshot.vibration_g,
        "power_w":        snapshot.power_w,
        "machine_temp_c": snapshot.temp_c,  # store as machine_temp_c for frontend
    }
    # Include optional fields if present
    if snapshot.pressure_bar is not None:
        machine_data["pressure_bar"] = snapshot.pressure_bar
    if snapshot.oil_temp_c is not None:
        machine_data["oil_temp_c"] = snapshot.oil_temp_c
    if snapshot.airflow_lpm is not None:
        machine_data["airflow_lpm"] = snapshot.airflow_lpm

    state.update_machine(machine_data)
    state.update_last_ingest(snapshot.ts_ms)

    # 3. Forward to Pi (fire-and-forget)
    asyncio.create_task(_safe_forward(pi_client.forward_machine, payload))

    # 4. Broadcast snapshot to WS clients
    await state.broadcast({
        "type": "snapshot",
        "snapshot": state.twin_cache.model_dump(),
        "report": state.report_cache.model_dump() if state.report_cache else None,
    })

    return {"status": "ok"}


@router.post("/alarm")
async def ingest_alarm(alarm: AlarmEvent):
    """Receive alarm event from any ESP32."""
    payload = alarm.model_dump()
    zone = alarm.zone_id.value

    # 1. Write to safety_events table
    await db.insert_safety_event(
        source_module=alarm.source_module,
        sensor_field=alarm.sensor_field,
        value=alarm.value,
        threshold=alarm.threshold,
        zone_id=zone,
        timestamp_ms=alarm.timestamp_ms,
    )

    # 2. Update twin cache alarm flag
    state.update_alarm(zone)

    # 3. Forward to Pi (fire-and-forget)
    asyncio.create_task(_safe_forward(pi_client.forward_alarm, payload))

    # 4. Immediately broadcast alarm to WS clients
    await state.broadcast({
        "type": "alarm",
        "alarm": payload,
    })

    return {"status": "ok"}


async def _safe_forward(fn, payload: dict) -> None:
    """Wrapper to catch any exception from fire-and-forget Pi forwards."""
    try:
        await fn(payload)
    except Exception as e:
        logger.error(f"[Pi forward] Unexpected error: {e}")
