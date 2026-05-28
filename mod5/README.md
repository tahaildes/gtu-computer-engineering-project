# MOD-05 — Endüstriyel API & Dashboard

> **Dark Factory** projesinin dış arayüz katmanı.  
> FastAPI + WebSocket backend, React frontend dashboard.

---

## Sistem İçindeki Yeri

```
[ESP32 #1]  ──┐
               │  MQTT (Wi-Fi / JSON)
[ESP32 #2]  ──┤
               ▼
          [ MOD-03 ]  ←──── Sensör verilerini alır, SQLite'a yazar
               │             twin_state'i günceller
               │  Python callback (her 2 saniyede)
               ▼
          [ MOD-04 ]  ←──── LLM (Qwen 2.5 3B / Ollama) analiz eder
               │             bakım raporu üretir
               │  on_snapshot_push()
               ▼
         [ MOD-05 ]  ←──── BU MODÜL
          │       │
          │       └──  WebSocket /ws  ──►  React Dashboard (Tarayıcı)
          │
          └── REST API :8000
```

**Özet akış:**
1. ESP32'ler JSON ölçüm paketlerini MQTT üzerinden Raspberry Pi'ye gönderir
2. MOD-03 bu paketleri alır, SQLite'a yazar ve twin_state'i günceller
3. Her 2 saniyede `on_snapshot_push()` çağrılır → MOD-05'e gelir
4. MOD-05 bu snapshot'ı bağlı tüm tarayıcılara WebSocket ile push eder
5. Tarayıcı sayfayı yenilemeden canlı veri görür

---

## REST API Endpointleri

Tüm endpointler `http://<raspberry-pi-ip>:8000` altında çalışır.

### `GET /`
Servis sağlık kontrolü.

```json
{ "status": "Dark Factory API çalışıyor" }
```

---

### `GET /twin`
Fabrikanın anlık dijital ikiz snapshot'ını döner.  
Sayfa ilk yüklendiğinde WebSocket bağlanmadan önce initial state almak için kullanılır.

```json
{
  "version": 42,
  "updated_at": 1711630800000,
  "zones": {
    "zone_a": { "temperature_c": 36.4, "humidity_pct": 58, "co2_ppm": 420, "alarm": "OK" },
    "machine": { "state": "NORMAL", "rpm": 1457, "vibration_g": 0.28, "pressure_bar": 8.12 }
  }
}
```

---

### `GET /report`
MOD-04'ün ürettiği son LLM bakım raporunu döner.

```json
{
  "risk_level": "RISK_WATCH",
  "predicted_failure_hrs": 18,
  "recommended_action": "Fan devri artırılmalı, rulman kontrolü yapılmalı."
}
```

---

### `GET /history?limit=50`
SQLite'taki sensör geçmişini döner. `limit` parametresiyle kaç kayıt isteneceği belirtilir (varsayılan: 50).  
Grafiklerin geçmiş veriyle dolu başlaması için kullanılır.

```json
[
  { "zone_id": "zone_a", "sensor_type": "temperature_c", "value": 36.4, "unit": "°C", "timestamp_ms": 1711630800000 },
  { "zone_id": "machine", "sensor_type": "rpm",           "value": 1457, "unit": "rpm", "timestamp_ms": 1711630798000 }
]
```

---

### `GET /reports?limit=10`
SQLite'taki LLM bakım raporu geçmişini döner.  
Son N raporu listelemek, haftalık risk trendini görmek için kullanılır.

```json
[
  { "report": { "risk_level": "RISK_CRITICAL", ... }, "created_at": 1711630700000 },
  { "report": { "risk_level": "RISK_WATCH",    ... }, "created_at": 1711630400000 }
]
```

---

### `POST /actuator/cmd`
Dashboard üzerindeki manuel kontrol panelinden donanımları tetikler.  
MOD-03 → MQTT → ESP32 zinciriyle fiziksel cihaza ulaşır.

**Request body:**
```json
{
  "zone_id":     "zone_a",
  "device_type": "DEV_FAN",
  "value_pct":   80.0
}
```

| Alan | Tip | Açıklama |
|---|---|---|
| `zone_id` | string | `zone_a` veya `zone_b` |
| `device_type` | string | `DEV_FAN`, `DEV_SERVO_VENT`, `DEV_MIST_MAKER`, `DEV_BUZZER` |
| `value_pct` | float (0–100) | Cihazın çalışma yüzdesi |

**Response:**
```json
{ "status": "ok", "cmd": { ... } }
```

---

### `WebSocket /ws`
Gerçek zamanlı veri akışı. Bağlı kaldığı sürece her ~2 saniyede push gelir.

**Gelen mesaj formatı:**
```json
{
  "type": "snapshot",
  "snapshot": { "version": 42, "zones": { ... } },
  "report":   { "risk_level": "RISK_OK", ... }
}
```

---

## Kurulum

```bash
pip install fastapi uvicorn pydantic
python main.py   # MOD-03, MOD-04, MOD-05 birlikte başlar
```

API: `http://0.0.0.0:8000`  
Swagger docs: `http://0.0.0.0:8000/docs`

---

## Dosyalar

| Dosya | Açıklama |
|---|---|
| `mod05_api.py` | Bu modül — FastAPI + WebSocket |
| `mod03_twin.py` | Dijital ikiz çekirdeği, SQLite yazımı |
| `mod04_cognitive.py` | LLM analiz motoru |
| `main.py` | Tüm modülleri başlatan giriş noktası |
| `Dark_Factory_Live.html` | React dashboard (tek HTML dosyası) |

---

*GTU CSE 396 — Dark Factory Projesi*
