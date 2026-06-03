"""
pi_callbacks.py  —  Raspberry Pi tarafında çalışır.
MOD-04'ün ürettiği rapor ve komutları MOD-05 API'sine gönderir.
"""

import logging
import httpx

from factory_types import MaintenanceReport, ActuatorCmd
from llm_engine import PredictiveEngine

API_URL = "http://10.161.35.114:8000"
log = logging.getLogger("pi_callbacks")

def on_report(report: MaintenanceReport) -> None:
    import time
    payload = {
        "risk_level":            report.risk_level,
        "predicted_failure_hrs": report.predicted_failure_hrs if report.predicted_failure_hrs is not None else 0.0,
        "anomalies":             report.anomalies,
        "recommended_action":    report.recommended_action,
        "confidence":            report.confidence,
        "timestamp_ms":          int(time.time() * 1000),
    }
    try:
        response = httpx.post(f"{API_URL}/decision/report", json=payload, timeout=10.0)
        response.raise_for_status()
        log.info("Rapor API'ye gönderildi: risk=%s", report.risk_level)
    except Exception as exc:
        log.error("Rapor gönderilemedi: %s", exc)


def on_commands(commands: list) -> None:
    for cmd in commands:
        payload = {
            "zone_id":     cmd.zone_id,
            "device_type": cmd.device_type,
            "value_pct":   cmd.value_pct,
            "relay_state": cmd.state,
            "source":      cmd.source,
        }
        try:
            response = httpx.post(f"{API_URL}/decision/actuator", json=payload, timeout=10.0)
            response.raise_for_status()
            log.info("Komut gönderildi: %s/%s", cmd.zone_id, cmd.device_type)
        except Exception as exc:
            log.error("Komut gönderilemedi: %s", exc)


def register_callbacks(engine: PredictiveEngine) -> None:
    engine.register_report_callback(on_report)
    engine.register_command_callback(on_commands)
    log.info("Callback'ler MOD-04 motoruna kayıt edildi.")
