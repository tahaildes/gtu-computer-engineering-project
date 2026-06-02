"""
MOD-05 — Pydantic v2 models & enums
Mirrors factory_types.h for the Dark Factory IIoT system.
"""

from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


# ── Enums ─────────────────────────────────────────────────────

class ZoneId(str, Enum):
    ZONE_A  = "ZONE_A"
    ZONE_B  = "ZONE_B"
    MACHINE = "MACHINE"


class DeviceType(str, Enum):
    DEV_FAN        = "DEV_FAN"
    DEV_COOLER     = "DEV_COOLER"
    DEV_VENT       = "DEV_VENT"
    DEV_BUZZER     = "DEV_BUZZER"
    DEV_SERVO_VENT = "DEV_SERVO_VENT"
    DEV_MIST_MAKER = "DEV_MIST_MAKER"


class RiskLevel(str, Enum):
    RISK_OK       = "RISK_OK"
    RISK_WATCH    = "RISK_WATCH"
    RISK_WARN     = "RISK_WARN"
    RISK_CRITICAL = "RISK_CRITICAL"


class CommandSource(str, Enum):
    RULE   = "RULE"
    LLM    = "LLM"
    MANUAL = "MANUAL"


# ── Sensor / Ingest models ───────────────────────────────────

class AmbientSnapshot(BaseModel):
    zone_id:       ZoneId
    temperature_c: float
    humidity_pct:  float
    co2_ppm:       float
    pm25:          float
    timestamp_ms:  int


class MachineSnapshot(BaseModel):
    node:         Optional[str]   = None  # "compressor"
    state:        Optional[str]   = None  # NORMAL|HEATING|DEGRADING|CRITICAL|FAILURE
    temp_c:       float                   # was: machine_temp_c
    rpm:          float
    vibration_g:  float
    power_w:      float
    ts_ms:        int                     # was: timestamp_ms
    pressure_bar: Optional[float] = None
    oil_temp_c:   Optional[float] = None
    airflow_lpm:  Optional[float] = None
    # removed: output_units


class AlarmEvent(BaseModel):
    source_module: str          # "MOD-01" | "MOD-02"
    sensor_field:  str          # "co2_ppm" | "temperature_c" etc.
    value:         float
    threshold:     float
    zone_id:       ZoneId
    timestamp_ms:  int


# ── Command models ───────────────────────────────────────────

class ActuatorCmd(BaseModel):
    zone_id:      ZoneId
    device_type:  DeviceType
    value_pct:    float          # 0.0 – 100.0
    relay_state:  bool
    source:       CommandSource
    cmd_id:       Optional[str] = None        # assigned by server
    timestamp_ms: Optional[int] = None


class ManualActuatorCmd(BaseModel):
    """Subset of ActuatorCmd used by the dashboard manual override endpoint.
    source is forced to MANUAL on the server side."""
    zone_id:     ZoneId
    device_type: DeviceType
    value_pct:   float
    relay_state: bool


class MachineCmd(BaseModel):
    cmd:   str                  # "MACHINE_RESET" | "MACHINE_SET_STATE"
    state: Optional[str] = None # "NORMAL" | "DEGRADING" | "FAULT"


class CmdAck(BaseModel):
    """Body sent by ESP32 when acknowledging a command."""
    cmd_id: str
    status: str                 # "OK" | other


# ── Decision models ──────────────────────────────────────────

class MaintenanceReport(BaseModel):
    risk_level:            RiskLevel
    predicted_failure_hrs: float
    anomalies:             List[str]
    recommended_action:    str
    confidence:            Optional[float] = None
    timestamp_ms:          int


# ── Twin state ───────────────────────────────────────────────

class TwinState(BaseModel):
    version:    int
    updated_at: int
    zones:      dict            # keyed by ZoneId value string
