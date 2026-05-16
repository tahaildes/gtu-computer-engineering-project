# MOD-03 — Digital Twin Core

## Modül Amacı
[cite_start]MOD-03, fabrikanın merkezi veri yönetim birimidir[cite: 119]. [cite_start]Tüm MQTT sensör verilerini toplar, SQLite veritabanına kaydeder ve fabrikanın anlık sanal kopyasını (Digital Twin) oluşturur[cite: 119]. [cite_start]Ayrıca, LLM'den bağımsız çalışan kural tabanlı bir acil durum güvenlik mekanizmasına sahiptir[cite: 120].

## Yazarlar
* [cite_start]Taha Emirhan İldeş (240104004995) [cite: 117]
* [cite_start]Yunus Emre Manav (210104004024) [cite: 117]

## Bağımlılıklar
* [cite_start]**Platform:** Python 3.10+ / Raspberry Pi 4 [cite: 116]
* [cite_start]**Kütüphaneler:** `paho-mqtt`, `sqlite3`, `asyncio` [cite: 116]
* [cite_start]**Veri Yapıları:** `factory_types.h` (Dataclass olarak yansıtılmıştır) [cite: 44]

## API Özeti
| Fonksiyon | Parametreler | Dönüş Değeri | Açıklama |
| :--- | :--- | :--- | :--- |
| `twin_init` | `void` | `twin_status_t` | [cite_start]DB ve MQTT bağlantılarını hazırlar[cite: 119]. |
| `twin_register_update_callback` | `twin_state_cb_t` | `void` | [cite_start]Yeni snapshot oluştuğunda MOD-04'ü tetikler[cite: 64]. |
| `twin_update_ambient` | `zone_id_t, snapshot` | `void` | [cite_start]Bölgesel ortam verisini ikize işler[cite: 61]. |
| `twin_get_state` | `twin_state_t*` | `twin_status_t` | [cite_start]Mevcut en güncel fabrika durumunu döndürür. |
| `twin_trigger_emergency` | `twin_state_t*` | `void` | [cite_start]Güvenlik eşiklerini kontrol eder ve bypass yapar[cite: 56]. |

## Entegrasyon Örneği
Aşağıdaki Pythonic mantığı temsil eden sözde kod, modülün işleyişini gösterir:

```python
# MOD-03 Başlatma ve Callback Kaydı
def on_new_state(state):
    print(f"Versiyon {state.snapshot_version} hazır. Analiz ediliyor...")

twin_init()
twin_register_update_callback(on_new_state)

# Gelen veriyi işleme (MQTT callback içinde)
new_reading = ambient_snapshot_t(temperature_c=28.5, ...)
twin_update_ambient(ZONE_A, new_reading)