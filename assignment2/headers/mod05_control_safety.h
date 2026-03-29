/**
 * @file mod05_control_safety.h
 * @brief Device Control & Safety Layer handling MQTT commands and sensor alarms.
 * @author Primary: Zeynep Sude Turan, Secondary: Burak Kurtaran, Taha Emirhan İdeş
 * @date 2026-03-28
 * @version 0.1
 *
 * Changelog:
 * v0.1 (2026-03-28) - Initial control and safety interface
 */

#ifndef MOD05_CONTROL_SAFETY_H
#define MOD05_CONTROL_SAFETY_H

#include <stdint.h>
#include <stdbool.h>
#include "project_types.h"
#include "mod01_sensor_hal.h"  /* for sensor_alarm_t */

/* Constants */
#define CTRL_MQTT_BROKER_HOST "localhost"
#define CTRL_MQTT_BROKER_PORT 1883
#define CTRL_MQTT_QOS 1
#define CTRL_MQTT_KEEPALIVE_S 60
#define CTRL_SAFETY_CHECK_INTERVAL_MS 500
#define CTRL_ALARM_RESPONSE_TARGET_MS 1000
#define CTRL_TOPIC_CMD_TEMPLATE "home/%s/%s/cmd"
#define CTRL_TOPIC_SENSOR_DATA "home/sensor/data"
#define CTRL_TEMP_MAX_C 40.0f
#define CTRL_HUMIDITY_MAX_PCT 80.0f

/**
 * @brief Control status enumerations.
 */
typedef enum {
    CTRL_OK = 0,            /**< Operation successful */
    CTRL_ERR_MQTT,          /**< MQTT error */
    CTRL_ERR_INVALID_INTENT,/**< Invalid intent */
    CTRL_ERR_DISPATCH,      /**< Dispatch error */
    CTRL_ALARM_ACTIVE       /**< Alarm is active */
} ctrl_status_t;

/**
 * @brief Safety rule structure.
 */
typedef struct {
    char rule_name[32];      /**< Rule name */
    float threshold;         /**< Threshold value */
    device_cmd_t response_cmd; /**< Response command */
    bool bypass_llm;         /**< Bypass LLM flag */
} safety_rule_t;

/**
 * @brief Control state structure.
 */
typedef struct {
    bool mqtt_connected;         /**< MQTT connection status */
    bool alarm_active;           /**< Alarm status */
    sensor_snapshot_t last_sensor; /**< Last sensor data */
    uint8_t active_safety_rules; /**< Number of active rules */
} ctrl_state_t;

/**
 * @brief Initializes control module.
 * @param broker_host MQTT broker host.
 * @param port MQTT broker port.
 * @return Control status.
 */
ctrl_status_t ctrl_init(const char *broker_host, uint16_t port);

/**
 * @brief Dispatches intent to MQTT commands.
 * @param intent Pointer to intent.
 * @return Control status.
 */
ctrl_status_t ctrl_dispatch_intent(const intent_t *intent);

/**
 * @brief Publishes single device command.
 * @param cmd Pointer to device command.
 * @return Control status.
 */
ctrl_status_t ctrl_publish_cmd(const device_cmd_t *cmd);

/**
 * @brief Subscribes to sensor data topic.
 * @return Control status.
 */
ctrl_status_t ctrl_subscribe_sensor_data(void);

/**
 * @brief Checks sensor data against safety rules.
 * @param snap Pointer to sensor snapshot.
 */
void ctrl_safety_check(const sensor_snapshot_t *snap);

/**
 * @brief Adds a safety rule.
 * @param rule Pointer to safety rule.
 * @return Control status.
 */
ctrl_status_t ctrl_add_safety_rule(const safety_rule_t *rule);

/**
 * @brief Triggers alarm based on sensor alarm.
 * @param alarm Pointer to sensor alarm.
 */
void ctrl_trigger_alarm(const sensor_alarm_t *alarm);

/**
 * @brief Silences active alarm.
 * @return Control status.
 */
ctrl_status_t ctrl_silence_alarm(void);

/**
 * @brief Gets current control state.
 * @return Control state.
 */
ctrl_state_t ctrl_get_state(void);

/**
 * @brief Shuts down control module.
 */
void ctrl_shutdown(void);

#endif /* MOD05_CONTROL_SAFETY_H */