"""
llm_engine.py  —  MOD-04
Bilişsel Kestirimci Motor: LLM tabanlı anomali tespiti ve kestirimci bakım.
"""

from __future__ import annotations
import json
import logging
import threading
import time
from collections import deque
from enum import Enum
from typing import Callable, Optional, Sequence

import requests

from factory_types import (
    ActuatorCmd,
    ActuatorSource,
    DeviceType,
    MaintenanceReport,
    RiskLevel,
    TwinState,
    ZoneId,
)
from promp_builder import SYSTEM_PROMPT, build_user_prompt

# ──────────────────────────────────────────────
# YAPILANDIRMA SABİTLERİ
# ──────────────────────────────────────────────

OLLAMA_URL        = "http://127.0.0.1:11434/api/generate" # Generate endpoint'i olmalı
OLLAMA_MODEL      = "qwen2.5:0.5b"
LLM_TEMPERATURE   = 0.2
LLM_HISTORY_LEN   = 30
LLM_INTERVAL_S    = 60.0
LLM_TIMEOUT_S     = 180
IMMEDIATE_LEVELS  = {"RISK_WARN", "RISK_CRITICAL"}

ENV_ALARM_PREFIXES = ("HIGH_CO2", "HIGH_GAS", "HIGH_TEMP", "HIGH_HUMIDITY",
                      "HIGH_PM25", "SMOKE", "GAS_")

log = logging.getLogger("MOD04")

class LLMError(str, Enum):
    LLM_ERR_VALIDATION = "LLM_ERR_VALIDATION"
    LLM_ERR_TIMEOUT    = "LLM_ERR_TIMEOUT"
    LLM_ERR_TRANSPORT  = "LLM_ERR_TRANSPORT"
    LLM_ERR_EMPTY      = "LLM_ERR_EMPTY"

# ──────────────────────────────────────────────
# KARAR TABLOSU
# ──────────────────────────────────────────────

def _has_real_env_anomaly(twin: TwinState) -> bool:
    return any(
        flag.upper().startswith(ENV_ALARM_PREFIXES)
        for flag in twin.alarm_flags
    )

def _validate_and_filter_commands(
    raw_cmds: list[ActuatorCmd],
    latest_twin: TwinState,
) -> list[ActuatorCmd]:
    env_anomaly = _has_real_env_anomaly(latest_twin)
    filtered: list[ActuatorCmd] = []

    for cmd in raw_cmds:
        # ActuatorSource enum olduğu için string kıyaslaması yapacağız veya getattr kullanacağız
        cmd_source = getattr(cmd, "source", cmd.source)
        
        if not (0.0 <= cmd.value_pct <= 100.0):
            log.warning("Komut reddedildi: value_pct=%.1f aralık dışı.", cmd.value_pct)
            continue

        if env_anomaly and cmd.device == "DEV_MIST_MAKER" and cmd.state:
            log.info("Sis Üretici komutu devre dışı bırakıldı: gerçek ortam anomalisi (gaz/CO2).")
            cmd = ActuatorCmd(
                zone_id=cmd.zone_id,
                device="DEV_MIST_MAKER",
                value_pct=0.0,
                state=False,
                source="LLM",
            )

        filtered.append(cmd)

    return filtered

# ──────────────────────────────────────────────
# LLM ÇAĞRISI
# ──────────────────────────────────────────────
def _call_ollama(user_prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": user_prompt,
        "system": SYSTEM_PROMPT,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": LLM_TEMPERATURE
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=None)
        response.raise_for_status()
        
        raw_text = response.json().get("response", "")
        if not raw_text:
            raise ValueError(LLMError.LLM_ERR_EMPTY)
            
        return raw_text

    except Exception as exc:
        log.error("Lokal Ollama çağrısı başarısız: %s", exc)
        raise ValueError(LLMError.LLM_ERR_TRANSPORT) from exc

# ──────────────────────────────────────────────
# JSON DOĞRULAMA VE DÖNÜŞTÜRME
# ──────────────────────────────────────────────

def _parse_maintenance_report(
    raw_text: str,
    latest_twin: TwinState,
) -> MaintenanceReport:
    clean = raw_text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        clean = "\n".join(
            ln for ln in lines
            if not ln.strip().startswith("```")
        ).strip()

    try:
        data: dict = json.loads(clean)
    except json.JSONDecodeError as exc:
        log.error("JSON parse hatası: %s | Ham: %.200s", exc, raw_text)
        raise ValueError(LLMError.LLM_ERR_VALIDATION) from exc

    required = {
        "risk_level", "predicted_failure_hrs",
        "anomalies", "recommended_action",
        "confidence", "actuator_commands",
    }
    missing = required - data.keys()
    if missing:
        log.error("Eksik alanlar: %s", missing)
        raise ValueError(LLMError.LLM_ERR_VALIDATION)

    # PYTHON 3.13 LITERAL TUZAKLARI TEMİZLENDİ! Sınıf yerine dümdüz string.
    try:
        risk_level = str(data["risk_level"])
    except ValueError:
        log.error("Geçersiz risk_level: %s", data["risk_level"])
        raise ValueError(LLMError.LLM_ERR_VALIDATION)

    try:
        confidence = float(data["confidence"])
        if not (0.0 <= confidence <= 1.0):
            raise ValueError
    except (TypeError, ValueError):
        log.error("Geçersiz confidence: %s", data["confidence"])
        raise ValueError(LLMError.LLM_ERR_VALIDATION)

    raw_cmds: list[ActuatorCmd] = []
    for idx, item in enumerate(data.get("actuator_commands", [])):
        try:
            cmd = ActuatorCmd(
                zone_id=str(item["zone_id"]),      # <-- Düzeltildi
                device=str(item["device"]),        # <-- Düzeltildi
                value_pct=float(item["value_pct"]),
                state=bool(item["state"]),
                source="LLM",                      # <-- Düzeltildi
            )
            raw_cmds.append(cmd)
        except (KeyError, ValueError) as exc:
            log.warning("Komut #%d atlandı (hatalı şema): %s", idx, exc)

    validated_cmds = _validate_and_filter_commands(raw_cmds, latest_twin)

    return MaintenanceReport(
        risk_level=risk_level,
        predicted_failure_hrs=data.get("predicted_failure_hrs"),
        anomalies=list(data.get("anomalies", [])),
        recommended_action=str(data.get("recommended_action", "")),
        confidence=confidence,
        actuator_commands=validated_cmds,
        raw_llm_output=raw_text,
    )

# ──────────────────────────────────────────────
# ANA MOTOR SINIFI
# ──────────────────────────────────────────────

class PredictiveEngine:
    def __init__(self) -> None:
        self._history: deque[TwinState] = deque(maxlen=LLM_HISTORY_LEN)
        self._history_lock = threading.Lock()
        self._immediate_event = threading.Event()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._report_callbacks: list[Callable[[MaintenanceReport], None]] = []
        self._command_callbacks: list[Callable[[list[ActuatorCmd]], None]] = []

        self.stats = {
            "analyses_run": 0,
            "analyses_ok":  0,
            "analyses_err": 0,
            "last_risk":    "RISK_OK",
            "last_run_ts":  0,
        }

    def register_report_callback(self, fn: Callable[[MaintenanceReport], None]) -> None:
        self._report_callbacks.append(fn)

    def register_command_callback(self, fn: Callable[[list[ActuatorCmd]], None]) -> None:
        self._command_callbacks.append(fn)

    def on_twin_update(self, twin: TwinState) -> None:
        with self._history_lock:
            self._history.append(twin)

        if self._should_trigger_immediately(twin):
            log.info("Anlık LLM analizi tetiklendi: alarm_flags=%s", twin.alarm_flags)
            self._immediate_event.set()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._analysis_loop,
            name="MOD04-PredictiveEngine",
            daemon=True,
        )
        self._thread.start()
        log.info("MOD-04 başlatıldı (model=%s, periyot=%ss, geçmiş=%d snapshot).",
                 OLLAMA_MODEL, LLM_INTERVAL_S, LLM_HISTORY_LEN)

    def stop(self) -> None:
        self._running = False
        self._immediate_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=LLM_TIMEOUT_S + 5)
        log.info("MOD-04 durduruldu.")

    def _analysis_loop(self) -> None:
        while self._running:
            triggered = self._immediate_event.wait(timeout=LLM_INTERVAL_S)
            self._immediate_event.clear()

            if not self._running:
                break

            with self._history_lock:
                history_snapshot: list[TwinState] = list(self._history)

            if not history_snapshot:
                continue

            reason = "tetikleyici" if triggered else "periyodik"
            log.info("LLM analizi başlıyor (%s, %d snapshot).", reason, len(history_snapshot))

            self._run_analysis(history_snapshot)

    def _run_analysis(self, history: list[TwinState]) -> None:
        self.stats["analyses_run"] += 1
        latest = history[-1]

        try:
            user_prompt = build_user_prompt(history)
        except Exception as exc:
            log.error("Prompt oluşturulamadı: %s", exc)
            self.stats["analyses_err"] += 1
            return

        if _has_real_env_anomaly(latest):
            log.info("Öncelik Mantığı aktif: gerçek ortam anomalisi tespit edildi (%s).", latest.alarm_flags)

        try:
            raw_text = _call_ollama(user_prompt)
        except ValueError as exc:
            log.error("Ollama çağrısı başarısız: %s", exc)
            self.stats["analyses_err"] += 1
            return

        try:
            report = _parse_maintenance_report(raw_text, latest)
        except ValueError as exc:
            log.error("Rapor doğrulama hatası (%s). Ham yanıt: %.300s", exc, raw_text)
            self.stats["analyses_err"] += 1
            return

        self.stats["analyses_ok"]  += 1
        
        # BOMBA İMHA EDİLDİ: report.risk_level artık bir string olduğu için .value silindi!
        self.stats["last_risk"]    = report.risk_level
        self.stats["last_run_ts"]  = int(time.time() * 1000)

        log.info(
            "Rapor hazır: risk=%s, confidence=%.2f, komut_sayısı=%d, "
            "öngörülen_arıza=%s saat, anormallik=%s",
            report.risk_level, # <-- Buradan da .value silindi
            report.confidence,
            len(report.actuator_commands),
            report.predicted_failure_hrs,
            report.anomalies,
        )

        self._dispatch(report)

    def _dispatch(self, report: MaintenanceReport) -> None:
        for cb in self._report_callbacks:
            try:
                cb(report)
            except Exception as exc:
                log.error("report_callback hatası: %s", exc)

        if report.actuator_commands:
            for cb in self._command_callbacks:
                try:
                    cb(report.actuator_commands)
                except Exception as exc:
                    log.error("command_callback hatası: %s", exc)

    def _should_trigger_immediately(self, twin: TwinState) -> bool:
        warn_flags = ("RISK_WARN", "RISK_CRITICAL", "HIGH_CO2", "HIGH_TEMP", "SMOKE", "GAS_")
        return any(flag.upper().startswith(warn_flags) for flag in twin.alarm_flags)

    def get_stats(self) -> dict:
        return dict(self.stats)