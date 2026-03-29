# MOD04 LLM Intent Engine

One-sentence purpose: Parses user intent from speech using Qwen 2.5 3B LLM with sensor context.

**Note**: This module's header (mod04_intent_engine.h) specifies C interfaces, but the actual implementation is Python-based. The C headers define the contract for embedded system integration; Python implementation runs Qwen 2.5 3B via Ollama for intent parsing.

## Authors

- Taha Emirhan İldeş (ID: 240104004995)
- Yunus Emre Manav (ID: 210104004024)
- Ahmet Burak Çelebi (ID: 220104004885)

## Dependencies

**Module Dependencies:** MOD03 (STT results as input)  
**External Dependencies:**
- Python 3.8+
- Ollama with Qwen 2.5 3B model
- Libraries: `ollama`, `pydantic`
- `project_types.h`, `mod03_stt_pipeline.h` (for types)

## Quick Start

```python
from mod04_intent_engine import intent_engine_init, intent_engine_parse

intent_engine_init("qwen2.5:3b", "http://localhost:11434/api/chat")

req = {
    "user_text": "turn on the light in living room",
    "sensor_ctx": current_sensor_data,
    "active_profile": user_profile,
    "room_hint": "living"
}

result = intent_engine_parse(req)
print(result.intent.action)
```

## C-Python Integration

Since this module presents C header interfaces but runs Python implementation:
- **Callbacks**: Intent results (intent_result_t) are returned via Python callbacks after LLM inference.
- **Ollama Bridge**: Python communicates with Ollama service via HTTP REST API on localhost:11434.
- **Code Linking**: Embedding projects should use ctypes or CFFI to wrap Python functions, or ipcm/RPC for distributed calling.
- **Latency Note**: LLM inference (10-30s) is dominant cost; consider request caching for similar inputs.
- **Example**: For Raspberry Pi integration, MOD04 Python output → MQTT `home/intent/result` → MOD05 subscribes and dispatches.

## API Summary

| Function                           | Parameters                                       | Return            | Notes                         |
| ---------------------------------- | ------------------------------------------------ | ----------------- | ----------------------------- |
| `intent_engine_init`               | `const char *model_name, const char *ollama_url` | `intent_status_t` | Initializes Ollama connection |
| `intent_engine_parse`              | `const llm_request_t *req, intent_result_t *out` | `intent_status_t` | Parses text to intent         |
| `intent_engine_load_few_shots`     | `const char *json_path`                          | `intent_status_t` | Loads few-shot examples       |
| `intent_engine_set_sensor_context` | `const sensor_snapshot_t *snap`                  | `void`            | Sets sensor context           |
| `intent_engine_set_active_profile` | `const user_profile_t *profile`                  | `void`            | Sets active profile           |
| `intent_engine_validate`           | `const char *json_str, intent_t *out`            | `intent_status_t` | Validates JSON to intent      |
| `intent_engine_shutdown`           | (none)                                           | `void`            | Shuts down engine             |

## Known Limitations

- LLM inference time may exceed 10s on Raspberry Pi 4
- Requires pre-loaded few-shot examples for accuracy
- Pydantic validation may reject valid but unconventional intents
- Model quantized to 4-bit may reduce accuracy

## TODOs

- Add more few-shot examples for edge cases
- Implement intent caching to reduce inference time
- Add support for multi-turn conversations
- Fine-tune model on smart home commands

## Version History

- v0.1 (2026-03-28) - Initial intent engine with Qwen 2.5 3B
