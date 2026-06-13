# Dark Factory — GTU CSE 396 IIoT Project

> A full-stack Industrial IoT system for predictive maintenance of a simulated dark (lights-out) factory.
> Built for the Gebze Technical University CSE 396 Computer Engineering Project course.

---

## Table of Contents

- [System Overview](#system-overview)
- [Architecture](#architecture)
- [Module Breakdown](#module-breakdown)
  - [MOD-01 — Ambient Sensors (ESP32 #1 & #2)](#mod-01--ambient-sensors-esp32-1--2)
  - [MOD-02 — Machine Telemetry (ESP32 #3)](#mod-02--machine-telemetry-esp32-3)
  - [MOD-03 / MOD-04 — Pi Receiver & LLM Engine](#mod-03--mod-04--pi-receiver--llm-engine)
  - [MOD-05 — FastAPI Hub & Dashboard](#mod-05--fastapi-hub--dashboard)
- [Repository Structure](#repository-structure)
- [Data Flow](#data-flow)
- [Sensor & Actuator Reference](#sensor--actuator-reference)
- [API Quick Reference](#api-quick-reference)
- [WebSocket Protocol](#websocket-protocol)
- [Quick Start](#quick-start)
- [Demo / Simulation Mode](#demo--simulation-mode)
- [Enum Reference](#enum-reference)
- [Team](#team)

---

## System Overview

**Dark Factory** simulates a fully automated, lights-out industrial facility. Three ESP32 microcontrollers collect ambient environmental data and machine telemetry, which is forwarded to a central FastAPI hub. The hub persists readings to SQLite, maintains an in-memory digital twin, forwards data to a Raspberry Pi for LLM-based predictive maintenance analysis, and pushes live updates to a React dashboard over WebSocket.

Key features:

- **Real-time digital twin** — in-memory factory state updated on every sensor ingest
- **LLM predictive maintenance** — Qwen 2.5 running locally via Ollama on the Pi; analyzes sensor history every 60 s or immediately on alarm
- **5-state machine degradation model** — NORMAL → HEATING → DEGRADING → CRITICAL → FAILURE
- **Demo mode** — full JavaScript simulation engine; runs entirely in-browser with no backend
- **Live mode** — wires the dashboard to the real FastAPI backend via REST + WebSocket

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SENSOR LAYER (ESP32)                         │
│                                                                     │
│  ESP32 #1 (MOD-01)          ESP32 #2 (MOD-01)     ESP32 #3 (MOD-02)│
│  ZONE_A — Ambient           ZONE_B — Ambient       Compressor       │
│  BME280, MQ-2, DHT          DHT, MQ-2              Sim + Sensors    │
│  → temperature_c            → temperature_c        → rpm            │
│  → humidity_pct             → humidity_pct         → vibration_g    │
│  → co2_ppm                  → co2_ppm              → temp_c         │
│  → lpg_ppm (MQ-2)           → lpg_ppm              → power_w        │
│  → pressure_hpa (BME280)    → pressure_hpa         → pressure_bar   │
│                                                    → oil_temp_c     │
│                                                    → airflow_lpm    │
└───────────────────────┬─────────────────────────────────┬───────────┘
                        │  HTTP POST (Wi-Fi / JSON)        │
                        ▼                                  ▼
┌───────────────────────────────────────────────────────────────────┐
│              MOD-05 — FastAPI Hub  :8000                          │
│                                                                   │
│  POST /ingest/ambient   POST /ingest/machine   POST /ingest/alarm │
│                ↓                 ↓                   ↓            │
│         SQLite (aiosqlite) ←─────┴───────────────────┘            │
│         In-memory Twin Cache                                      │
│                ↓                                                  │
│    POST forward to Pi :8001 (fire-and-forget)                     │
│                ↓                                                  │
│    WebSocket /ws  ──────────────────────────────────────────────► │
└───────────────────────────────────────────────────────────────────┘
                        │  HTTP forward                             │
                        ▼                                          │
┌───────────────────────────────────────────┐                      │
│  MOD-03/04 — Raspberry Pi  :8001          │                      │
│                                           │                      │
│  pi_receiver.py — receives forwarded data │                      │
│  llm_engine.py  — PredictiveEngine        │                      │
│  Ollama (qwen2.5:0.5b) local inference    │                      │
│                ↓                          │                      │
│  POST /decision/report  ──────────────────┼──────────────────►   │
│  POST /decision/actuator ─────────────────┼──────────────────►   │
└───────────────────────────────────────────┘                      │
                                                                   ▼
                                              ┌─────────────────────────────┐
                                              │  React Dashboard (Browser)  │
                                              │  Dark Factory.html           │
                                              │  FloorMap.jsx                │
                                              │  MachineDetail.jsx           │
                                              │  simulation.js (Demo mode)  │
                                              └─────────────────────────────┘
```

---

## Module Breakdown

### MOD-01 — Ambient Sensors (ESP32 #1)

**Hardware:** ESP32 DevKit + BME280 (I²C, GPIO 21/22) + MQ135i (CO₂/NH₃, GPIO 34/35) + MQ-2 (LPG/smoke, GPIO 32/33)  
**Firmware:** [`esp32/esp32_1_sensor/esp32_1_sensor.ino`](esp32/esp32_1_sensor/esp32_1_sensor.ino)  
**Zone:** `ZONE_A`  
**Posting interval:** 3 000 ms → `POST /ingest/ambient`  
**Alarm interval:** immediate when threshold breached → `POST /ingest/alarm`

Reads BME280 via I²C and both MQ sensors via 12-bit ADC. Converts raw ADC values to PPM using sensor-specific calibration curves.

**Payload sent by firmware:**
```json
{
  "zone_id":       "ZONE_A",
  "temperature_c": 28.5,
  "humidity_pct":  58.2,
  "pressure_hpa":  1013.1,
  "co2_ppm":       420.0,
  "lpg_ppm":       115.0,
  "timestamp_ms":  9021
}
```

> No `pm25` field — no PM2.5 sensor fitted. `pressure_hpa`, `lpg_ppm` are always included when BME280 and MQ-2 are functional.

**Alarm thresholds:**

| Sensor | WARNING | CRITICAL |
|--------|---------|----------|
| CO₂ | > 800 ppm | > 1 500 ppm |
| LPG | > 300 ppm | > 500 ppm |

**Alarm payload:**
```json
{ "source_module": "MOD-01", "zone_id": "ZONE_A",
  "sensor_field": "lpg_ppm", "value": 520.0, "threshold": 500.0, "timestamp_ms": 12000 }
```

**Arduino libraries required:** Adafruit BME280, Adafruit Unified Sensor, ArduinoJson

### MOD-01 — Actuator Controller (ESP32 #2)

**Hardware:** ESP32 DevKit + DC Fan (GPIO 13, PWM via 2N2222) + Passive Buzzer (GPIO 16) + LED (GPIO 2, 220 Ω) + Mist Maker (GPIO 14, pulse via 2N2222)  
**Firmware:** [`esp32/esp32_2_actuator/esp32_2_actuator.ino`](esp32/esp32_2_actuator/esp32_2_actuator.ino)  
**Zone:** `ZONE_A`  
**Poll interval:** 1 000 ms → `GET /cmd/ZONE_A`

Polls for pending commands and executes them. Acknowledges every executed command via `POST /cmd/ZONE_A/ack`.

**Supported device types:**

| `device_type` | Effect | Control signal |
|---------------|--------|----------------|
| `DEV_FAN` | Fan PWM speed | `value_pct` → 0–100% |
| `DEV_VENT` | Treated as fan | `value_pct` → 0–100% |
| `DEV_COOLER` | Treated as fan | `value_pct` → 0–100% |
| `DEV_BUZZER` | Buzzer on/off | `relay_state` true/false |
| `DEV_LED` | LED on/off | `relay_state` true/false |
| `DEV_MIST_MAKER` | Mist maker pulse toggle | `relay_state` true/false |

> No servo in the actual firmware — `DEV_SERVO_VENT` commands are accepted by the API but ignored by the hardware.

**Arduino libraries required:** ArduinoJson

### MOD-02 — Machine Telemetry (ESP32 #3)

**Hardware:** ESP32 DevKit — no external sensors; purely synthetic simulation  
**Firmware:** [`esp32/esp32_3_compressor/esp32_3_compressor.ino`](esp32/esp32_3_compressor/esp32_3_compressor.ino)  
**Zone:** `MACHINE`  
**Posting interval:** 2 000 ms → `POST /ingest/machine`  
**BOOT button (GPIO 0):** triggers immediate FAILURE state

Runs a 5-state software simulation. Values are smoothly interpolated with soft-lerp transitions between state-specific ranges.

**State machine transitions:**
```
 NORMAL ──(1% chance per tick)──► HEATING ──(20 ticks/40 s)──► DEGRADING
                                                                     │
 NORMAL ◄──────(30 ticks/60 s)── FAILURE ◄──(15 ticks)── CRITICAL ◄─┘
```
BOOT button press → immediate jump to FAILURE from any state.

**Metric ranges per state:**

| State | temp_c | rpm | vibration_g | pressure_bar |
|-------|--------|-----|-------------|---------------|
| NORMAL | 33–46 | 1415–1485 | 0.10–0.45 | 7.4–8.6 |
| HEATING | 43–72 | 1370–1465 | 0.28–0.70 | 6.8–8.6 |
| DEGRADING | 68–90 | 1290–1430 | 0.45–1.60 | 5.2–7.8 |
| CRITICAL | 86–108 | 1080–1310 | 1.40–3.60 | 2.8–5.8 |
| FAILURE | 98–115 | 0–1120 | 3.20–8.00 | 0.0–3.2 |

**Payload sent by firmware:**
```json
{
  "node":         "compressor",
  "state":        "NORMAL",
  "temp_c":       36.4,
  "rpm":          1457,
  "vibration_g":  0.28,
  "power_w":      753,
  "ts_ms":        4021,
  "pressure_bar": 8.12,
  "oil_temp_c":   41.3,
  "airflow_lpm":  278
}
```

**Arduino libraries required:** ArduinoJson

### MOD-03 / MOD-04 — Pi Receiver & LLM Engine

**Runtime:** Raspberry Pi — runs `llm/pi_receiver.py` on port `8001`  
**LLM:** Ollama with `qwen2.5:0.5b` running locally  
**Source:** [`llm/`](llm/)

#### Pi Receiver (`pi_receiver.py`)

Receives forwarded sensor data from the MOD-05 API hub via HTTP. Maintains the last known `AmbientSnapshot` per zone and the last `MachineSnapshot`. When both are available, assembles a `TwinState` and triggers the predictive engine.

Endpoints exposed (called by MOD-05, not ESP32s directly):
- `POST /ingest/ambient`
- `POST /ingest/machine`
- `POST /ingest/alarm`
- `GET /health`

#### LLM Engine (`llm_engine.py` — `PredictiveEngine`)

- Maintains a rolling history of up to **30 TwinState snapshots**
- Runs analysis periodically every **60 seconds**
- Triggers **immediately** on `RISK_WARN`, `RISK_CRITICAL`, or `HIGH_CO2/HIGH_TEMP/GAS` alarm flags
- Calls Ollama via `POST http://127.0.0.1:11434/api/generate`
- Validates JSON response and extracts a `MaintenanceReport` with:
  - `risk_level` — RISK_OK | RISK_WATCH | RISK_WARN | RISK_CRITICAL
  - `predicted_failure_hrs`
  - `anomalies[]`
  - `recommended_action`
  - `confidence`
  - `actuator_commands[]` — filtered/validated before dispatch
- POSTs results back to MOD-05 via `POST /decision/report` and `POST /decision/actuator`
- Safety rule: DEV_MIST_MAKER commands are blocked when a real gas/CO₂ alarm is active

**Run the Pi receiver:**
```bash
cd llm/
pip install fastapi uvicorn requests
uvicorn pi_reciever:app --host 0.0.0.0 --port 8001
```

### MOD-05 — FastAPI Hub & Dashboard

**Source:** [`api/`](api/) (backend) · [`front-end/`](front-end/) (dashboard)

The central hub of the system. Receives all sensor data, persists it, maintains the digital twin, forwards to the Pi, and serves the React dashboard.

#### Backend (`api/`)

| File | Role |
|------|------|
| `main.py` | FastAPI app entry point, CORS, router registration, lifespan |
| `models.py` | Pydantic v2 models & enums (mirrors `factory_types.h`) |
| `database.py` | Async SQLite via aiosqlite — schema, CRUD, WAL mode |
| `state.py` | In-memory twin cache, report cache, WebSocket client list |
| `pi_client.py` | Async httpx — fire-and-forget forwarding to the Pi |
| `simulate.py` | Standalone fake ESP32 + fake Pi data pump for testing |
| `routers/ingest.py` | `POST /ingest/ambient`, `/machine`, `/alarm` |
| `routers/decision.py` | `POST /decision/actuator`, `/report` |
| `routers/commands.py` | `GET /cmd/{zone_id}`, `POST /cmd/{zone_id}/ack` |
| `routers/dashboard.py` | `GET /twin`, `/report`, `/history`, `/reports`, `/health` |
| `routers/control.py` | `POST /actuator/cmd`, `/machine/control` |
| `routers/websocket.py` | `WS /ws` |
| `routers/admin.py` | `POST /admin/reset-db`, `/admin/cleanup` |

**Run the API:**
```bash
cd api/
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

#### Dashboard (`front-end/`)

| File | Role |
|------|------|
| `Dark Factory.html` | Single-file React app (CDN React + Babel) — main entry point |
| `FloorMap.jsx` | Interactive SVG factory floor map with zone overlays |
| `MachineDetail.jsx` | Compressor detail page — telemetry sparklines, actuator controls |
| `simulation.js` | Full client-side simulation engine (Demo mode) |

Open `front-end/Dark Factory.html` directly in a browser. Toggle **DEMO ↔ LIVE** in the top-right corner.

---

## Repository Structure

```
gtu-computer-engineering-project/
├── README.md                          ← this file
│
├── api/                               ← MOD-05 FastAPI backend
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── state.py
│   ├── pi_client.py
│   ├── simulate.py
│   ├── requirements.txt
│   ├── README.md                      ← API-specific docs
│   ├── MOD05_API_SPEC.md              ← full API spec
│   └── routers/
│       ├── ingest.py
│       ├── decision.py
│       ├── commands.py
│       ├── dashboard.py
│       ├── control.py
│       ├── websocket.py
│       └── admin.py
│
├── front-end/                         ← MOD-05 React dashboard
│   ├── Dark Factory.html
│   ├── FloorMap.jsx
│   ├── MachineDetail.jsx
│   └── simulation.js
│
├── esp32/                             ← Real ESP32 firmware (Arduino)
│   ├── esp32_1_sensor/
│   │   └── esp32_1_sensor.ino         ← ESP32 #1: BME280 + MQ135i + MQ-2
│   ├── esp32_2_actuator/
│   │   └── esp32_2_actuator.ino       ← ESP32 #2: Fan, Buzzer, LED, Mist
│   ├── esp32_3_compressor/
│   │   └── esp32_3_compressor.ino     ← ESP32 #3: 5-state machine simulation
│   └── docs/
│       └── DOKUMANTASYON.md           ← Hardware wiring & setup guide (Turkish)
│
├── llm/                               ← MOD-03/04 Pi receiver + LLM engine
│   ├── pi_reciever.py
│   ├── llm_engine.py
│   ├── factory_types.py
│   ├── promp_builder.py
│   ├── pi_callbacks.py
│   └── test_mock.py
│
├── mod5/                              ← Earlier MOD-05 prototype
│   ├── mod05_api.py
│   └── README.md
│
└── Group3_Dark_Factory/               ← Shared firmware headers & project docs
    ├── Headers/
    │   ├── factory_types.h            ← Canonical C data structures
    │   ├── mod01_ambient_hal.h        ← ESP32 #1 & #2 HAL interface
    │   ├── mod02_machine_sim.h        ← ESP32 #3 HAL interface
    │   ├── mod03_digital_twin.h
    │   ├── mod04_predictive_engine.h
    │   └── mod05_api_dashboard.h
    ├── Readmes/
    └── Dark_Factory_Guncellenmis_TamSurum_V4.docx
```

---

## Data Flow

### Sensor Ingest Path (happy path)

```
ESP32 firmware
    │  POST /ingest/ambient  (every 3 s)
    │  POST /ingest/machine  (every 1 s)
    ▼
api/routers/ingest.py
    ├─ Validate payload (Pydantic)
    ├─ Write rows to SQLite (aiosqlite, WAL mode)
    ├─ Update in-memory twin cache (state.py)
    ├─ Fire-and-forget forward to Pi :8001 (pi_client.py)
    └─ Broadcast WS snapshot to all connected dashboards
```

### Command Path (LLM → ESP32)

```
Pi llm_engine.py
    │  POST /decision/actuator  →  api/routers/decision.py
    │                               └─ INSERT into pending_commands
    │                               └─ Broadcast WS "ack" event
    │
ESP32 polls  GET /cmd/{zone_id}   (flat JSON response)
    │  ← { has_cmd: true, cmd_id, device_type, value_pct, relay_state, source }
    │
ESP32 executes command
    │
    └─ POST /cmd/{zone_id}/ack  →  DELETE from pending_commands
                                   └─ Broadcast WS "ack" event
```

### Alarm Path

```
ESP32 detects threshold breach
    │  POST /ingest/alarm
    ▼
api/routers/ingest.py
    ├─ Broadcast WS "alarm" event  →  Dashboard updates alarm badge
    ├─ Forward to Pi (immediate LLM trigger)
    └─ Dashboard captures lpg_ppm value from alarm payload if sensor_field == "lpg_ppm"
```

---

## Sensor & Actuator Reference

### Ambient Sensors (MOD-01 — ESP32 #1)

| Sensor IC | Field | Unit | GPIO | Notes |
|-----------|-------|------|------|-------|
| BME280 (I²C) | `temperature_c` | °C | SDA=21, SCL=22 | Required |
| BME280 | `humidity_pct` | % | — | Required |
| BME280 | `pressure_hpa` | hPa | — | Required (if BME OK) |
| MQ135i | `co2_ppm` | ppm | A-OUT=34, D-OUT=35 | Required |
| MQ-2 | `lpg_ppm` | ppm | A-OUT=32, D-OUT=33 | Required |
| — | `pm25` | µg/m³ | — | **Not fitted** — no sensor |

### Machine Sensors (MOD-02 — ESP32 #3)

| Sensor | Field | Unit | Notes |
|--------|-------|------|-------|
| Synthetic sim | `rpm` | rpm | Required |
| Synthetic sim | `vibration_g` | g | Required |
| Synthetic sim | `power_w` | W | Required |
| Synthetic sim | `temp_c` | °C | Required |
| Synthetic sim | `pressure_bar` | bar | Required |
| Synthetic sim | `oil_temp_c` | °C | Required |
| Synthetic sim | `airflow_lpm` | L/min | Required |

### Actuator Devices (ESP32 #2 — ZONE_A)

| Enum | Device | GPIO | Drive |
|------|--------|------|-------|
| `DEV_FAN` | DC cooling fan (25 kHz PWM) | 13 | 2N2222 NPN transistor |
| `DEV_BUZZER` | Passive piezo buzzer | 16 | Direct PWM |
| `DEV_LED` | Indicator LED | 2 | 220 Ω direct |
| `DEV_MIST_MAKER` | Ultrasonic mist maker (pulse toggle) | 14 | 2N2222 NPN transistor |
| `DEV_VENT` / `DEV_COOLER` | Mapped to fan speed | 13 | — |

---

## API Quick Reference

All endpoints served on port `8000`.

### Ingest (ESP32 → API)

| Method | Path | Body |
|--------|------|------|
| `POST` | `/ingest/ambient` | `AmbientSnapshot` JSON |
| `POST` | `/ingest/machine` | `MachineSnapshot` JSON |
| `POST` | `/ingest/alarm` | `AlarmEvent` JSON |

### Decision (Pi → API)

| Method | Path | Body |
|--------|------|------|
| `POST` | `/decision/actuator` | `ActuatorCmd` JSON |
| `POST` | `/decision/report` | `MaintenanceReport` JSON |

### Commands (ESP32 polls)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/cmd/{zone_id}` | Poll for pending command (flat JSON) |
| `POST` | `/cmd/{zone_id}/ack` | Acknowledge executed command |

### Dashboard (React → API)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/twin` | Current digital twin state |
| `GET` | `/report` | Latest LLM maintenance report |
| `GET` | `/history?limit=50` | Sensor reading history (max 500) |
| `GET` | `/reports?limit=10` | LLM report history |
| `GET` | `/health` | Pi reachability, pending cmds, DB size |
| `POST` | `/actuator/cmd` | Manual actuator override |
| `POST` | `/machine/control` | Force machine state / reset |
| `WS` | `/ws` | Real-time push stream |

### Admin

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/reset-db` | Truncate all tables, reset caches |
| `POST` | `/admin/cleanup` | Prune sensor readings older than 2 h |

---

## WebSocket Protocol

Connect to `ws://<host>:8000/ws`. On connect the server immediately sends the current twin state. Subsequent messages are pushed on every ingest or event.

```jsonc
// snapshot — pushed on every sensor ingest
{ "type": "snapshot", "snapshot": { "version": 42, "zones": { ... } }, "report": { ... } }

// alarm — immediately on /ingest/alarm
{ "type": "alarm", "alarm": { "zone_id": "ZONE_A", "sensor_field": "co2_ppm", "value": 1150.0, "threshold": 1000.0 } }

// report — immediately on /decision/report
{ "type": "report", "report": { "risk_level": "RISK_WARN", "predicted_failure_hrs": 2.5, ... } }

// ack — on command queued or ESP32 acknowledgement
{ "type": "ack", "cmd_id": "uuid-here", "status": "OK" }
```

---

## Quick Start

### 1. Start the API

```bash
cd api/
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Start the Pi Receiver (on Raspberry Pi or localhost)

```bash
cd llm/
pip install fastapi uvicorn requests
uvicorn pi_reciever:app --host 0.0.0.0 --port 8001
# Requires Ollama running: ollama run qwen2.5:0.5b
```

### 3. Run the Simulator (replaces real ESP32s for testing)

```bash
cd api/
python simulate.py
# or against a remote API:
python simulate.py --url http://192.168.1.50:8000
```

### 4. Open the Dashboard

Open `front-end/Dark Factory.html` in any modern browser.  
- **DEMO mode** — runs entirely in-browser, no backend needed  
- **LIVE mode** — toggle the switch in the top-right to connect to `http://localhost:8000`

### 5. Flash the ESP32s (real hardware)

See [`esp32/docs/DOKUMANTASYON.md`](esp32/docs/DOKUMANTASYON.md) for full wiring diagrams and Arduino IDE setup.

**Before flashing — update credentials in each `.ino`:**
```cpp
#define WIFI_SSID     "your-ssid"
#define WIFI_PASSWORD "your-password"
#define API_HOST      "192.168.x.x"   // IP of the machine running the FastAPI hub
```

Flash order: ESP32 #3 → ESP32 #1 → ESP32 #2

---

## Demo / Simulation Mode

`simulation.js` implements a full client-side twin of the backend simulation engine:

- 5-state machine (NORMAL → HEATING → DEGRADING → CRITICAL → FAILURE) with smooth lerp transitions
- Ambient sensor drift (sinusoidal + Gaussian noise)
- LPG/pressure/CO₂/PM2.5 generation with per-zone profiles
- Alarm threshold triggering
- Actuator state management (`applyCmd`)

All dashboard components work identically in Demo and Live modes. The `simulate.py` script on the backend mirrors this logic so the API and browser stay in sync.

---

## Enum Reference

```
zone_id:        ZONE_A | ZONE_B | MACHINE
device_type:    DEV_FAN | DEV_COOLER | DEV_VENT | DEV_BUZZER | DEV_LED | DEV_MIST_MAKER
risk_level:     RISK_OK | RISK_WATCH | RISK_WARN | RISK_CRITICAL
source:         RULE | LLM | MANUAL
machine_state:  NORMAL | HEATING | DEGRADING | CRITICAL | FAILURE
alarm_status:   OK | WARNING | CRITICAL
```

---

## Team

**GTU CSE 396 — Group 3 · Spring 2026**

| Module | Member(s) |
|--------|-----------|
| MOD-01 (ESP32 #1 & #2 — Ambient) | Emirhan Çalışkan, Mehmet Akif Pekşen, Ahmet Burak Çelebi, Burak Kurtaran |
| MOD-02 (ESP32 #3 — Machine) | Emirhan Çalışkan, Ahmet Burak Çelebi, Mehmet Akif Pekşen |
| MOD-03 (Digital Twin / Pi) | Zeynep Sude Turan, Dilara Gözen, Taha Emirhan İldeş |
| MOD-04 (LLM Engine) | Zeynep Sude Turan, Dilara Gözen, Yunus Emre Manav |
| MOD-05 (API Hub & Dashboard) | Yunus Emre Manav, Taha Emirhan İldeş, Burak Kurtaran |

---

*GTU CSE 396 — Dark Factory · Spring 2026*
