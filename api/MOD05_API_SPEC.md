# MOD-05 — API Implementation Specification
**Dark Factory | GTU CSE 396**
_Last updated: 31.05.2026_

---

## Overview

MOD-05 is the central API hub of the Dark Factory system in the revised architecture.
It sits between all components and is responsible for:

- Receiving sensor data from ESP32s
- Forwarding data to the Raspberry Pi (MOD-03/04)
- Receiving decisions and LLM reports back from the Pi
- Queuing and delivering actuator commands to ESP32s
- Serving live data to the React dashboard via REST and WebSocket

**Stack:** Python 3.10+ · FastAPI · Uvicorn · SQLite · Pydantic

**Base URL:** `http://<server-ip>:8000`

**Pi receiver URL:** `http://<pi-ip>:8001` _(MOD-03 implements this, not MOD-05)_

---

## Data Types (Pydantic Models)

These mirror `factory_types.h`. Verify field names against Çelebi's final ESP32 code before implementing.

```python
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class ZoneId(str, Enum):
    ZONE_A  = "ZONE_A"
    ZONE_B  = "ZONE_B"
    MACHINE = "MACHINE"

class DeviceType(str, Enum):
    DEV_FAN       = "DEV_FAN"
    DEV_COOLER    = "DEV_COOLER"
    DEV_VENT      = "DEV_VENT"
    DEV_BUZZER    = "DEV_BUZZER"
    DEV_SERVO_VENT = "DEV_SERVO_VENT"   # confirm with Emirhan
    DEV_MIST_MAKER = "DEV_MIST_MAKER"   # confirm with Emirhan

class RiskLevel(str, Enum):
    RISK_OK       = "RISK_OK"
    RISK_WATCH    = "RISK_WATCH"
    RISK_WARN     = "RISK_WARN"
    RISK_CRITICAL = "RISK_CRITICAL"

class CommandSource(str, Enum):
    RULE   = "RULE"
    LLM    = "LLM"
    MANUAL = "MANUAL"

class AmbientSnapshot(BaseModel):
    zone_id:       ZoneId
    temperature_c: float
    humidity_pct:  float
    co2_ppm:       float
    pm25:          float
    timestamp_ms:  int

class MachineSnapshot(BaseModel):
    rpm:            float
    vibration_g:    float
    power_w:        float
    machine_temp_c: float
    output_units:   int
    timestamp_ms:   int
    # Confirm these with Çelebi — present in simulation.js but not in spec:
    pressure_bar:   Optional[float] = None
    oil_temp_c:     Optional[float] = None
    airflow_lpm:    Optional[float] = None

class AlarmEvent(BaseModel):
    source_module: str          # "MOD-01" | "MOD-02"
    sensor_field:  str          # "co2_ppm" | "temperature_c" etc.
    value:         float
    threshold:     float
    zone_id:       ZoneId
    timestamp_ms:  int

class ActuatorCmd(BaseModel):
    zone_id:     ZoneId
    device_type: DeviceType
    value_pct:   float          # 0.0 – 100.0
    relay_state: bool
    source:      CommandSource
    cmd_id:      Optional[str] = None       # assigned by server on creation
    timestamp_ms: Optional[int] = None

class MaintenanceReport(BaseModel):
    risk_level:           RiskLevel
    predicted_failure_hrs: float
    anomalies:            List[str]
    recommended_action:   str
    confidence:           Optional[float] = None   # confirm with MOD-04 team
    timestamp_ms:         int

class TwinState(BaseModel):
    version:    int
    updated_at: int
    zones:      dict            # keyed by ZoneId string

class MachineCmd(BaseModel):
    cmd:   str                  # "MACHINE_RESET" | "MACHINE_SET_STATE"
    state: Optional[str] = None # "NORMAL" | "DEGRADING" | "FAULT"
```

---

## Endpoints

### 1. ESP32 → Server (Ingest)

ESP32s push sensor readings to the server on every measurement cycle.
Server validates, stores to SQLite, forwards to Pi, and broadcasts to WebSocket clients.

---

#### `POST /ingest/ambient`

Called by ESP32 #1 and #2 every ~3 seconds.

**Request body:** `AmbientSnapshot`
```json
{
  "zone_id": "ZONE_A",
  "temperature_c": 28.5,
  "humidity_pct": 58.2,
  "co2_ppm": 420.0,
  "pm25": 12.3,
  "timestamp_ms": 1748694523000
}
```

**Response 200:**
```json
{ "status": "ok" }
```

**Response 422:** Pydantic validation error

**Server behavior:**
1. Validate payload
2. Write to `sensor_readings` table in SQLite
3. Forward to `POST http://pi:8001/feed/ambient`
4. Update in-memory twin state cache
5. Push updated snapshot to all WebSocket clients

---

#### `POST /ingest/machine`

Called by ESP32 #3 every ~1 second.

**Request body:** `MachineSnapshot`
```json
{
  "rpm": 1457.0,
  "vibration_g": 0.28,
  "power_w": 753.0,
  "machine_temp_c": 36.4,
  "output_units": 42,
  "timestamp_ms": 1748694523000
}
```

**Response 200:**
```json
{ "status": "ok" }
```

**Server behavior:** Same as `/ingest/ambient` but for machine data.
Forward to `POST http://pi:8001/feed/machine`.

---

#### `POST /ingest/alarm`

Called by any ESP32 when a threshold is crossed. Sent before the normal snapshot.

**Request body:** `AlarmEvent`
```json
{
  "source_module": "MOD-01",
  "sensor_field": "co2_ppm",
  "value": 1150.0,
  "threshold": 1000.0,
  "zone_id": "ZONE_A",
  "timestamp_ms": 1748694523000
}
```

**Response 200:**
```json
{ "status": "ok" }
```

**Server behavior:**
1. Write to `safety_events` table
2. Forward to `POST http://pi:8001/feed/alarm`
3. Immediately push `type: "alarm"` WebSocket event to all clients (do not wait for 2s cycle)

---

### 2. Pi → Server (Decisions)

Pi calls these after MOD-03 rule trigger or MOD-04 LLM analysis.

---

#### `POST /decision/actuator`

Pi sends an actuator command. Server queues it for the target ESP32 to pick up.

**Request body:** `ActuatorCmd`
```json
{
  "zone_id": "ZONE_A",
  "device_type": "DEV_FAN",
  "value_pct": 80.0,
  "relay_state": false,
  "source": "LLM",
  "timestamp_ms": 1748694523000
}
```

**Response 200:**
```json
{
  "status": "ok",
  "cmd_id": "a1b2c3d4-uuid"
}
```

**Server behavior:**
1. Assign a `cmd_id` (UUID)
2. Write to `pending_commands` table keyed by `zone_id`
3. Push `type: "ack"` WebSocket event to dashboard so operator sees the command was issued

---

#### `POST /decision/report`

Pi sends an LLM maintenance report after each MOD-04 analysis cycle.

**Request body:** `MaintenanceReport`
```json
{
  "risk_level": "RISK_WARN",
  "predicted_failure_hrs": 2.5,
  "anomalies": ["machine_temp_rising", "rpm_dropping"],
  "recommended_action": "activate_zone_a_cooling",
  "confidence": 0.85,
  "timestamp_ms": 1748694523000
}
```

**Response 200:**
```json
{ "status": "ok" }
```

**Server behavior:**
1. Write to `maintenance_reports` table
2. Update in-memory latest report cache
3. Immediately push `type: "report"` WebSocket event to all clients

---

### 3. Server → ESP32 (Command delivery)

ESP32s poll this endpoint. Server holds pending commands until ESP32 picks them up.

---

#### `GET /cmd/{zone_id}`

Called by each ESP32 on its polling interval (suggested: every 1 second).

**Path param:** `zone_id` — one of `ZONE_A`, `ZONE_B`, `MACHINE`

**Response — command pending:**
```json
{
  "has_cmd": true,
  "cmd": {
    "zone_id": "ZONE_A",
    "device_type": "DEV_FAN",
    "value_pct": 80.0,
    "relay_state": false,
    "source": "LLM",
    "cmd_id": "a1b2c3d4-uuid"
  }
}
```

**Response — nothing pending:**
```json
{ "has_cmd": false }
```

**Server behavior:**
- Returns the oldest pending command for that zone
- Does NOT clear it until ESP32 sends an ack
- If multiple commands are queued, returns one at a time (FIFO)

---

#### `POST /cmd/{zone_id}/ack`

ESP32 confirms it received and executed the command.

**Path param:** `zone_id`

**Request body:**
```json
{
  "cmd_id": "a1b2c3d4-uuid",
  "status": "OK"
}
```

**Response 200:**
```json
{ "status": "ok" }
```

**Server behavior:**
1. Remove command from `pending_commands` table
2. Push `type: "ack"` WebSocket event with execution status to dashboard

---

### 4. Frontend → Server (Dashboard reads)

---

#### `GET /twin`

Current factory state snapshot. Called on initial page load before WebSocket connects.

**Response 200:**
```json
{
  "version": 42,
  "updated_at": 1748694523000,
  "zones": {
    "ZONE_A": {
      "temperature_c": 28.5,
      "humidity_pct": 58.2,
      "co2_ppm": 420.0,
      "pm25": 12.3,
      "alarm": "OK"
    },
    "ZONE_B": {
      "temperature_c": 26.1,
      "humidity_pct": 55.0,
      "co2_ppm": 410.0,
      "pm25": 11.0,
      "alarm": "OK"
    },
    "MACHINE": {
      "state": "NORMAL",
      "rpm": 1457.0,
      "vibration_g": 0.28,
      "power_w": 753.0,
      "machine_temp_c": 36.4,
      "pressure_bar": 8.12,
      "oil_temp_c": 41.3,
      "airflow_lpm": 278.0
    }
  }
}
```

---

#### `GET /report`

Latest LLM maintenance report.

**Response 200:** `MaintenanceReport`
```json
{
  "risk_level": "RISK_WATCH",
  "predicted_failure_hrs": 18.0,
  "anomalies": ["rpm_dropping"],
  "recommended_action": "Schedule bearing inspection within 24 hours.",
  "confidence": 0.78,
  "timestamp_ms": 1748694523000
}
```

**Response 404:** No report generated yet
```json
{ "detail": "No report available yet" }
```

---

#### `GET /history?limit=50`

Sensor reading history from SQLite. Used to seed sparkline charts on page load.

**Query param:** `limit` (default: 50, max: 500)

**Response 200:**
```json
[
  {
    "zone_id": "ZONE_A",
    "sensor_type": "temperature_c",
    "value": 28.5,
    "unit": "°C",
    "timestamp_ms": 1748694523000
  },
  {
    "zone_id": "MACHINE",
    "sensor_type": "rpm",
    "value": 1457.0,
    "unit": "rpm",
    "timestamp_ms": 1748694522000
  }
]
```

---

#### `GET /reports?limit=10`

LLM report history from SQLite. Used for the report stream panel.

**Query param:** `limit` (default: 10)

**Response 200:**
```json
[
  {
    "report": {
      "risk_level": "RISK_CRITICAL",
      "predicted_failure_hrs": 0.5,
      "anomalies": ["machine_temp_rising", "vibration_spike"],
      "recommended_action": "Immediate shutdown recommended.",
      "confidence": 0.94,
      "timestamp_ms": 1748694523000
    },
    "created_at": 1748694523000
  }
]
```

---

#### `GET /health`

System health check. Dashboard uses this to show connectivity status.

**Response 200:**
```json
{
  "status": "ok",
  "pi_reachable": true,
  "last_ingest_ms": 1748694523000,
  "pending_cmds": {
    "ZONE_A": 0,
    "ZONE_B": 1,
    "MACHINE": 0
  },
  "db_size_bytes": 204800,
  "websocket_clients": 2
}
```

---

### 5. Frontend → Server (Manual control)

---

#### `POST /actuator/cmd`

Operator manually controls a device from the dashboard.
Goes into the same command queue as Pi decisions, tagged as `source: "MANUAL"`.

**Request body:**
```json
{
  "zone_id": "ZONE_A",
  "device_type": "DEV_FAN",
  "value_pct": 80.0,
  "relay_state": false
}
```

**Response 200:**
```json
{
  "status": "ok",
  "cmd_id": "a1b2c3d4-uuid"
}
```

---

#### `POST /machine/control`

Operator sends a control command to MOD-02 (reset or force state).
Server forwards to Pi which forwards to ESP32 #3 via MQTT.

**Request body:**
```json
{
  "cmd": "MACHINE_RESET"
}
```
or
```json
{
  "cmd": "MACHINE_SET_STATE",
  "state": "NORMAL"
}
```

**Response 200:**
```json
{ "status": "ok" }
```

---

### 6. WebSocket `/ws`

Browser connects here for live updates. Server pushes on two triggers:
- Every ~2 seconds (snapshot cycle)
- Immediately on alarm or new LLM report

**Connection:** `ws://<server-ip>:8000/ws`

---

**Message types (server → client):**

**Snapshot** (every ~2 seconds):
```json
{
  "type": "snapshot",
  "snapshot": {
    "version": 42,
    "updated_at": 1748694523000,
    "zones": { ... }
  },
  "report": {
    "risk_level": "RISK_OK",
    "predicted_failure_hrs": 99.0,
    "anomalies": [],
    "recommended_action": "No action required.",
    "timestamp_ms": 1748694400000
  }
}
```

**Alarm** (immediate on `/ingest/alarm`):
```json
{
  "type": "alarm",
  "alarm": {
    "source_module": "MOD-01",
    "sensor_field": "co2_ppm",
    "value": 1150.0,
    "threshold": 1000.0,
    "zone_id": "ZONE_A",
    "timestamp_ms": 1748694523000
  }
}
```

**Report** (immediate on `/decision/report`):
```json
{
  "type": "report",
  "report": {
    "risk_level": "RISK_WARN",
    "predicted_failure_hrs": 2.5,
    "anomalies": ["machine_temp_rising"],
    "recommended_action": "activate_zone_a_cooling",
    "confidence": 0.85,
    "timestamp_ms": 1748694523000
  }
}
```

**Ack** (when ESP32 confirms command execution):
```json
{
  "type": "ack",
  "cmd_id": "a1b2c3d4-uuid",
  "status": "OK"
}
```

---

## SQLite Schema (Server-side)

Server maintains its own lightweight DB. Pi keeps the full historical DB for LLM use.

```sql
-- Latest sensor readings (rolling, for dashboard history)
CREATE TABLE sensor_readings (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  zone_id      TEXT    NOT NULL,
  sensor_type  TEXT    NOT NULL,
  value        REAL    NOT NULL,
  unit         TEXT    NOT NULL,
  timestamp_ms INTEGER NOT NULL
);
CREATE INDEX idx_zone_sensor ON sensor_readings(zone_id, sensor_type, timestamp_ms DESC);

-- LLM maintenance reports
CREATE TABLE maintenance_reports (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  report     TEXT    NOT NULL,  -- serialized MaintenanceReport JSON
  created_at INTEGER NOT NULL
);

-- Safety events / alarms
CREATE TABLE safety_events (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  source_module TEXT   NOT NULL,
  sensor_field  TEXT   NOT NULL,
  value         REAL,
  threshold     REAL,
  zone_id       TEXT,
  timestamp_ms  INTEGER NOT NULL
);

-- Pending actuator commands (cleared after ESP32 ack)
CREATE TABLE pending_commands (
  cmd_id       TEXT    PRIMARY KEY,
  zone_id      TEXT    NOT NULL,
  payload      TEXT    NOT NULL,  -- serialized ActuatorCmd JSON
  created_at   INTEGER NOT NULL,
  acked        INTEGER DEFAULT 0
);
```

Enable WAL mode to avoid read/write contention:
```sql
PRAGMA journal_mode=WAL;
```

---

## Internal State (In-memory cache)

Server keeps these in memory for fast reads — avoids hitting SQLite on every WebSocket push:

```python
# Latest twin state (updated on every /ingest call)
twin_cache: TwinState = None

# Latest LLM report (updated on every /decision/report call)
report_cache: MaintenanceReport = None

# Connected WebSocket clients
ws_clients: List[WebSocket] = []
```

---

## Pi Receiver Endpoints (MOD-03 implements these)

Your server calls these. MOD-03's responsibility to implement on port 8001.

| Method | Endpoint | Body | Notes |
|---|---|---|---|
| `POST` | `http://pi:8001/feed/ambient` | `AmbientSnapshot` | Server calls after `/ingest/ambient` |
| `POST` | `http://pi:8001/feed/machine` | `MachineSnapshot` | Server calls after `/ingest/machine` |
| `POST` | `http://pi:8001/feed/alarm` | `AlarmEvent` | Server calls after `/ingest/alarm` |

If Pi is unreachable, server should log the failure and continue — do not return an error to the ESP32.

---

## Endpoint Summary

| Method | Endpoint | Caller | Purpose |
|---|---|---|---|
| `POST` | `/ingest/ambient` | ESP32 #1&#38;#2 | Push ambient sensor reading |
| `POST` | `/ingest/machine` | ESP32 #3 | Push machine telemetry |
| `POST` | `/ingest/alarm` | Any ESP32 | Push alarm event |
| `POST` | `/decision/actuator` | Pi (MOD-03/04) | Pi sends actuator command |
| `POST` | `/decision/report` | Pi (MOD-04) | Pi sends LLM report |
| `GET` | `/cmd/{zone_id}` | ESP32s | Poll for pending commands |
| `POST` | `/cmd/{zone_id}/ack` | ESP32s | Confirm command executed |
| `GET` | `/twin` | Browser | Get current factory state |
| `GET` | `/report` | Browser | Get latest LLM report |
| `GET` | `/history` | Browser | Get sensor history |
| `GET` | `/reports` | Browser | Get report history |
| `GET` | `/health` | Browser | System health check |
| `POST` | `/actuator/cmd` | Browser | Manual actuator control |
| `POST` | `/machine/control` | Browser | Manual machine control |
| `WS` | `/ws` | Browser | Live data stream |

---

## Open Questions (Resolve before implementing)

These need confirmation from teammates before you finalize the Pydantic models:

1. **`machine_snapshot_t` fields** — does it include `pressure_bar`, `oil_temp_c`, `airflow_lpm`? (ask Çelebi)
2. **`device_type_t` enum** — does it include `DEV_SERVO_VENT` and `DEV_MIST_MAKER`? (ask Emirhan)
3. **`maintenance_report_t`** — does MOD-04 output a `confidence` field? (ask Ahmet Burak / Burak)
4. **ESP32 transport** — HTTP POST or MQTT to server broker? (ask Emirhan)
5. **Command delivery to ESP32s** — polling or MQTT? (ask Emirhan / Çelebi)
6. **Pi receiver port** — is 8001 agreed for MOD-03's receiver API?

---

_GTU CSE 396 — Dark Factory Project — MOD-05 API Spec_
