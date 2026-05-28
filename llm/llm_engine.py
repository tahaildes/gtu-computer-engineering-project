"""
llm_engine.py  —  MOD-04
Bilişsel Kestirimci Motor: LLM tabanlı anomali tespiti ve kestirimci bakım.

Sorumluluklar:
  1. MOD-03'ten TwinState callback'i alır; 30 snapshot'lık geçmiş tutar.
  2. Her 60 saniyede bir VEYA yeni snapshot'ta RISK_WARN / RISK_CRITICAL
     tespit edildiğinde Qwen 2.5 3B'yi anında çalıştırır.
  3. LLM çıktısını doğrular → MaintenanceReport'a dönüştürür.
  4. Sabit kodlu karar tablosundan geçen aktüatör komutlarını MOD-03'e iletir.
  5. Öncelik mantığı: gerçek ortam anomalileri (MOD-01) makine simülasyonunu
     (MOD-02) gölgeler.

Bağımlılıklar:
  pip install requests
  Ollama servisi 127.0.0.1:11434'te çalışıyor olmalı.
"""

from __future__ import annotations
import google.generativeai as genai

import json
import logging
import threading
import time
from collections import deque
from enum import Enum
from typing import Callable, Optional, Sequence

import requests
genai.configure(api_key="BURAYA_API_ANAHTARINI_YAZ")

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

OLLAMA_URL        = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL      = "qwen2.5:3b"
LLM_TEMPERATURE   = 0.2
LLM_HISTORY_LEN   = 30           # Context'e girecek maksimum snapshot sayısı (~60 sn)
LLM_INTERVAL_S    = 60.0         # Planlı analiz periyodu (saniye)
LLM_TIMEOUT_S     = 90           # Ollama yanıt zaman aşımı
IMMEDIATE_LEVELS  = {RiskLevel.RISK_WARN, RiskLevel.RISK_CRITICAL}

# Ortam anomalisini işaret eden alarm bayrak önekleri
ENV_ALARM_PREFIXES = ("HIGH_CO2", "HIGH_GAS", "HIGH_TEMP", "HIGH_HUMIDITY",
                      "HIGH_PM25", "SMOKE", "GAS_")

log = logging.getLogger("MOD04")


# ──────────────────────────────────────────────
# HATA KODLARI
# ──────────────────────────────────────────────

class LLMError(str, Enum):
    LLM_ERR_VALIDATION = "LLM_ERR_VALIDATION"   # JSON geçersiz veya şema hatası
    LLM_ERR_TIMEOUT    = "LLM_ERR_TIMEOUT"       # Ollama yanıt vermedi
    LLM_ERR_TRANSPORT  = "LLM_ERR_TRANSPORT"     # HTTP / ağ hatası
    LLM_ERR_EMPTY      = "LLM_ERR_EMPTY"         # Boş yanıt


# ──────────────────────────────────────────────
# KARAR TABLOSU
# ──────────────────────────────────────────────

def _has_real_env_anomaly(twin: TwinState) -> bool:
    """
    MOD-01 (gerçek sensör) kaynaklı ortam anomalisi var mı?
    alarm_flags içinde ENV_ALARM_PREFIXES'ten biriyle başlayan bayrak yeterledir.
    """
    return any(
        flag.upper().startswith(ENV_ALARM_PREFIXES)
        for flag in twin.alarm_flags
    )


def _validate_and_filter_commands(
    raw_cmds: list[ActuatorCmd],
    latest_twin: TwinState,
) -> list[ActuatorCmd]:
    """
    LLM'in önerdiği aktüatör komutlarını sabit kodlu karar tablosundan geçirir.

    Karar Tablosu (şartname §3.4 ve §6):
      • Gerçek ortam anomalisi (gaz / CO2) varsa:
            Fan AÇIK + Servo havalandırma AÇIK, Sis Üretici KAPALI zorunlu.
      • Yalnızca makine sorunu (simülasyon) varsa:
            Fan + Sis Üretici AÇIK kabul (soğutma modu).
      • Sorun yok (RISK_OK):
            Boş liste; ısrar eden komutlar reddedilir.
      • Genel kural:
            source alanı her zaman LLM olmalı; başka kaynaklı komutlar reddedilir.

    Güvenlik: Bu fonksiyon LLM kararlarını SINIRLAR, yerine koymaz.
    """
    env_anomaly = _has_real_env_anomaly(latest_twin)
    filtered: list[ActuatorCmd] = []

    for cmd in raw_cmds:
        # Kaynak kontrolü — başka modülden gelen komut reddedilir
        if cmd.source != ActuatorSource.LLM:
            log.warning("Komut reddedildi: source=%s (LLM bekleniyor).", cmd.source)
            continue

        # value_pct aralık kontrolü
        if not (0.0 <= cmd.value_pct <= 100.0):
            log.warning("Komut reddedildi: value_pct=%.1f aralık dışı.", cmd.value_pct)
            continue

        # Ortam anomalisi öncelik mantığı (Priority Logic §4.4.1)
        if env_anomaly and cmd.device == DeviceType.DEV_MIST_MAKER and cmd.state:
            log.info(
                "Sis Üretici komutu devre dışı bırakıldı: "
                "gerçek ortam anomalisi (gaz/CO2) — yalnızca havalandırma modu."
            )
            # Kapama komutuna çevir
            cmd = ActuatorCmd(
                zone_id=cmd.zone_id,
                device=DeviceType.DEV_MIST_MAKER,
                value_pct=0.0,
                state=False,
                source=ActuatorSource.LLM,
            )

        filtered.append(cmd)

    return filtered


# ──────────────────────────────────────────────
# LLM ÇAĞRISI
# ──────────────────────────────────────────────
def _call_ollama(user_prompt: str) -> str:
    """
    Geçici olarak Ollama yerine Gemini API / AI Studio kullanır.
    Döndürür: ham LLM metin yanıtı.
    """
    try:
        # Modeli System Prompt ve Temperature=0.2 ile yapılandırıyoruz
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
            )
        )
        
        # İstek atıyoruz
        response = model.generate_content(user_prompt)
        raw_text = response.text.strip()
        
        if not raw_text:
            raise ValueError(LLMError.LLM_ERR_EMPTY)
            
        return raw_text

    except Exception as exc:
        log.error("Gemini API çağrısı başarısız: %s", exc)
        raise ValueError(LLMError.LLM_ERR_TRANSPORT) from exc

# ──────────────────────────────────────────────
# JSON DOĞRULAMA VE DÖNÜŞTÜRME
# ──────────────────────────────────────────────

def _parse_maintenance_report(
    raw_text: str,
    latest_twin: TwinState,
) -> MaintenanceReport:
    """
    LLM ham metnini MaintenanceReport'a dönüştürür.
    Şema veya enum hatası → LLM_ERR_VALIDATION fırlatır.
    """
    # ```json ... ``` bloklarını temizle (LLM bazen ekler)
    clean = raw_text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        # İlk ve son fence satırlarını çıkar
        clean = "\n".join(
            ln for ln in lines
            if not ln.strip().startswith("```")
        ).strip()

    try:
        data: dict = json.loads(clean)
    except json.JSONDecodeError as exc:
        log.error("JSON parse hatası: %s | Ham: %.200s", exc, raw_text)
        raise ValueError(LLMError.LLM_ERR_VALIDATION) from exc

    # Zorunlu alan kontrolleri
    required = {
        "risk_level", "predicted_failure_hrs",
        "anomalies", "recommended_action",
        "confidence", "actuator_commands",
    }
    missing = required - data.keys()
    if missing:
        log.error("Eksik alanlar: %s", missing)
        raise ValueError(LLMError.LLM_ERR_VALIDATION)

    # risk_level enum doğrulama
    try:
        risk_level = RiskLevel(data["risk_level"])
    except ValueError:
        log.error("Geçersiz risk_level: %s", data["risk_level"])
        raise ValueError(LLMError.LLM_ERR_VALIDATION)

    # confidence aralık kontrolü
    try:
        confidence = float(data["confidence"])
        if not (0.0 <= confidence <= 1.0):
            raise ValueError
    except (TypeError, ValueError):
        log.error("Geçersiz confidence: %s", data["confidence"])
        raise ValueError(LLMError.LLM_ERR_VALIDATION)

    # Aktüatör komutlarını dönüştür
    raw_cmds: list[ActuatorCmd] = []
    for idx, item in enumerate(data.get("actuator_commands", [])):
        try:
            cmd = ActuatorCmd(
                zone_id=ZoneId(item["zone_id"]),
                device=DeviceType(item["device"]),
                value_pct=float(item["value_pct"]),
                state=bool(item["state"]),
                source=ActuatorSource.LLM,   # source alanı her zaman LLM'dir
            )
            raw_cmds.append(cmd)
        except (KeyError, ValueError) as exc:
            log.warning("Komut #%d atlandı (hatalı şema): %s", idx, exc)

    # Karar tablosundan geçir
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
    """
    MOD-04 Bilişsel Kestirimci Motor.

    Kullanım:
        engine = PredictiveEngine()
        engine.register_report_callback(on_new_report)   # MOD-05 için
        engine.register_command_callback(on_new_cmds)    # MOD-03 → MQTT
        engine.start()

        # MOD-03 her twin güncellemesinde şunu çağırır:
        engine.on_twin_update(twin_state)

        engine.stop()
    """

    def __init__(self) -> None:
        self._history: deque[TwinState] = deque(maxlen=LLM_HISTORY_LEN)
        self._history_lock = threading.Lock()

        # Anlık tetikleme mekanizması
        self._immediate_event = threading.Event()

        # Çalışma bayrağı
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Kayıtlı callback'ler
        self._report_callbacks: list[Callable[[MaintenanceReport], None]] = []
        self._command_callbacks: list[Callable[[list[ActuatorCmd]], None]] = []

        # İstatistikler (basit sayaçlar)
        self.stats = {
            "analyses_run": 0,
            "analyses_ok":  0,
            "analyses_err": 0,
            "last_risk":    RiskLevel.RISK_OK.value,
            "last_run_ts":  0,
        }

    # ── Callback kayıt ──────────────────────────────

    def register_report_callback(
        self, fn: Callable[[MaintenanceReport], None]
    ) -> None:
        """Yeni MaintenanceReport üretildiğinde çağrılacak fonksiyonu kaydeder."""
        self._report_callbacks.append(fn)

    def register_command_callback(
        self, fn: Callable[[list[ActuatorCmd]], None]
    ) -> None:
        """Aktüatör komutları hazır olduğunda çağrılacak fonksiyonu kaydeder."""
        self._command_callbacks.append(fn)

    # ── MOD-03 Arayüzü ──────────────────────────────

    def on_twin_update(self, twin: TwinState) -> None:
        """
        MOD-03 tarafından her 2 saniyede bir çağrılır.
        Snapshot geçmişe eklenir; RISK_WARN/RISK_CRITICAL'da anında analiz tetiklenir.
        """
        with self._history_lock:
            self._history.append(twin)

        # Kural motorundan gelen alarm bayrakları üzerinden risk tespiti
        if self._should_trigger_immediately(twin):
            log.info(
                "Anlık LLM analizi tetiklendi: alarm_flags=%s", twin.alarm_flags
            )
            self._immediate_event.set()

    # ── Başlat / Durdur ─────────────────────────────

    def start(self) -> None:
        """Analiz thread'ini başlatır."""
        if self._running:
            log.warning("PredictiveEngine zaten çalışıyor.")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._analysis_loop,
            name="MOD04-PredictiveEngine",
            daemon=True,
        )
        self._thread.start()
        log.info(
            "MOD-04 başlatıldı (model=%s, periyot=%ss, geçmiş=%d snapshot).",
            OLLAMA_MODEL, LLM_INTERVAL_S, LLM_HISTORY_LEN,
        )

    def stop(self) -> None:
        """Analiz thread'ini düzgünce durdurur."""
        self._running = False
        self._immediate_event.set()   # Bekleme döngüsünden çık
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=LLM_TIMEOUT_S + 5)
        log.info("MOD-04 durduruldu.")

    # ── İç Analiz Döngüsü ───────────────────────────

    def _analysis_loop(self) -> None:
        """
        Thread gövdesi.
        Her LLM_INTERVAL_S saniyede bir veya _immediate_event set edildiğinde
        LLM analizini çalıştırır.
        """
        while self._running:
            triggered = self._immediate_event.wait(timeout=LLM_INTERVAL_S)
            self._immediate_event.clear()

            if not self._running:
                break

            with self._history_lock:
                history_snapshot: list[TwinState] = list(self._history)

            if not history_snapshot:
                log.debug("Analiz atlandı: henüz snapshot yok.")
                continue

            reason = "tetikleyici" if triggered else "periyodik"
            log.info("LLM analizi başlıyor (%s, %d snapshot).", reason, len(history_snapshot))

            self._run_analysis(history_snapshot)

    def _run_analysis(self, history: list[TwinState]) -> None:
        """
        Prompt oluşturur → LLM çağırır → raporu doğrular → callback'leri tetikler.
        """
        self.stats["analyses_run"] += 1
        latest = history[-1]

        try:
            user_prompt = build_user_prompt(history)
        except Exception as exc:
            log.error("Prompt oluşturulamadı: %s", exc)
            self.stats["analyses_err"] += 1
            return

        # Öncelik mantığı logu: gerçek ortam sorunu var mı?
        if _has_real_env_anomaly(latest):
            log.info(
                "Öncelik Mantığı aktif: gerçek ortam anomalisi tespit edildi "
                "(%s). Makine simülasyon verileri arka plana alındı.",
                latest.alarm_flags,
            )

        try:
            raw_text = _call_ollama(user_prompt)
        except ValueError as exc:
            err_code = str(exc)
            log.error("Ollama çağrısı başarısız: %s", err_code)
            self.stats["analyses_err"] += 1
            return

        try:
            report = _parse_maintenance_report(raw_text, latest)
        except ValueError as exc:
            err_code = str(exc)
            log.error(
                "Rapor doğrulama hatası (%s). Ham yanıt: %.300s", err_code, raw_text
            )
            self.stats["analyses_err"] += 1
            return

        # Başarılı analiz
        self.stats["analyses_ok"]  += 1
        self.stats["last_risk"]    = report.risk_level.value
        self.stats["last_run_ts"]  = int(time.time() * 1000)

        log.info(
            "Rapor hazır: risk=%s, confidence=%.2f, komut_sayısı=%d, "
            "öngörülen_arıza=%s saat, anormallik=%s",
            report.risk_level.value,
            report.confidence,
            len(report.actuator_commands),
            report.predicted_failure_hrs,
            report.anomalies,
        )

        self._dispatch(report)

    # ── Dispatch ────────────────────────────────────

    def _dispatch(self, report: MaintenanceReport) -> None:
        """Raporu ve komutları kayıtlı callback'lere iletir."""
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

    # ── Yardımcı ────────────────────────────────────

    def _should_trigger_immediately(self, twin: TwinState) -> bool:
        """
        Yeni snapshot'ın anlık analizi tetikleyip tetiklemeyeceğini belirler.
        RISK_WARN veya RISK_CRITICAL alarm bayrağı içeriyorsa True.
        """
        warn_flags = ("RISK_WARN", "RISK_CRITICAL",
                      "HIGH_CO2", "HIGH_TEMP", "SMOKE", "GAS_")
        return any(
            flag.upper().startswith(warn_flags)
            for flag in twin.alarm_flags
        )

    def get_stats(self) -> dict:
        """Basit durum istatistiklerini döndürür (MOD-05 / dashboard için)."""
        return dict(self.stats)