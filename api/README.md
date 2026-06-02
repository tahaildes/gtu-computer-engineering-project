# MOD-05 — Dark Factory API

Central FastAPI hub for the Dark Factory IIoT system (GTU CSE 396). Receives sensor data from ESP32 nodes, forwards it to the Raspberry Pi (MOD-03/04) for rule evaluation and LLM analysis, queues actuator commands back to ESP32s, and serves live data to the React dashboard via REST and WebSocket.

## Quick Start

```bash
cd api/
pip3 install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger docs at [http://localhost:8000/docs](http://localhost:8000/docs).

## Project Structure

```
api/
├── main.py              # FastAPI app, CORS, router registration, lifespan
├── models.py            # Pydantic v2 models & enums (mirrors factory_types.h)
├── database.py          # Async SQLite (aiosqlite) — schema, CRUD, WAL mode
├── state.py             # In-memory twin cache, report cache, WS client list
├── pi_client.py         # Async httpx client — fire-and-forget forwarding to Pi
├── simulate.py          # Fake ESP32 + fake Pi data pump for testing
├── requirements.txt     # fastapi, uvicorn, pydantic, aiosqlite, httpx
└── routers/
    ├── ingest.py        # POST /ingest/ambient, /machine, /alarm
    ├── decision.py      # POST /decision/actuator, /report
    ├── commands.py      # GET /cmd/{zone_id}, POST /cmd/{zone_id}/ack
    ├── dashboard.py     # GET /twin, /report, /history, /reports, /health
    ├── control.py       # POST /actuator/cmd, /machine/control
    ├── websocket.py     # WS /ws
    └── admin.py         # POST /admin/reset-db, /admin/cleanup
```

## REST Endpoints

| Method | Endpoint | Caller | Purpose |
|--------|----------|--------|---------|
| `POST` | `/ingest/ambient` | ESP32 #1&#38;#2 | Push ambient sensor reading |
| `POST` | `/ingest/machine` | ESP32 #3 | Push machine telemetry |
| `POST` | `/ingest/alarm` | Any ESP32 | Push threshold alarm |
| `POST` | `/decision/actuator` | Pi | Queue actuator command for ESP32 |
| `POST` | `/decision/report` | Pi | Submit LLM maintenance report |
| `GET` | `/cmd/{zone_id}` | ESP32s | Poll for pending command (FIFO) |
| `POST` | `/cmd/{zone_id}/ack` | ESP32s | Acknowledge executed command |
| `GET` | `/twin` | Dashboard | Current factory state snapshot |
| `GET` | `/report` | Dashboard | Latest LLM report (404 if none) |
| `GET` | `/history?limit=50` | Dashboard | Sensor reading history (max 500) |
| `GET` | `/reports?limit=10` | Dashboard | LLM report history |
| `GET` | `/health` | Dashboard | Pi reachability, pending cmds, DB size |
| `POST` | `/actuator/cmd` | Dashboard | Manual actuator override (source=MANUAL) |
| `POST` | `/machine/control` | Dashboard | Machine reset / force state |
| `POST` | `/admin/reset-db` | Dev tools | Truncate all tables, reset caches |
| `POST` | `/admin/cleanup` | Dev tools | Prune sensor readings older than 2h |

## Data Payloads

#### `POST /ingest/ambient`
```jsonc
{ "zone_id": "ZONE_A", "temperature_c": 28.5, "humidity_pct": 58.2, "co2_ppm": 420.0, "pm25": 12.3, "timestamp_ms": 1748694523000 }
```
#### `POST /ingest/machine`
```jsonc
{ "rpm": 1457.0, "vibration_g": 0.28, "power_w": 753.0, "machine_temp_c": 36.4, "output_units": 42, "timestamp_ms": 1748694523000,
  "pressure_bar": 8.12, // optional
  "oil_temp_c": 41.3,   // optional
  "airflow_lpm": 278.0  // optional
}
```
#### `POST /ingest/alarm`
```jsonc
{ "source_module": "MOD-01", "sensor_field": "co2_ppm", "value": 1150.0, "threshold": 1000.0, "zone_id": "ZONE_A", "timestamp_ms": 1748694523000 }
```
#### `POST /decision/actuator`
```jsonc
{ "zone_id": "ZONE_A", "device_type": "DEV_FAN", "value_pct": 80.0, "relay_state": false, "source": "LLM", "timestamp_ms": 1748694523000 }
```
#### `POST /decision/report`
```jsonc
{ "risk_level": "RISK_WARN", "predicted_failure_hrs": 2.5, "anomalies": ["machine_temp_rising", "rpm_dropping"],
  "recommended_action": "activate_zone_a_cooling", "confidence": 0.85, /* optional */ "timestamp_ms": 1748694523000 }
```
#### `POST /cmd/{zone_id}/ack`
```jsonc
{ "cmd_id": "a1b2c3d4-uuid", "status": "OK" }
```
#### `POST /actuator/cmd`
```jsonc
{ "zone_id": "ZONE_A", "device_type": "DEV_FAN", "value_pct": 80.0, "relay_state": false }
```
#### `POST /machine/control`
```jsonc
{ "cmd": "MACHINE_RESET" }
{ "cmd": "MACHINE_SET_STATE", "state": "NORMAL" } // state: NORMAL | DEGRADING | FAULT
```

**Enum values:**
```
zone_id:      ZONE_A | ZONE_B | MACHINE
device_type:  DEV_FAN | DEV_COOLER | DEV_VENT | DEV_BUZZER | DEV_SERVO_VENT | DEV_MIST_MAKER
risk_level:   RISK_OK | RISK_WATCH | RISK_WARN | RISK_CRITICAL
source:       RULE | LLM | MANUAL
```

## WebSocket

Connect to `ws://<host>:8000/ws`. Server pushes JSON with a `type` field:

**`snapshot`** — on every ingest (twin state + latest report):
```json
{ "type": "snapshot", "snapshot": { "version": 42, "zones": { ... } }, "report": { ... } }
```

**`alarm`** — immediately on `/ingest/alarm`:
```json
{ "type": "alarm", "alarm": { "zone_id": "ZONE_A", "sensor_field": "co2_ppm", "value": 1150.0, "threshold": 1000.0 } }
```

**`report`** — immediately on `/decision/report`:
```json
{ "type": "report", "report": { "risk_level": "RISK_WARN", "predicted_failure_hrs": 2.5, "anomalies": ["machine_temp_rising"] } }
```

**`ack`** — on command queued or ESP32 acknowledgement:
```json
{ "type": "ack", "cmd_id": "uuid-here", "status": "OK" }
```

On connect, the server sends an initial `snapshot` with current state.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PI_BASE_URL` | `http://pi:8001` | Pi receiver address (set in `pi_client.py`) |
| `DB_PATH` | `dark_factory.db` | SQLite file path (env var, used in `database.py`) |

## Simulation

`simulate.py` is a standalone script that acts as fake ESP32 + fake Pi, pumping realistic data into the API. It runs a 5-state machine (NORMAL → HEATING → DEGRADING → CRITICAL → FAILURE) with smooth value transitions and concurrent loops for ambient, machine, report, actuator, and alarm data. On startup it calls `/admin/reset-db` for a clean slate.

```bash
# Terminal 1
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2
python3 simulate.py
python3 simulate.py --url http://192.168.1.50:8000  # custom API URL
```

## Open Questions

- **MachineSnapshot optional fields** — does ESP32 #3 send `pressure_bar`, `oil_temp_c`, `airflow_lpm`? (confirm with Çelebi)
- **DeviceType enum** — are `DEV_SERVO_VENT` and `DEV_MIST_MAKER` in the final firmware? (confirm with Emirhan)
- **MaintenanceReport.confidence** — does MOD-04 output this field? (confirm with Ahmet Burak / Burak)
- **Pi receiver port** — is `8001` agreed for MOD-03's receiver API?
