# MOD02 ESP32 Actuator HAL

One-sentence purpose: Abstracts servo, fan, heater, humidifier, and buzzer actuators behind a clean C interface.

## Authors

- Emirhan Çalışkan (ID: 220104004955)
- Mehmet Akif Pekşen (ID: 230104004013)
- Dilara Gözen (ID: -)

## Dependencies

**Module Dependencies:** None  
**External Dependencies:**
- ESP-IDF 5.0 or later
- `project_types.h` (shared types)

## Quick Start

```c
#include "mod02_actuator_hal.h"

actuator_config_t cfg = {
    .servo_gpio_pin = 12,              // ESP32 GPIO 12 for servo PWM (SG90)
    .fan_gpio_pin = 13,                // ESP32 GPIO 13 for fan PWM
    .heater_relay_pin = 14,            // ESP32 GPIO 14 for heater relay
    .humidifier_relay_pin = 15,        // ESP32 GPIO 15 for humidifier relay
    .buzzer_gpio_pin = 16              // ESP32 GPIO 16 for buzzer PWM
};

actuator_hal_init(&cfg);

// Example: Set servo to 50% position (90 degrees)
actuator_hal_set_servo(ROOM_LIVING, 50);

// Example: Execute device command from intent engine
device_cmd_t cmd = {HOME_ROOM_FAN, ROOM_LIVING, 75, ACTUATOR_RELAY_OFF};
actuator_hal_execute(&cmd);

// Example: Trigger alarm on smoke detection
actuator_hal_trigger_alarm(2400, 500);  // 2400 Hz buzzer for 500ms
```

## API Summary

| Function                      | Parameters                                           | Return              | Notes                       |
| ----------------------------- | ---------------------------------------------------- | ------------------- | --------------------------- |
| `actuator_hal_init`           | `const actuator_config_t *cfg`                       | `actuator_status_t` | Initializes PWM and relays  |
| `actuator_hal_execute`        | `const device_cmd_t *cmd`                            | `actuator_status_t` | Executes device command     |
| `actuator_hal_get_state`      | `actuator_type_t type, actuator_state_t *out`        | `actuator_status_t` | Gets current actuator state |
| `actuator_hal_set_servo`      | `room_id_t room, uint8_t position_pct`               | `actuator_status_t` | Sets servo position 0-100%  |
| `actuator_hal_set_fan`        | `room_id_t room, uint8_t speed_pct`                  | `actuator_status_t` | Sets fan speed 0-100%       |
| `actuator_hal_set_relay`      | `actuator_type_t device, room_id_t room, bool state` | `actuator_status_t` | Sets relay on/off           |
| `actuator_hal_trigger_alarm`  | `uint16_t freq_hz, uint32_t duration_ms`             | `void`              | Triggers buzzer alarm       |
| `actuator_hal_silence_alarm`  | (none)                                               | `void`              | Silences buzzer             |
| `actuator_hal_emergency_stop` | (none)                                               | `void`              | Shuts down all actuators    |

## Known Limitations

- Servo angle range limited to 0-180° (SG90 hardware limitation)
- Fan PWM frequency fixed at 25 kHz (may not suit all fan types)
- Relay switching not debounced (potential contact bounce)
- Buzzer volume not adjustable

## Error Handling

- **ACTUATOR_OK (0)**: Operation successful; no action needed.
- **ACTUATOR_ERR_PWM_INIT**: PWM initialization failed (GPIO pins misconfigured?); verify GPIO 12/13/16 are available.
- **ACTUATOR_ERR_GPIO_INIT**: GPIO initialization failed (relay pins?); verify GPIO 14/15 available and not in use.
- **ACTUATOR_ERR_INVALID_CMD**: Device command invalid (unknown topic or room); check mqtt_topic_t enum values.
- **ACTUATOR_ERR_RANGE**: Value out of range (e.g., servo position >100%); clamp to 0-100% before sending.

Caller should log errors and optionally trigger failsafe state (all relays off, servo neutral).

## TODOs

- Add support for stepper motors or DC motors with encoders
- Implement actuator calibration routines
- Add overcurrent protection for relays
- Support multiple actuators per room

## Version History

- v0.1 (2026-03-28) - Initial draft, basic actuator control
