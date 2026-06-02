"""
pi_callbacks.py  —  Raspberry Pi tarafında çalışır.
MOD-04'ün ürettiği rapor ve komutları MOD-05 API'sine gönderir.

Bu dosyayı değiştirmen gereken tek şey:
    API_URL = "http://API_SUNUCUSUNUN_IP_ADRESİ:8000"
"""

import logging
import httpx

from factory_types import MaintenanceReport, ActuatorCmd
from llm_engine import PredictiveEngine

# ──────────────────────────────────────────────
# YAPILANDIRMA — sadece bu satırı değiştir
# ──────────────────────────────────────────────

API_URL = "http://api:8000"   # API sunucusunun adresi (Docker'da "api", IP'de "192.168.x.x")

log = logging.getLogger("pi_callbacks")


# ──────────────────────────────────────────────
# CALLBACK FONKSİYONLARI
# ──────────────────────────────────────────────

def on_report(report: MaintenanceReport) -> None:
    """
    MOD-04 bir bakım raporu ürettiğinde bu fonksiyon çağrılır.
    Raporu API'nin /decision/report endpoint'ine gönderir.
    API oradan React dashboard'una WebSocket ile iletir.
    """
    payload = {
        "risk_level":            report.risk_level,
        "predicted_failure_hrs": report.predicted_failure_hrs,
        "anomalies":             report.anomalies,
        "recommended_action":    report.recommended_action,
        "confidence":            report.confidence,
    }

    try:
        response = httpx.post(
            f"{API_URL}/decision/report",
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        log.info("Rapor API'ye gönderildi: risk=%s confidence=%.2f",
                 report.risk_level, report.confidence)

    except httpx.TimeoutException:
        log.error("Rapor gönderilemedi: API zaman aşımı.")
    except httpx.HTTPStatusError as exc:
        log.error("Rapor gönderilemedi: HTTP %s — %s", exc.response.status_code, exc.response.text)
    except Exception as exc:
        log.error("Rapor gönderilemedi: %s", exc)


def on_commands(commands: list[ActuatorCmd]) -> None:
    """
    MOD-04 aktüatör komutları ürettiğinde bu fonksiyon çağrılır.
    Her komutu API'nin /decision/actuator endpoint'ine ayrı ayrı gönderir.
    API komutu kuyruğa alır, ESP32 GET /cmd/{zone_id} ile çeker.
    """
    for cmd in commands:
        payload = {
            "zone_id":     cmd.zone_id,
            "device_type": cmd.device,
            "value_pct":   cmd.value_pct,
            "relay_state": cmd.state,
            "source":      cmd.source,      # "LLM"
        }

        try:
            response = httpx.post(
                f"{API_URL}/decision/actuator",
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            log.info("Komut API'ye gönderildi: zone=%s device=%s state=%s value=%.1f%%",
                     cmd.zone_id, cmd.device, cmd.state, cmd.value_pct)

        except httpx.TimeoutException:
            log.error("Komut gönderilemedi (%s/%s): API zaman aşımı.", cmd.zone_id, cmd.device)
        except httpx.HTTPStatusError as exc:
            log.error("Komut gönderilemedi: HTTP %s — %s", exc.response.status_code, exc.response.text)
        except Exception as exc:
            log.error("Komut gönderilemedi (%s/%s): %s", cmd.zone_id, cmd.device, exc)


# ──────────────────────────────────────────────
# KAYIT FONKSİYONU — pi_receiver.py bunu çağırır
# ──────────────────────────────────────────────

def register_callbacks(engine: PredictiveEngine) -> None:
    """
    Callback'leri motora kayıt eder.
    pi_receiver.py startup'ında bir kez çağrılır.
    """
    engine.register_report_callback(on_report)
    engine.register_command_callback(on_commands)
    log.info("Callback'ler MOD-04 motoruna kayıt edildi.")