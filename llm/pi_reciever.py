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

# MOD-04 motoru — uygulama başlarken bir kez oluşturulur
engine = PredictiveEngine()


@app.on_event("startup")
def startup():
    """Uygulama başladığında motoru ve callback'leri başlat."""
    register_callbacks(engine)   # pi_callbacks.py'deki fonksiyonu çağır
    engine.start()
    log.info("MOD-04 motoru başlatıldı.")


@app.on_event("shutdown")
def shutdown():
    """Uygulama kapanırken motoru düzgünce durdur."""
    engine.stop()
    log.info("MOD-04 motoru durduruldu.")


# ──────────────────────────────────────────────
# GELEN VERİ MODELLERİ (API'nin gönderdiği JSON formatı)
# ──────────────────────────────────────────────

class AmbientPayload(BaseModel):
    zone_id: str
    temperature_c: float
    humidity_pct: float
    co2_ppm: float
    pm25: float
    timestamp_ms: int


class MachinePayload(BaseModel):
    rpm: float
    vibration_g: float
    power_w: float
    machine_temp_c: float
    output_units: int
    timestamp_ms: int
    # Opsiyonel alanlar (ESP32 #3 gönderiyorsa)
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
# Pi'nin kendi belleği — son gelen ambient ve machine verileri
# (TwinState oluşturmak için ikisine de ihtiyaç var)
# ──────────────────────────────────────────────

_last_ambients: dict[str, AmbientSnapshot] = {}   # zone_id → snapshot
_last_machine: Optional[MachineSnapshot] = None


def _try_build_twin(alarm_flags: List[str] = []) -> Optional[TwinState]:
    """
    Elimizde en az bir ambient ve bir machine verisi varsa TwinState oluştur.
    İkisi de yoksa None döner — motor tetiklenmez.
    """
    if not _last_ambients or _last_machine is None:
        return None

    import time
    return TwinState(
        ambient=list(_last_ambients.values()),
        machine=_last_machine,
        alarm_flags=alarm_flags,
        snapshot_version=int(time.time()),   # basit versiyon numarası
        updated_at=int(time.time() * 1000),
    )


# ──────────────────────────────────────────────
# ENDPOINT'LER
# ──────────────────────────────────────────────

@app.post("/ingest/ambient")
def ingest_ambient(payload: AmbientPayload):
    """
    API'den gelen ortam sensörü verisini kaydet.
    Her zone'un son verisi _last_ambients'te tutulur.
    """
    global _last_ambients

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

    # TwinState oluşturup motoru tetikle
    twin = _try_build_twin()
    if twin:
        engine.on_twin_update(twin)

    return {"ok": True}


@app.post("/ingest/machine")
def ingest_machine(payload: MachinePayload):
    """
    API'den gelen makine telemetrisini kaydet.
    """
    global _last_machine

    _last_machine = MachineSnapshot(
        rpm=payload.rpm,
        vibration_g=payload.vibration_g,
        power_w=payload.power_w,
        machine_temp_c=payload.machine_temp_c,
        output_units=payload.output_units,
        state="NORMAL",          # kural motoru (MOD-03) bunu güncelleyecek
        timestamp_ms=payload.timestamp_ms,
    )
    log.info("Makine güncellendi: rpm=%.0f vibration=%.2f temp=%.1f",
             payload.rpm, payload.vibration_g, payload.machine_temp_c)

    # TwinState oluşturup motoru tetikle
    twin = _try_build_twin()
    if twin:
        engine.on_twin_update(twin)

    return {"ok": True}


@app.post("/ingest/alarm")
def ingest_alarm(payload: AlarmPayload):
    """
    API'den gelen alarm verisini al.
    Alarm bayrağını ekleyerek motoru hemen tetikle (anlık analiz).
    """
    alarm_flag = f"{payload.sensor_field.upper()}"   # örn: "CO2_PPM"

    twin = _try_build_twin(alarm_flags=[alarm_flag])
    if twin:
        log.warning("Alarm tetiklendi: %s=%.1f (eşik: %.1f)",
                    payload.sensor_field, payload.value, payload.threshold)
        engine.on_twin_update(twin)
    else:
        log.warning("Alarm geldi ama henüz twin oluşturulamadı (veri eksik).")

    return {"ok": True}


@app.get("/health")
def health():
    """Pi'nin sağlık durumu — API bu endpoint'i çağırarak Pi'nin ayakta olup olmadığını kontrol eder."""
    return {
        "status": "ok",
        "engine_stats": engine.get_stats(),
        "has_ambient": len(_last_ambients) > 0,
        "has_machine": _last_machine is not None,
    }