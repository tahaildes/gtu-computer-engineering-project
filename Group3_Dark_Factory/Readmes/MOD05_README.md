# MOD-05 — Endüstriyel API ve Dashboard

## Modül Amacı
[cite_start]MOD-05, karanlık fabrika sisteminin dış arayüz katmanıdır[cite: 139]. [cite_start]FastAPI tabanlı bir REST ve WebSocket arka ucu (Backend) ile gerçek zamanlı fabrika telemetrisini, dijital ikiz durumunu ve LLM bakım raporlarını React tabanlı bir web paneline (Dashboard) sunar[cite: 139]. [cite_start]Ayrıca operatörün LLM'i devre dışı bırakarak donanımları manuel olarak kontrol etmesine olanak tanır[cite: 141].

## Yazarlar
* Dark Factory Core Team (Tüm Ekip Entegrasyonu)

## Bağımlılıklar
* [cite_start]**Arka Uç (Backend):** Python 3.10+, FastAPI, Uvicorn, SQLite[cite: 136].
* [cite_start]**Ön Uç (Frontend):** React 18, Vite, TypeScript[cite: 136].
* [cite_start]**Portlar:** API: 8000 (HTTP/WS), React Dev: 5173 (Vite)[cite: 137].
* **Dosyalar:** `factory_types.h` (REST Payload'ları için referans alınmıştır).

## API Özeti
| Fonksiyon / Uç Nokta (Endpoint) | Parametreler | Dönüş Değeri | Açıklama |
| :--- | :--- | :--- | :--- |
| `api_server_init` | `void` | `api_status_t` | FastAPI ve WebSocket sunucusunu başlatır. |
| `api_broadcast_state` | `twin_state_t*` | `api_status_t` | Dijital ikiz güncellemelerini UI'a (Kullanıcı Arayüzü) canlı yayınlar. |
| `api_broadcast_llm_report` | `maintenance_report_t*` | `api_status_t` | LLM düşünce sürecini (Thought Process) canlı olarak yansıtır. |
| `api_handle_manual_override` | `actuator_cmd_t*` | `api_status_t` | `POST /actuator/cmd` üzerinden gelen manuel donanım komutlarını işler. |

## Entegrasyon Örneği (FastAPI Sözde Kodu)
Aşağıdaki örnek, FastAPI üzerinde bir WebSocket bağlantısının nasıl kurulduğunu ve manuel kontrol komutunun nasıl alındığını gösterir:

```python
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel

app = FastAPI()

# Manuel Kontrol Endpoint'i (Manual Override)
@app.post("/actuator/cmd")
async def manual_control(cmd: ActuatorCmd):
    # Komutu doğrudan MOD-03 üzerinden MQTT'ye ilet (LLM devre dışı kalır)
    route_to_mod03(cmd)
    return {"status": "API_OK", "message": f"{cmd.device_type} manual command executed."}

# Canlı Dashboard Yayını
@app.websocket("/ws/state")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        state = await get_latest_twin_state()
        await websocket.send_json(state)