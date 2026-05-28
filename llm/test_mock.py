"""
test_mock.py — MOD-04 Test Ortamı
Donanım olmadan yapay zeka motorunu (llm_engine.py) test etmek için sahte veriler üretir.
"""

import time
import logging
from factory_types import TwinState, AmbientSnapshot, MachineSnapshot, ActuatorCmd, MaintenanceReport
from llm_engine import PredictiveEngine

# Loglama ayarlarını yapalım ki ekranda ne olup bittiğini görelim
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# ──────────────────────────────────────────────
# 1. SAHTE VERİ ÜRETİCİLERİ (MOCK DATA)
# ──────────────────────────────────────────────

def create_mock_snapshot(version: int, temp_c: float, vibration_g: float, alarm: str = "") -> TwinState:
    """Belirli sıcaklık ve titreşim değerleriyle tek bir anlık fabrika durumu (snapshot) oluşturur."""
    now = int(time.time() * 1000)
    
    ambient = [
        AmbientSnapshot(zone_id="ZONE_A", temperature_c=24.5, humidity_pct=50.0, co2_ppm=400, pm25=10.0, timestamp_ms=now),
        AmbientSnapshot(zone_id="ZONE_B", temperature_c=25.0, humidity_pct=52.0, co2_ppm=410, pm25=12.0, timestamp_ms=now)
    ]
    
    machine = MachineSnapshot(
        rpm=1400, 
        vibration_g=vibration_g, 
        power_w=750, 
        machine_temp_c=temp_c, 
        output_units=100, 
        state="NORMAL", 
        timestamp_ms=now
    )
    
    alarms = [alarm] if alarm else []
    
    return TwinState(
        ambient=ambient,
        machine=machine,
        alarm_flags=alarms,
        snapshot_version=version,
        updated_at=now
    )

# ──────────────────────────────────────────────
# 2. CALLBACK FONKSİYONLARI (LLM'den dönen cevabı yakalayacak)
# ──────────────────────────────────────────────

def on_report_ready(report: MaintenanceReport):
    print("\n" + "="*50)
    print("🎯 YENİ BAKIM RAPORU GELDİ!")
    print("="*50)
    print(f"Risk Seviyesi   : {report.risk_level}")
    print(f"Güven Skoru     : % {report.confidence * 100:.0f}")
    print(f"Kalan Süre (Tahmin): {report.predicted_failure_hrs} saat")
    print(f"Anomaliler      : {', '.join(report.anomalies)}")
    print(f"Öneri           : {report.recommended_action}")
    print("="*50 + "\n")

def on_commands_ready(cmds: list[ActuatorCmd]):
    print("⚙️  DONANIM KOMUTLARI:")
    for cmd in cmds:
        durum = "AÇIK" if cmd.state else "KAPALI"
        print(f"   -> {cmd.device} ({cmd.zone_id}): %{cmd.value_pct} - {durum} [Kaynak: {cmd.source}]")
    print("-" * 50 + "\n")

# ──────────────────────────────────────────────
# 3. TEST SENARYOSU
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 MOD-04 Kestirimci Motor Testi Başlıyor...\n")
    
    # Motoru başlatalım
    engine = PredictiveEngine()
    engine.register_report_callback(on_report_ready)
    engine.register_command_callback(on_commands_ready)
    engine.start()

    # Senaryo: Sıcaklık ve titreşim yavaş yavaş artıyor
    print("Veriler akmaya başladı (3 saniye arayla)...")
    
    try:
        # Snapshot 1: Her şey normal
        s1 = create_mock_snapshot(version=1, temp_c=40.0, vibration_g=0.5)
        engine.on_twin_update(s1)
        time.sleep(3)

        # Snapshot 2: Sıcaklık biraz artıyor
        s2 = create_mock_snapshot(version=2, temp_c=55.0, vibration_g=1.2)
        engine.on_twin_update(s2)
        time.sleep(3)

        # Snapshot 3: Sıcaklık kritik seviyeye çıkıyor ve alarm tetikleniyor!
        # RISK_WARN alarmı, LLM'in beklemeden hemen analiz yapmasını sağlayacak.
        s3 = create_mock_snapshot(version=3, temp_c=85.0, vibration_g=3.5, alarm="RISK_WARN")
        engine.on_twin_update(s3)
        
        # LLM'in düşünmesi ve raporu döndürmesi için biraz bekleyelim
        print("\nLLM düşünmeye başladı, rapor bekleniyor...")
        time.sleep(15) 

    except KeyboardInterrupt:
        print("\nTest iptal edildi.")
    finally:
        engine.stop()
        print("Test bitti.")