import json
import time
import sqlite3
import asyncio
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

DB_PATH = "dark_factory.db"

_main_loop = None

app = FastAPI(title="Dark Factory API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── MOD-03 / MOD-04 fonksiyon bağları ────────────────────
_get_snapshot_fn    = None
_get_last_report_fn = None
_send_actuator_fn   = None

def register(get_snapshot, get_last_report, send_actuator):
    """api_server_init karşılığı: MOD-03 ve MOD-04 arayüzlerini bağlar."""
    global _get_snapshot_fn, _get_last_report_fn, _send_actuator_fn
    _get_snapshot_fn    = get_snapshot
    _get_last_report_fn = get_last_report
    _send_actuator_fn   = send_actuator

# ── WebSocket Bağlantı Yöneticisi ────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        print(f"[WS] Bağlandı. Toplam: {len(self.active)}")

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        print(f"[WS] Ayrıldı. Toplam: {len(self.active)}")

    async def broadcast(self, data: dict):
        msg = json.dumps(data)
        for ws in list(self.active):
            try:
                await ws.send_text(msg)
            except Exception:
                if ws in self.active:
                    self.active.remove(ws)

manager = ConnectionManager()

# ── REST Endpoints ────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Dark Factory API çalışıyor"}

@app.get("/twin")
def get_twin():
    """api_broadcast_state karşılığı — anlık twin_state_t snapshot'ını döner."""
    if _get_snapshot_fn is None:
        return JSONResponse({"error": "Henüz veri yok"}, status_code=503)
    return _get_snapshot_fn()

@app.get("/report")
def get_report():
    """api_broadcast_llm_report karşılığı — son maintenance_report_t'yi döner."""
    if _get_last_report_fn is None:
        return JSONResponse({"error": "Henüz rapor yok"}, status_code=503)
    return _get_last_report_fn()

@app.get("/history")
def get_history(limit: int = 50):
    """MOD-03 SQLite'tan ham sensör geçmişini döner."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT zone_id, sensor_type, value, unit, timestamp_ms "
            "FROM sensor_readings ORDER BY timestamp_ms DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [
            {"zone_id": r[0], "sensor_type": r[1], "value": r[2],
             "unit": r[3], "timestamp_ms": r[4]}
            for r in rows
        ]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/reports")
def get_reports(limit: int = 10):
    """MOD-03 SQLite'tan geçmiş LLM bakım raporlarını döner."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT report, created_at FROM maintenance_reports "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [
            {"report": json.loads(r[0]), "created_at": r[1]}
            for r in rows
        ]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/actuator/cmd")
async def actuator_cmd(body: dict):
    """
    api_handle_manual_override karşılığı.
    Payload: actuator_cmd_t şemasına uygun
      { zone_id, device_type, value_pct, state (opsiyonel) }
    source="MANUAL" olarak MOD-03'e iletilir; LLM devre dışı kalır.
    """
    if _send_actuator_fn is None:
        return JSONResponse({"error": "Actuator bağlı değil"}, status_code=503)
    try:
        zone_id     = body.get("zone_id", "zone_a")
        device_type = body.get("device_type")
        value_pct   = int(body.get("value_pct", 0))
        # actuator_cmd_t.state alanı: belirtilmezse value_pct'den türetilir
        state       = body.get("state", 1 if value_pct > 0 else 0)

        _send_actuator_fn(zone_id, device_type, value_pct,
                          state=state, source="MANUAL")
        return {"status": "API_OK", "cmd": {
            "zone_id":     zone_id,
            "device_type": device_type,
            "value_pct":   value_pct,
            "state":       state,
            "source":      "MANUAL",
        }}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ── WebSocket Endpoints ───────────────────────────────────

@app.websocket("/ws/state")
async def websocket_state(websocket: WebSocket):
    """
    api_broadcast_state + api_broadcast_llm_report birleşik kanalı.
    Her snapshot geldiğinde { type, snapshot, report } payload'u push edilir.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()   # client ping / keep-alive bekle
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ── Push: MOD-03 snapshot'ı gelince WS'e yayınla ─────────

def _broadcast_state(snap: dict):
    """api_broadcast_state implementasyonu — twin_state_t payload'unu yayınlar."""
    report = _get_last_report_fn() if _get_last_report_fn else {}
    payload = {
        "type":     "snapshot",
        "snapshot": snap,         # twin_state_t karşılığı
        "report":   report,       # maintenance_report_t karşılığı
    }
    _schedule_broadcast(payload)

def broadcast_llm_report(report: dict):
    """
    api_broadcast_llm_report implementasyonu.
    MOD-04 yeni rapor ürettiğinde main.py üzerinden çağrılır;
    anlık twin snapshot'ı olmadan yalnızca raporu push eder.
    """
    payload = {
        "type":   "report",
        "report": report,
    }
    _schedule_broadcast(payload)

def _schedule_broadcast(payload: dict):
    global _main_loop
    if _main_loop is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(manager.broadcast(payload), _main_loop)
    except Exception as e:
        print(f"[WS] Broadcast hatası: {e}")

# on_snapshot_push: main.py'nin çağırdığı genel arayüz (geriye dönük uyum)
def on_snapshot_push(snap: dict):
    _broadcast_state(snap)

# ── Sunucu Başlatma ───────────────────────────────────────

def start():
    """api_server_init karşılığı — FastAPI + Uvicorn sunucusunu başlatır."""
    global _main_loop
    _main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_main_loop)
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="warning",
        loop="none",
    )
    server = uvicorn.Server(config)
    _main_loop.run_until_complete(server.serve())