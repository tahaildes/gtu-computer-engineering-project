#ifndef FACTORY_TYPES_H
#define FACTORY_TYPES_H

/**
 * @file    factory_types.h
 * @brief   Shared Data Types - Dark Factory canonical data structures
 * @author  Dark Factory Core Team
 * @date    2026-05-09
 * @version 0.1
 *
 * Changelog:
 * v0.1 - Initial draft: Core sensor, actuator, and twin state structures
 */

#include <stdint.h>

/* -- Enumerations --------------------------------------------------------- */

typedef enum {
    ZONE_A = 0,
    ZONE_B = 1
} zone_id_t;

typedef enum {
    DEV_FAN          = 0,
    DEV_SERVO_VENT   = 1,
    DEV_MIST_MAKER   = 2,
    DEV_BUZZER       = 3
} device_type_t;

typedef enum {
    RISK_OK       = 0,
    RISK_WATCH    = 1,
    RISK_WARN     = 2,
    RISK_CRITICAL = 3
} risk_level_t;

/* -- Data Structures ------------------------------------------------------ */

/** @brief Ambient sensor readings (MOD-01) */
typedef struct {
    float    temperature_c;
    float    humidity_pct;
    float    co2_ppm;
    float    pm25;
    uint32_t timestamp_ms;
} ambient_snapshot_t;

/** @brief Machine telemetry readings (MOD-02) */
typedef struct {
    uint16_t rpm;
    float    vibration_g;
    float    power_w;
    float    machine_temp_c;
    uint32_t output_units;
    uint32_t timestamp_ms;
} machine_snapshot_t;

/** @brief Actuator command payload */
typedef struct {
    zone_id_t     zone_id;
    device_type_t device_type;
    uint8_t       value_pct;    /**< 0-100 percentage */
    uint8_t       state;        /**< 0 for OFF, 1 for ON */
    char          source[8];    /**< "RULE", "LLM", or "MANUAL" */
} actuator_cmd_t;

/** @brief Alarm event payload */
typedef struct {
    char     source_module[8];
    char     sensor_field[16];
    float    value;
    float    threshold;
    uint32_t timestamp_ms;
} alarm_event_t;

/** @brief Maintenance prediction payload (MOD-04) */
typedef struct {
    risk_level_t risk_level;
    float        predicted_failure_hrs;
    char         anomalies[128];
    char         recommended_action[128];
    float        confidence;
} maintenance_report_t;

/** @brief Digital Twin complete state representation (MOD-03) */
typedef struct {
    ambient_snapshot_t ambient[2]; /* Index matches zone_id_t */
    machine_snapshot_t machine;
    uint32_t           alarm_flags;
    uint32_t           snapshot_version;
    uint32_t           updated_at;
} twin_state_t;

#endif /* FACTORY_TYPES_H */