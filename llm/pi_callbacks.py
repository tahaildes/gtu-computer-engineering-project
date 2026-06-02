"""
pi_callbacks.py  —  Raspberry Pi tarafında çalışır.
MOD-04'ün ürettiği rapor ve komutları MOD-05 API'sine gönderir.
"""

import logging
import httpx

from factory_types import MaintenanceReport, ActuatorCmd
from llm_engine import PredictiveEngine

API_URL = "http://10.161.35.59:8000"  # API sunucusunun adresi

log = logging.getLogger("pi_callbacks")


def on_report(report: MaintenanceReport) -> None:
    payload = {
        "risk_level":            report.risk_level,
        "predicted_failure_hrs": report.predicted_failure_hrs,
        "anomalies":             report.anomalies,
        "recommended_action":    report.recommended_action,
        "confidence":            report.confidence,
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
            "device_type": cmd.device,
            "value_pct":   cmd.value_pct,
            "relay_state": cmd.state,
            "source":      cmd.source,
        }
        try:
            response = httpx.post(f"{API_URL}/decision/actuator", json=payload, timeout=10.0)
            response.raise_for_status()
            log.info("Komut gönderildi: %s/%s", cmd.zone_id, cmd.device)
        except Exception as exc:
            log.error("Komut gönderilemedi: %s", exc)


def register_callbacks(engine: PredictiveEngine) -> None:
    engine.register_report_callback(on_report)
    engine.register_command_callback(on_commands)
    log.info("Callback'ler MOD-04 motoruna kayıt edildi.")
