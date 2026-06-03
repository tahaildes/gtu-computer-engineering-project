"""
pi_receiver.py  —  Raspberry Pi tarafında çalışır.
MOD-05 API'den gelen sensör verilerini karşılar,
TwinState'e dönüştürür ve MOD-04 motorunu tetikler.

Çalıştırmak için:
    pip install fastapi uvicorn
    uvicorn pi_receiver:app --host 0.0.0.0 --port 8001
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import logging

from factory_types import (
    TwinState,
    AmbientSnapshot,
    MachineSnapshot,
)
from llm_engine import PredictiveEngine
from pi_callbacks import register_callbacks

# ──────────────────────────────────────────────
# UYGULAMA VE MOTOR BAŞLATMA
# ──────────────────────────────────────────────

log = logging.getLogger("pi_receiver")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Dark Factory Pi Receiver", version="1.0")

engine = PredictiveEngine()

# Alarm durumu — tek seferlik aç/kapat için
_alarm_on = False


@app.on_event("startup")
def startup():
    register_callbacks(engine)
    engine.start()
    log.info("MOD-04 motoru başlatıldı.")


@app.on_event("shutdown")
def shutdown():
    engine.stop()
    log.info("MOD-04 motoru durduruldu.")


# ──────────────────────────────────────────────
# GELEN VERİ MODELLERİ
# ──────────────────────────────────────────────

class AmbientPayload(BaseModel):
    zone_id: str = "ZONE_A"
    temperature_c: float = 0.0
    humidity_pct: float = 0.0
    co2_ppm: float = 0.0
    pm25: Optional[float] = 0.0
    timestamp_ms: int = 0
    lpg_ppm: Optional[float] = 0.0
    pressure_hpa: Optional[float] = 0.0

class MachinePayload(BaseModel):
    rpm: float = 0.0
    vibration_g: float = 0.0
    power_w: float = 0.0
    machine_temp_c: float = 0.0
    output_units: int = 0
    timestamp_ms: int = 0
    pressure_bar: Optional[float] = None
    oil_temp_c: Optional[float] = None
    airflow_lpm: Optional[float] = None

class AlarmPayload(BaseModel):
    source_module: str
    sensor_field: str
    value: float
    threshold: float
    zone_id: str
    timestamp_ms: int


# ──────────────────────────────────────────────
# Pi belleği
# ──────────────────────────────────────────────

_last_ambients: dict[str, AmbientSnapshot] = {}
_last_machine: Optional[MachineSnapshot] = None


def _try_build_twin(alarm_flags: List[str] = []) -> Optional[TwinState]:
    if not _last_ambients or _last_machine is None:
        return None
    import time
    return TwinState(
        ambient=list(_last_ambients.values()),
        machine=_last_machine,
        alarm_flags=alarm_flags,
        snapshot_version=int(time.time()),
        updated_at=int(time.time() * 1000),
    )


def _send_cmd(zone_id, device, pct, state):
    import httpx, time
    try:
        httpx.post("http://10.161.35.114:8000/decision/actuator", json={
            "zone_id": zone_id,
            "device_type": device,
            "value_pct": pct,
            "relay_state": state,
            "source": "RULE",
            "timestamp_ms": int(time.time() * 1000),
        }, timeout=3)
    except Exception as e:
        log.error("%s komutu gönderilemedi: %s", device, e)


# ──────────────────────────────────────────────
# ENDPOINT'LER
# ──────────────────────────────────────────────

@app.post("/feed/ambient")
def ingest_ambient(payload: AmbientPayload):
    global _last_ambients, _alarm_on

    snapshot = AmbientSnapshot(
        zone_id=payload.zone_id,
        temperature_c=payload.temperature_c,
        humidity_pct=payload.humidity_pct,
        co2_ppm=payload.co2_ppm,
        pm25=payload.pm25,
        timestamp_ms=payload.timestamp_ms,
    )
    _last_ambients[payload.zone_id] = snapshot
    log.info("Ambient güncellendi: zone=%s temp=%.1f co2=%.0f",
             payload.zone_id, payload.temperature_c, payload.co2_ppm)

    # Gaz/CO2 normale döndüyse bir kez kapat
    if payload.co2_ppm < 800 and (payload.lpg_ppm or 0) < 300:
        if _alarm_on:
            _alarm_on = False
            for device in ["DEV_FAN", "DEV_BUZZER", "DEV_LED", "DEV_MIST_MAKER"]:
                _send_cmd(payload.zone_id, device, 0.0, False)
            log.info("Kural motoru TÜM CİHAZLAR kapattı.")

    twin = _try_build_twin()
    if twin:
        engine.on_twin_update(twin)

    return {"ok": True}


@app.post("/feed/machine")
def ingest_machine(payload: MachinePayload):
    global _last_machine

    _last_machine = MachineSnapshot(
        rpm=payload.rpm,
        vibration_g=payload.vibration_g,
        power_w=payload.power_w,
        machine_temp_c=payload.machine_temp_c or 0.0,
        output_units=payload.output_units or 0,
        state="NORMAL",
        timestamp_ms=payload.timestamp_ms,
    )
    log.info("Makine güncellendi: rpm=%.0f vibration=%.2f temp=%.1f",
             payload.rpm, payload.vibration_g, payload.machine_temp_c)

    twin = _try_build_twin()
    if twin:
        engine.on_twin_update(twin)

    return {"ok": True}


@app.post("/feed/alarm")
def ingest_alarm(payload: AlarmPayload):
    global _alarm_on

    sensor = payload.sensor_field.upper()
    if "LPG" in sensor or "GAS" in sensor:
        alarm_flag = "GAS_ALARM"
    elif "CO2" in sensor:
        alarm_flag = "HIGH_CO2"
    elif "TEMP" in sensor:
        alarm_flag = "HIGH_TEMP"
    else:
        alarm_flag = sensor

    # Zaten alarm aktifse hiçbir şey yapma
    if _alarm_on:
        return {"ok": True}

    # İlk alarm — cihazları aç ve LLM'i tetikle
    _alarm_on = True
    for device in ["DEV_FAN", "DEV_BUZZER", "DEV_LED", "DEV_MIST_MAKER"]:
        _send_cmd(payload.zone_id, device, 100.0, True)
    log.warning("Kural motoru TÜM CİHAZLAR açtı: %s=%.1f", payload.sensor_field, payload.value)

    twin = _try_build_twin(alarm_flags=[alarm_flag])
    if twin:
        log.warning("Alarm tetiklendi: %s=%.1f (eşik: %.1f)",
                    payload.sensor_field, payload.value, payload.threshold)
        engine.on_twin_update(twin)

    return {"ok": True}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "alarm_on": _alarm_on,
        "engine_stats": engine.get_stats(),
        "has_ambient": len(_last_ambients) > 0,
        "has_machine": _last_machine is not None,
    }