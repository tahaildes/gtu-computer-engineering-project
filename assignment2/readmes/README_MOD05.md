# MOD05 Device Control & Safety

One-sentence purpose: Handles device control via MQTT with rule-based safety checks.

## Authors

- Burak Kurtaran (ID: 210104004240)
- Ahmet Burak Çelebi (ID: -)

## Dependencies

**Module Dependencies:** MOD01 (sensor data), MOD02 (actuator control), MOD04 (intent parsing)  
**External Dependencies:**
- Python 3.8+
- Mosquitto MQTT broker
- Libraries: `paho-mqtt`
- `project_types.h`, `mod01_sensor_hal.h` (for types)

## Quick Start

```python
from mod05_control_safety import ctrl_init, ctrl_dispatch_intent

ctrl_init("localhost", 1883)

intent = {
    "action": "turn_on",
    "room": ROOM_LIVING,
    "commands": [device_cmd],
    "cmd_count": 1,
    "is_profile_recall": False
}

ctrl_dispatch_intent(intent)
# Commands dispatched via MQTT
```

## MQTT Topic Schema

- **Sensor Data**: `home/sensor/data` (published by MOD01)
  - Payload: JSON with bme280/mcp3008 readings + timestamps
- **Device Commands**: `home/{room_id}/{device_id}/cmd` (published by MOD05)
  - Example: `home/living/fan/cmd` for fan control
  - Payload: JSON with device_cmd struct fields

## C-Python Integration

Since this module presents C header interfaces but runs Python implementation:
- **Safety Monitoring**: Critical sensor checks (temperature >40°C, humidity >80%) trigger immediate responses via MQTT publish.
- **MQTT Pub/Sub**: Python uses paho-mqtt library to subscribe/publish; ESP32 units listen on respective topics.
- **Code Linking**: Embedding projects should wrap Python functions via ctypes or connect via MQTT broker (recommended for distributed systems).
- **LLM Bypass**: During alarm states, Python skips LLM inference and publishes emergency commands directly.
- **Latency**: MQTT pub time ~50-100ms; total safety response target is 1 second.

## API Summary

| Function                     | Parameters                               | Return          | Notes                        |
| ---------------------------- | ---------------------------------------- | --------------- | ---------------------------- |
| `ctrl_init`                  | `const char *broker_host, uint16_t port` | `ctrl_status_t` | Initializes MQTT connection  |
| `ctrl_dispatch_intent`       | `const intent_t *intent`                 | `ctrl_status_t` | Converts intent to MQTT cmds |
| `ctrl_publish_cmd`           | `const device_cmd_t *cmd`                | `ctrl_status_t` | Publishes single command     |
| `ctrl_subscribe_sensor_data` | (none)                                   | `ctrl_status_t` | Subscribes to sensor data    |
| `ctrl_safety_check`          | `const sensor_snapshot_t *snap`          | `void`          | Checks safety rules          |
| `ctrl_add_safety_rule`       | `const safety_rule_t *rule`              | `ctrl_status_t` | Adds safety rule             |
| `ctrl_trigger_alarm`         | `const sensor_alarm_t *alarm`            | `void`          | Triggers alarm (LLM bypass)  |
| `ctrl_silence_alarm`         | (none)                                   | `ctrl_status_t` | Silences alarm               |
| `ctrl_get_state`             | (none)                                   | `ctrl_state_t`  | Gets current state           |
| `ctrl_shutdown`              | (none)                                   | `void`          | MQTT disconnect              |

## Known Limitations

- MQTT QoS 1 may cause message loss in unstable networks
- Safety rules are static and not configurable at runtime
- Alarm response time may exceed 1s under high load
- No retry mechanism for failed MQTT publishes

## Error Handling

- **CTRL_OK (0)**: Operation successful.
- **CTRL_ERR_MQTT**: MQTT broker connection failed or publish failed; check Mosquitto is running on localhost:1883.
- **CTRL_ERR_INVALID_INTENT**: Intent struct contains invalid fields (e.g., out-of-range room_id); validate intent_t before dispatch.
- **CTRL_ERR_DISPATCH**: Command dispatch to ESP32 failed (topic not subscribed?); verify ESP32 MQTT client is active.
- **CTRL_ALARM_ACTIVE**: Attempt to process normal command while alarm is active; silence alarm first via `ctrl_silence_alarm()`.

Caller should implement exponential backoff retry for transient MQTT errors and log all dispatch failures.

## TODOs

- Add configurable safety rules via API
- Implement command queuing for offline devices
- Add device status feedback and error handling
- Support for MQTT over TLS

## Version History

- v0.1 (2026-03-28) - Initial control and safety layer
