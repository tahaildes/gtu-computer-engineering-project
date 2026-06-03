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

SYSTEM_PROMPT = """You are a sensor data analyzer.
Analyze the telemetry and return ONLY a JSON with anomalies list.
Return short anomaly keywords like: "high_vibration", "rpm_dropping", "co2_rising", "temp_stable"
If everything is normal, return empty list.

OUTPUT FORMAT (nothing else):
{"anomalies": ["keyword1", "keyword2"]}
"""
# ──────────────────────────────────────────────
# SNAPSHOT → ÖZET DÖNÜŞTÜRÜCÜ
# ──────────────────────────────────────────────

def _snapshot_to_dict(twin: TwinState) -> dict:
    ambient_list = []
    for a in twin.ambient:
        ambient_list.append({
            "zone":     a.zone_id,
            "temp_c":   round(a.temperature_c or 0.0, 1),
            "humidity": round(a.humidity_pct   or 0.0, 1),
            "co2_ppm":  round(a.co2_ppm        or 0.0, 0),
            "pm25":     round(a.pm25            or 0.0, 1),
        })

    return {
        "version": twin.snapshot_version,
        "ts_ms":   twin.updated_at,
        "ambient": ambient_list,
        "machine": {
            "state":        twin.machine.state,
            "rpm":          round(twin.machine.rpm            or 0.0, 0),
            "vibration_g":  round(twin.machine.vibration_g    or 0.0, 2),
            "power_w":      round(twin.machine.power_w        or 0.0, 0),
            "machine_temp": round(twin.machine.machine_temp_c or 0.0, 1),
            "output_units": twin.machine.output_units or 0,
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
        
        dt_machine = (last.machine.machine_temp_c or 0.0) - (first.machine.machine_temp_c or 0.0)
        if abs(dt_machine) > 1.0:
            trend_notes.append(
                f"Machine temperature {'increased' if dt_machine > 0 else 'decreased'} "
                f"by {abs(dt_machine):.1f}°C over the last {len(history)*2} seconds."
            )

        dt_vib = (last.machine.vibration_g    or 0.0) - (first.machine.vibration_g    or 0.0)
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