"""
factory_types.py  —  MOD-04
Veri tiplerinin düz string'lerle (Literal) sadeleştirilmiş hali.
"""

from dataclasses import dataclass
from typing import Literal, List, Optional

# ──────────────────────────────────────────────
# DÜZ STRING (LITERAL) TİPLERİ
# ──────────────────────────────────────────────

ZoneId = Literal["ZONE_A", "ZONE_B"]
DeviceType = Literal["DEV_FAN", "DEV_SERVO_VENT", "DEV_MIST_MAKER", "DEV_BUZZER"]
RiskLevel = Literal["RISK_OK", "RISK_WATCH", "RISK_WARN", "RISK_CRITICAL"]
ActuatorSource = Literal["RULE", "LLM", "MANUAL"]
MachineState = Literal["NORMAL", "DEGRADING", "FAULT"]


# ──────────────────────────────────────────────
# SENSÖR / DURUM YAPILARI
# ──────────────────────────────────────────────

@dataclass
class AmbientSnapshot:
    zone_id: ZoneId
    temperature_c: float
    humidity_pct: float
    co2_ppm: float
    pm25: float
    timestamp_ms: int


@dataclass
class MachineSnapshot:
    rpm: float
    vibration_g: float
    power_w: float
    machine_temp_c: float
    output_units: int
    state: MachineState
    timestamp_ms: int


@dataclass
class TwinState:
    ambient: List[AmbientSnapshot]
    machine: MachineSnapshot
    alarm_flags: List[str]
    snapshot_version: int
    updated_at: int


# ──────────────────────────────────────────────
# KOMUT VE RAPOR YAPILARI
# ──────────────────────────────────────────────

@dataclass
class ActuatorCmd:
    zone_id: ZoneId
    device_type: DeviceType
    value_pct: float
    relay_state: bool
    source: ActuatorSource


@dataclass
class MaintenanceReport:
    risk_level: RiskLevel
    predicted_failure_hrs: Optional[float]
    anomalies: List[str]
    recommended_action: str
    confidence: float
    actuator_commands: List[ActuatorCmd]
    raw_llm_output: str


@dataclass
class AlarmEvent:
    source_module: str
    sensor_field: str
    value: float
    threshold: float
    timestamp_ms: int