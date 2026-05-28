"""
prompt_builder.py  —  MOD-04
TwinState geçmişini Qwen 2.5 3B için anlamlı bir prompt'a çevirir.

Tasarım ilkeleri:
  - LLM sadece JSON döndürür (başka hiçbir şey yok).
  - Son 30 snapshot (~60 sn geçmiş) context window'a girer.
  - Eşik tanımları ve örnek şema prompt'un içine gömülür.
  - Temperature=0.2 → neredeyse deterministik çıktı.
"""

import json
from typing import Sequence
from factory_types import TwinState, RiskLevel


# ──────────────────────────────────────────────
# EŞİK TANIMLARI  (MOD-03 kural motoruyla senkron tutulmalı)
# ──────────────────────────────────────────────

THRESHOLDS = {
    "temperature_c":  {"watch": 32.0, "warn": 38.0, "critical": 45.0},
    "humidity_pct":   {"watch": 70.0, "warn": 80.0, "critical": 90.0},
    "co2_ppm":        {"watch": 800,  "warn": 1000,  "critical": 1500},
    "pm25":           {"watch": 25.0, "warn": 50.0,  "critical": 75.0},
    "machine_temp_c": {"watch": 65.0, "warn": 80.0,  "critical": 95.0},
    "vibration_g":    {"watch": 2.5,  "warn": 4.0,   "critical": 6.0},
    "power_w":        {"watch": 400,  "warn": 500,   "critical": 600},
    "rpm":            {"warn_low": 800, "warn_high": 3200},
}

# ──────────────────────────────────────────────
# SYSTEM PROMPT  (bir kez oluşturulur, her istekte kullanılır)
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """Sen bir endüstriyel IoT fabrikasının kestirimci bakım yapay zekasısın.
Görevin: verilen sensör geçmişini analiz etmek ve aşağıdaki JSON şemasına uyan bir bakım raporu üretmek.

ÇIKTI KURALLARI:
- YALNIZCA geçerli JSON döndür. Açıklama, markdown, ```json bloğu veya başka hiçbir şey ekleme.
- Tüm alan adları tam olarak şemadaki gibi olmalı.
- risk_level: "RISK_OK" | "RISK_WATCH" | "RISK_WARN" | "RISK_CRITICAL"
- confidence: 0.0 ile 1.0 arasında ondalık sayı
- predicted_failure_hrs: sayı veya null

JSON ŞEMASI:
{
  "risk_level": "RISK_OK",
  "predicted_failure_hrs": null,
  "anomalies": ["string listesi"],
  "recommended_action": "operatöre yönelik Türkçe öneri",
  "confidence": 0.85,
  "actuator_commands": [
    {
      "zone_id": "ZONE_A" | "ZONE_B",
      "device": "DEV_FAN" | "DEV_SERVO_VENT" | "DEV_MIST_MAKER" | "DEV_BUZZER",
      "value_pct": 0-100,
      "state": true | false,
      "source": "LLM"
    }
  ]
}

EŞİK DEĞERLERİ:
""" + json.dumps(THRESHOLDS, ensure_ascii=False, indent=2) + """

KARAR REHBERİ:
- Makine sıcaklığı yükseliyor veya titreşim artıyorsa: Fan + Sis Üretici devreye al (soğutma modu).
- CO2 veya gaz eşiği aşılıyorsa: Fan + Servo havalandırma kapağı aç, Sis Üretici KAPAT.
- Hem gaz hem makine sorunu varsa: Gerçek ortam sorunu (gaz) önceliklidir, simülasyon verisini görmezden gel.
- Hiçbir sorun yoksa: actuator_commands boş liste döndür.
- Donanım müdahalesi yetersizse: actuator_commands boş bırak, recommended_action ile operatörü bildir.
"""


# ──────────────────────────────────────────────
# SNAPSHOT → ÖZET DÖNÜŞTÜRÜCÜ
# ──────────────────────────────────────────────

def _snapshot_to_dict(twin: TwinState) -> dict:
    """Bir TwinState nesnesini LLM'e beslenecek sözlüğe dönüştürür."""
    ambient_list = []
    for a in twin.ambient:
        ambient_list.append({
            "zone":        a.zone_id.value,
            "temp_c":      round(a.temperature_c, 1),
            "humidity":    round(a.humidity_pct, 1),
            "co2_ppm":     round(a.co2_ppm, 0),
            "pm25":        round(a.pm25, 1),
        })

    return {
        "version":      twin.snapshot_version,
        "ts_ms":        twin.updated_at,
        "ambient":      ambient_list,
        "machine": {
            "state":        twin.machine.state.value,
            "rpm":          round(twin.machine.rpm, 0),
            "vibration_g":  round(twin.machine.vibration_g, 2),
            "power_w":      round(twin.machine.power_w, 0),
            "machine_temp": round(twin.machine.machine_temp_c, 1),
            "output_units": twin.machine.output_units,
        },
        "alarms": twin.alarm_flags,
    }


# ──────────────────────────────────────────────
# ANA PROMPT OLUŞTURUCU
# ──────────────────────────────────────────────

def build_user_prompt(history: Sequence[TwinState]) -> str:
    """
    Son N snapshot'ı alır, kullanıcı mesajını oluşturur.
    history[0] = en eski, history[-1] = en yeni snapshot.
    """
    if not history:
        raise ValueError("Prompt oluşturmak için en az 1 snapshot gerekli.")

    snapshots = [_snapshot_to_dict(s) for s in history]

    # Trend tespiti: ilk ve son değerleri karşılaştır
    trend_notes = []
    if len(history) >= 2:
        first = history[0]
        last  = history[-1]

        dt_machine = last.machine.machine_temp_c - first.machine.machine_temp_c
        if abs(dt_machine) > 1.0:
            trend_notes.append(
                f"Makine sıcaklığı {abs(dt_machine):.1f}°C "
                f"{'arttı' if dt_machine > 0 else 'azaldı'} "
                f"(son {len(history)*2} saniye)."
            )

        dt_vib = last.machine.vibration_g - first.machine.vibration_g
        if abs(dt_vib) > 0.2:
            trend_notes.append(
                f"Titreşim {abs(dt_vib):.2f}g "
                f"{'arttı' if dt_vib > 0 else 'azaldı'}."
            )

        for amb in last.ambient:
            for first_amb in first.ambient:
                if first_amb.zone_id == amb.zone_id:
                    dt_co2 = amb.co2_ppm - first_amb.co2_ppm
                    if abs(dt_co2) > 50:
                        trend_notes.append(
                            f"{amb.zone_id.value}: CO2 {abs(dt_co2):.0f} ppm "
                            f"{'arttı' if dt_co2 > 0 else 'azaldı'}."
                        )

    trend_section = (
        "HESAPLANAN TRENDLER:\n" + "\n".join(f"  - {t}" for t in trend_notes)
        if trend_notes
        else "HESAPLANAN TRENDLER: Belirgin trend yok."
    )

    prompt = f"""{trend_section}

SON {len(snapshots)} SNAPSHOT GEÇMİŞİ (en eski → en yeni):
{json.dumps(snapshots, ensure_ascii=False, indent=2)}

Yukarıdaki verileri analiz et ve JSON bakım raporunu döndür."""

    return prompt