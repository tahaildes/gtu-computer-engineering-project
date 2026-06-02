"""
MOD-05 — Async SQLite database layer
Uses aiosqlite for non-blocking I/O.  WAL mode for concurrent reads.
"""

import json
import time
import os
import aiosqlite

DB_PATH = os.getenv("DB_PATH", "dark_factory.db")

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Return the shared database connection, creating it if necessary."""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
    return _db


async def init_db() -> None:
    """Create tables, indexes, and enable WAL journal mode."""
    db = await get_db()

    await db.execute("PRAGMA journal_mode=WAL;")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id      TEXT    NOT NULL,
            sensor_type  TEXT    NOT NULL,
            value        REAL    NOT NULL,
            unit         TEXT    NOT NULL,
            timestamp_ms INTEGER NOT NULL
        );
    """)

    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_zone_sensor
        ON sensor_readings(zone_id, sensor_type, timestamp_ms DESC);
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_reports (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            report     TEXT    NOT NULL,
            created_at INTEGER NOT NULL
        );
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS safety_events (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            source_module TEXT    NOT NULL,
            sensor_field  TEXT    NOT NULL,
            value         REAL,
            threshold     REAL,
            zone_id       TEXT,
            timestamp_ms  INTEGER NOT NULL
        );
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS pending_commands (
            cmd_id     TEXT    PRIMARY KEY,
            zone_id    TEXT    NOT NULL,
            payload    TEXT    NOT NULL,
            created_at INTEGER NOT NULL,
            acked      INTEGER DEFAULT 0
        );
    """)

    await db.commit()


async def close_db() -> None:
    """Close the database connection."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None


# ── Sensor readings ──────────────────────────────────────────

async def insert_sensor_reading(
    zone_id: str,
    sensor_type: str,
    value: float,
    unit: str,
    timestamp_ms: int,
) -> None:
    db = await get_db()
    await db.execute(
        "INSERT INTO sensor_readings (zone_id, sensor_type, value, unit, timestamp_ms) "
        "VALUES (?, ?, ?, ?, ?)",
        (zone_id, sensor_type, value, unit, timestamp_ms),
    )
    await db.commit()


async def insert_sensor_readings_batch(rows: list[tuple]) -> None:
    """Insert multiple sensor readings at once.
    Each tuple: (zone_id, sensor_type, value, unit, timestamp_ms)
    """
    db = await get_db()
    await db.executemany(
        "INSERT INTO sensor_readings (zone_id, sensor_type, value, unit, timestamp_ms) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    await db.commit()


async def get_sensor_history(limit: int = 50) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT zone_id, sensor_type, value, unit, timestamp_ms "
        "FROM sensor_readings ORDER BY timestamp_ms DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "zone_id": row[0],
            "sensor_type": row[1],
            "value": row[2],
            "unit": row[3],
            "timestamp_ms": row[4],
        }
        for row in rows
    ]


# ── Maintenance reports ──────────────────────────────────────

async def insert_report(report_json: str, created_at: int | None = None) -> None:
    db = await get_db()
    ts = created_at or int(time.time() * 1000)
    await db.execute(
        "INSERT INTO maintenance_reports (report, created_at) VALUES (?, ?)",
        (report_json, ts),
    )
    await db.commit()


async def get_report_history(limit: int = 10) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT report, created_at FROM maintenance_reports "
        "ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [
        {"report": json.loads(row[0]), "created_at": row[1]}
        for row in rows
    ]


# ── Safety events ────────────────────────────────────────────

async def insert_safety_event(
    source_module: str,
    sensor_field: str,
    value: float,
    threshold: float,
    zone_id: str,
    timestamp_ms: int,
) -> None:
    db = await get_db()
    await db.execute(
        "INSERT INTO safety_events "
        "(source_module, sensor_field, value, threshold, zone_id, timestamp_ms) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (source_module, sensor_field, value, threshold, zone_id, timestamp_ms),
    )
    await db.commit()


# ── Pending commands ─────────────────────────────────────────

async def insert_pending_command(
    cmd_id: str,
    zone_id: str,
    payload_json: str,
) -> None:
    db = await get_db()
    await db.execute(
        "INSERT INTO pending_commands (cmd_id, zone_id, payload, created_at) "
        "VALUES (?, ?, ?, ?)",
        (cmd_id, zone_id, payload_json, int(time.time() * 1000)),
    )
    await db.commit()


async def get_oldest_pending_command(zone_id: str) -> dict | None:
    """Return the oldest un-acked command for a zone, or None."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT cmd_id, payload FROM pending_commands "
        "WHERE zone_id = ? AND acked = 0 "
        "ORDER BY created_at ASC LIMIT 1",
        (zone_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {"cmd_id": row[0], "payload": json.loads(row[1])}


async def ack_command(cmd_id: str) -> bool:
    """Mark a command as acked. Returns True if the command existed."""
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM pending_commands WHERE cmd_id = ?",
        (cmd_id,),
    )
    await db.commit()
    return cursor.rowcount > 0


async def count_pending_commands() -> dict[str, int]:
    """Return {zone_id: count} of un-acked pending commands."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT zone_id, COUNT(*) FROM pending_commands "
        "WHERE acked = 0 GROUP BY zone_id",
    )
    rows = await cursor.fetchall()
    counts = {"ZONE_A": 0, "ZONE_B": 0, "MACHINE": 0}
    for row in rows:
        counts[row[0]] = row[1]
    return counts


async def get_db_size_bytes() -> int:
    """Return the database file size in bytes."""
    try:
        return os.path.getsize(DB_PATH)
    except OSError:
        return 0


async def truncate_all_tables() -> None:
    """Delete all rows from all data tables (keeps schema intact)."""
    db = await get_db()
    await db.execute("DELETE FROM sensor_readings;")
    await db.execute("DELETE FROM safety_events;")
    await db.execute("DELETE FROM pending_commands;")
    await db.execute("DELETE FROM maintenance_reports;")
    await db.commit()


async def cleanup_old_readings(max_age_hours: int = 2) -> int:
    """Delete sensor readings older than max_age_hours. Returns number of rows deleted."""
    db = await get_db()
    cutoff_ms = int((time.time() - max_age_hours * 3600) * 1000)
    cursor = await db.execute(
        "DELETE FROM sensor_readings WHERE timestamp_ms < ?",
        (cutoff_ms,),
    )
    await db.commit()
    return cursor.rowcount

