# MOD06 API Server & UI Backend

One-sentence purpose: Provides REST API and WebSocket server for remote access and user profiles.

**Note**: This module's header (mod06_api_backend.h) specifies C interfaces, but the actual implementation is Python-based with FastAPI. The C headers define the contract for embedded system integration; Python implementation provides REST/WebSocket server functionality.

## Authors

- Dilara Gözen (ID: 230104004065)
- Zeynep Sude Turan (ID: 220104004031)
- Burak Kurtaran (ID: 210104004240)

## Dependencies

**Module Dependencies:** MOD04 (intent parsing), MOD05 (control layer for sensor data)  
**External Dependencies:**
- Python 3.8+
- Libraries: `fastapi`, `uvicorn`, `websockets`, `sqlite3`, `pyngrok`
- `project_types.h`, `mod04_intent_engine.h`, `mod05_control_safety.h` (for types)

## Quick Start

```python
from mod06_api_backend import api_init, api_start

api_init("/var/smartHome/smartHome.db", 8000)
api_start()
# FastAPI server starts on port 8000
# Ngrok tunnel created for remote access
```

## C-Python Integration

Since this module presents C header interfaces but runs Python implementation:
- **REST API**: FastAPI serves JSON endpoints; HTTP clients (web/mobile) communicate via REST.
- **WebSocket Bridge**: Real-time sensor updates pushed to clients via WebSocket (port 8000/ws).
- **Code Linking**: Embedding projects should call Python functions via ctypes, or communicate via HTTPS/WebSocket.
- **Ngrok Tunnel**: Free tier provides temporary URL for remote access; consider Cloudflare Tunnel or Tailscale for stability.
- **Database**: SQLite on disk at path specified in api_init(); command history logged for debugging.

## API Summary

| Function              | Parameters                                                 | Return         | Notes                         |
| --------------------- | ---------------------------------------------------------- | -------------- | ----------------------------- |
| `api_init`            | `const char *db_path, uint16_t port`                       | `api_status_t` | Initializes database and port |
| `api_start`           | (none)                                                     | `api_status_t` | Starts FastAPI + Ngrok        |
| `api_handle_text_cmd` | `const text_cmd_request_t *req, intent_result_t *out`      | `api_status_t` | POST /command handler         |
| `api_save_profile`    | `const user_profile_t *profile`                            | `api_status_t` | Saves profile to SQLite       |
| `api_load_profile`    | `const char *name, room_id_t room, user_profile_t *out`    | `api_status_t` | Loads profile                 |
| `api_list_profiles`   | `room_id_t room, user_profile_t *profiles, uint8_t *count` | `api_status_t` | Lists profiles                |
| `api_delete_profile`  | `const char *name, room_id_t room`                         | `api_status_t` | Deletes profile               |
| `api_log_command`     | `const cmd_log_entry_t *entry`                             | `api_status_t` | Logs command                  |
| `api_ws_broadcast`    | `const ws_message_t *msg`                                  | `api_status_t` | Broadcasts via WebSocket      |
| `api_shutdown`        | (none)                                                     | `void`         | Shuts down server             |

## Known Limitations

- SQLite database may have concurrency issues under high load
- Ngrok free tier has bandwidth and connection limits
- WebSocket broadcast interval fixed at 1s
- No authentication or authorization implemented

## TODOs

- Add user authentication and authorization
- Implement rate limiting for API endpoints
- Add command history pagination
- Support for multiple database backends

## Version History

- v0.1 (2026-03-28) - Initial API backend with FastAPI
