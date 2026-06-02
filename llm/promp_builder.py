"""
prompt_builder.py  —  MOD-04
TwinState geçmişini Qwen 2.5 için hafifletilmiş ve İngilizce optimize prompt'a çevirir.
"""

import json
from typing import Sequence
from factory_types import TwinState

# ──────────────────────────────────────────────
# SYSTEM PROMPT  (İngilizce optimize, Türkçe çıktı garantili)
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are an Industrial IoT predictive maintenance AI.
Task: Analyze the provided sensor history and return ONLY a valid JSON backup report matching the schema below.

OUTPUT RULES:
- Return ONLY raw JSON. No explanations, no markdown blocks (```json), no extra text.
- Field names must strictly match the schema.
- risk_level values: "RISK_OK" | "RISK_WATCH" | "RISK_WARN" | "RISK_CRITICAL"
- confidence: float between 0.0 and 1.0
- recommended_action: Provide a short operator advice in TURKISH language.

JSON SCHEMA:
{
  "risk_level": "RISK_OK",
  "predicted_failure_hrs": null,
  "anomalies": ["string list"],
  "recommended_action": "Operatör için Türkçe öneri cümlesi",
  "confidence": 0.85,
  "actuator_commands": [
    {
      "zone_id": "ZONE_A",
      "device": "DEV_FAN",
      "value_pct": 50,
      "state": true,
      "source": "LLM"
    }
  ]
}

DECISION GUIDE:
- High Temp/Vibration: Turn ON Fan + Mist Maker.
- High CO2/Gas: Open Fan + Servo Vent, Turn OFF Mist Maker.
- Both: Gas problem has priority, ignore machine telemetry.
- No issue: return empty list for actuator_commands.
"""

# ──────────────────────────────────────────────
# SNAPSHOT → ÖZET DÖNÜŞTÜRÜCÜ
# ──────────────────────────────────────────────

def _snapshot_to_dict(twin: TwinState) -> dict:
    ambient_list = []
    for a in twin.ambient:
        ambient_list.append({
            "zone":        a.zone_id,
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
            "state":        twin.machine.state,
            "rpm":          round(twin.machine.rpm, 0),
            "vibration_g":  round(twin.machine.vibration_g, 2),
            "power_w":      round(twin.machine.power_w, 0),
            "machine_temp": round(twin.machine.machine_temp_c, 1),
            "output_units": twin.machine.output_units,
        },
        "alarms": twin.alarm_flags,
    }

# ──────────────────────────────────────────────
# ANA PROMPT OLUŞTURUCU (İngilizce Trend Notları)
# ──────────────────────────────────────────────

def build_user_prompt(history: Sequence[TwinState]) -> str:
    if not history:
        raise ValueError("Prompt oluşturmak için en az 1 snapshot gerekli.")

    snapshots = [_snapshot_to_dict(s) for s in history]

    # Trend tespiti (İngilizceye çevrildi)
    trend_notes = []
    if len(history) >= 2:
        first = history[0]
        last  = history[-1]

        dt_machine = last.machine.machine_temp_c - first.machine.machine_temp_c
        if abs(dt_machine) > 1.0:
            trend_notes.append(
                f"Machine temperature {'increased' if dt_machine > 0 else 'decreased'} "
                f"by {abs(dt_machine):.1f}°C over the last {len(history)*2} seconds."
            )

        dt_vib = last.machine.vibration_g - first.machine.vibration_g
        if abs(dt_vib) > 0.2:
            trend_notes.append(
                f"Vibration {'increased' if dt_vib > 0 else 'decreased'} by {abs(dt_vib):.2f}g."
            )

        for amb in last.ambient:
            for first_amb in first.ambient:
                if first_amb.zone_id == amb.zone_id:
                    dt_co2 = amb.co2_ppm - first_amb.co2_ppm
                    if abs(dt_co2) > 50:
                        trend_notes.append(
                            f"{amb.zone_id}: CO2 {'increased' if dt_co2 > 0 else 'decreased'} by {abs(dt_co2):.0f} ppm."
                        )

    trend_section = (
        "CALCULATED TRENDS:\n" + "\n".join(f"  - {t}" for t in trend_notes)
        if trend_notes
        else "CALCULATED TRENDS: No significant trend detected."
    )

    prompt = f"""{trend_section}

LAST {len(snapshots)} SNAPSHOT HISTORY (oldest → newest):
{json.dumps(snapshots, ensure_ascii=False, indent=2)}

Analyze the telemetry data above and return the required JSON backup report."""

    return prompt