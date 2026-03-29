/**
 * @file mod01_sensor_hal.h
 * @brief Hardware Abstraction Layer for ESP32 sensors (BME280, MQ-2/135).
 * @author Primary: Emirhan Çalışkan, Secondary: Burak Kurtaran
 * @date 2026-03-28
 * @version 0.1
 *
 * Changelog:
 * v0.1 (2026-03-28) - Initial sensor HAL interface
 */

#ifndef MOD01_SENSOR_HAL_H
#define MOD01_SENSOR_HAL_H

#include <stdint.h>
#include <stdbool.h>
#include "project_types.h"

/* Constants */
#define SENSOR_READ_INTERVAL_MS 5000
#define SENSOR_BME280_I2C_ADDR 0x76
#define SENSOR_MCP3008_SPI_FREQ_HZ 1350000
#define SENSOR_GAS_ALARM_PPM 300.0f
#define SENSOR_SMOKE_ALARM_PPM 200.0f
#define SENSOR_MQTT_TOPIC_SENSOR "home/sensor/data"
#define SENSOR_MQTT_TOPIC_ALARM "home/sensor/alarm"
#define SENSOR_MAX_RETRIES 3
#define SENSOR_TIMEOUT_MS 100

/**
 * @brief Sensor channel enumerations.
 */
typedef enum {
    SENSOR_CH_TEMP_HUM, /**< Temperature and humidity */
    SENSOR_CH_GAS,      /**< Gas sensor */
    SENSOR_CH_SMOKE,    /**< Smoke sensor */
    SENSOR_CH_ALL       /**< All channels */
} sensor_channel_t;

/**
 * @brief Sensor alarm data structure.
 */
typedef struct {
    sensor_channel_t source;    /**< Alarm source channel */
    float value;                /**< Current value */
    float threshold;            /**< Threshold value */
    uint32_t timestamp_ms;      /**< Timestamp */
} sensor_alarm_t;

/**
 * @brief Sensor configuration structure.
 */
typedef struct {
    uint16_t read_interval_ms;          /**< Read interval in milliseconds (overrides SENSOR_READ_INTERVAL_MS) */
    uint8_t bme280_sda_pin;             /**< I2C SDA pin for BME280 (ESP32) */
    uint8_t bme280_scl_pin;             /**< I2C SCL pin for BME280 (ESP32) */
    uint8_t mcp3008_cs_pin;             /**< SPI CS (Chip Select) pin for MCP3008 */
    uint8_t mcp3008_mosi_pin;           /**< SPI MOSI pin for MCP3008 */
    uint8_t mcp3008_miso_pin;           /**< SPI MISO pin for MCP3008 */
    uint8_t mcp3008_clk_pin;            /**< SPI CLK pin for MCP3008 */
    float gas_threshold_ppm;            /**< Gas alarm threshold (ppm) */
    float smoke_threshold_ppm;          /**< Smoke alarm threshold (ppm) */
    void (*on_reading)(const sensor_snapshot_t *data); /**< Reading callback */
    void (*on_alarm)(const sensor_alarm_t *alarm);     /**< Alarm callback */
} sensor_config_t;

/* Callback typedefs */
typedef void (*sensor_cb_t)(const sensor_snapshot_t *data);
typedef void (*sensor_alarm_cb_t)(const sensor_alarm_t *alarm);

/**
 * @brief Initializes BME280 and MCP3008 sensors.
 * @param cfg Pointer to sensor configuration.
 * @return Sensor status.
 */
sensor_status_t sensor_hal_init(const sensor_config_t *cfg);

/**
 * @brief Performs synchronous sensor read.
 * @param out Pointer to output sensor snapshot.
 * @return Sensor status.
 */
sensor_status_t sensor_hal_read(sensor_snapshot_t *out);

/**
 * @brief Starts periodic reading at SENSOR_READ_INTERVAL_MS intervals.
 * @return Sensor status.
 */
sensor_status_t sensor_hal_start_periodic(void);

/**
 * @brief Stops periodic reading and releases resources.
 */
void sensor_hal_stop(void);

/**
 * @brief Calibrates specified sensor channel.
 * @param ch Sensor channel to calibrate.
 * @return Sensor status.
 */
sensor_status_t sensor_hal_calibrate(sensor_channel_t ch);

/**
 * @brief Checks if alarm is currently active.
 * @return True if alarm is active, false otherwise.
 */
bool sensor_hal_is_alarm_active(void);

#endif /* MOD01_SENSOR_HAL_H */