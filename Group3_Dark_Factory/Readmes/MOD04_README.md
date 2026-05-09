# MOD-04 — Bilişsel Kestirimci Motor

## Modül Amacı
MOD-04, sistemin yapay zeka katmanıdır. Raspberry Pi üzerinde yerel (local) olarak çalışan Qwen 2.5 3B modelini kullanarak, dijital ikiz verileri üzerinden anomali tespiti ve kestirimci bakım (predictive maintenance) raporları üretir.

## Yazarlar
* Ahmet Burak Çelebi (220104004885)
* Burak Kurtaran (210104004240)

## Bağımlılıklar
* **Platform:** Python 3.10+ / Raspberry Pi 4 (4GB RAM)
* **Yapay Zeka:** Ollama / Qwen 2.5 3B (qwen2.5:3b)
* **Parametreler:** Temperature = 0.2 (Deterministik çıktılar için)
* **Dosyalar:** `factory_types.h`

## API Özeti
| Fonksiyon | Parametreler | Dönüş Değeri | Açıklama |
| :--- | :--- | :--- | :--- |
| `llm_engine_init` | `void` | `llm_status_t` | Ollama servisini ve modeli hazırlar. |
| `llm_analyze_state` | `snapshot, report*` | `llm_status_t` | LLM çıkarım sürecini yönetir. |
| `llm_check_priority_logic` | `snapshot` | `uint8_t` | Gerçek veri vs Simülasyon önceliğini yönetir. |
| `llm_validate_output` | `char*` | `llm_status_t` | Model çıktısının JSON şemasına uygunluğunu kontrol eder. |

## Entegrasyon Örneği (Python/Ollama)
```python
# MOD-04 Prompt Stratejisi
context = get_last_30_snapshots()
prompt = f"Analyze the following factory data and return JSON: {context}"

# Ollama HTTP API üzerinden çağrı
response = requests.post("http://localhost:11434/api/generate", json={
    "model": "qwen2.5:3b",
    "prompt": prompt,
    "stream": False,
    "options": {"temperature": 0.2}
})