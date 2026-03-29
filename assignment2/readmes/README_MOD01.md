# MOD01 ESP32 Sensor HAL

One-sentence purpose: Abstracts BME280 and MCP3008 sensor hardware behind a clean C interface.

## Authors

- Emirhan Çalışkan (ID: 220104004955)
- Mehmet Akif Pekşen (ID: 230104004013)

## Dependencies

**Module Dependencies:** None  
**External Dependencies:**
- ESP-IDF 5.0 or later
- PIO library: `adafruit/Adafruit BME280`
- `project_types.h` (shared types)

## Quick Start

```c
#include "mod01_sensor_hal.h"

sensor_config_t cfg = {
    .read_interval_ms = 5000,
    .bme280_sda_pin = 21,              // ESP32 GPIO 21 for I2C SDA
    .bme280_scl_pin = 22,              // ESP32 GPIO 22 for I2C SCL
    .mcp3008_cs_pin = 5,               // ESP32 GPIO 5 for SPI CS
    .mcp3008_mosi_pin = 23,            // ESP32 GPIO 23 for SPI MOSI
    .mcp3008_miso_pin = 19,            // ESP32 GPIO 19 for SPI MISO
    .mcp3008_clk_pin = 18,             // ESP32 GPIO 18 for SPI CLK
    .gas_threshold_ppm = 300.0f,
    .smoke_threshold_ppm = 200.0f,
    .on_reading = my_callback,
    .on_alarm = my_alarm_callback
};

sensor_hal_init(&cfg);
sensor_hal_start_periodic();
// Callbacks will be invoked every 5 seconds
```

## API Summary

| Function                     | Parameters                   | Return            | Notes                                     |
| ---------------------------- | ---------------------------- | ----------------- | ----------------------------------------- |
| `sensor_hal_init`            | `const sensor_config_t *cfg` | `sensor_status_t` | Must call first; initializes I2C and SPI  |
| `sensor_hal_read`            | `sensor_snapshot_t *out`     | `sensor_status_t` | Synchronous single read                   |
| `sensor_hal_start_periodic`  | (none)                       | `sensor_status_t` | Starts FreeRTOS task for continuous reads |
| `sensor_hal_stop`            | (none)                       | `void`            | Stops periodic reads; powers down sensors |
| `sensor_hal_calibrate`       | `sensor_channel_t ch`        | `sensor_status_t` | Calibrates gas/smoke offset               |
| `sensor_hal_is_alarm_active` | (none)                       | `bool`            | Queries current alarm status              |

## Known Limitations

- I2C bus clock is fixed at 100 kHz (no higher speed tested)
- MCP3008 ADC resolution is 10-bit; consider external 16-bit ADC for higher precision
- Wake-up from deep sleep not yet tested on real hardware
- Gas sensor warm-up time not accounted for during initialization

## Error Handling

- **SENSOR_OK (0)**: Operation successful; no action needed.
- **SENSOR_ERR_I2C_INIT**: I2C bus initialization failed (GPIO pins misconfigured?); verify GPIO 21/22 are available and not in use.
- **SENSOR_ERR_I2C_TIMEOUT**: I2C read timed out (sensor not responding?); check BME280 is powered, address is 0x76, SDA/SCL properly connected.
- **SENSOR_ERR_SPI_INIT**: SPI bus init failed (GPIO pins misconfigured?); verify GPIO 5/23/19/18 available.
- **SENSOR_ERR_READ_FAILED**: Sensor read returned invalid data; retry or check sensor wiring.
- **SENSOR_ERR_TIMEOUT**: Read operation exceeded SENSOR_TIMEOUT_MS; increase timeout or debug I2C congestion.
- **SENSOR_ERR_INVALID_PARAM**: Configuration struct has invalid fields (e.g., thresholds outside 0-10000 ppm range).

Caller should log errors and potentially trigger safe shutdown or alarm state.

## TODOs

- Add support for additional I2C sensors (LPS22HB barometer, etc.)
- Implement sensor self-test routine
- Add exponential moving average (EMA) filter to reduce noise
- Profile power consumption in different modes

## Version History

- v0.1 (2026-03-28) - Initial draft, basic sensor_init / sensor_read
- v0.2 (2026-03-28) - Added periodic reading and callbacks
