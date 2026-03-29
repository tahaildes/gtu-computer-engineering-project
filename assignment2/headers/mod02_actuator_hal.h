/**
 * @file mod02_actuator_hal.h
 * @brief Hardware Abstraction Layer for ESP32 actuators (Servo, Fan, Heater, Humidifier, Buzzer).
 * @author Primary: Ahmet Burak Çelebi, Secondary: Dilara Gözen
 * @date 2026-03-28
 * @version 0.1
 *
 * Changelog:
 * v0.1 (2026-03-28) - Initial actuator HAL interface
 */

#ifndef MOD02_ACTUATOR_HAL_H
#define MOD02_ACTUATOR_HAL_H

#include <stdint.h>
#include <stdbool.h>
#include "project_types.h"

/* Constants */
#define ACTUATOR_SERVO_MIN_US 500
#define ACTUATOR_SERVO_MAX_US 2400
#define ACTUATOR_SERVO_FREQ_HZ 50
#define ACTUATOR_FAN_PWM_FREQ_HZ 25000
#define ACTUATOR_BUZZER_ALARM_FREQ_HZ 2400
#define ACTUATOR_BUZZER_ALARM_DURATION_MS 500
#define ACTUATOR_MQTT_TOPIC_CMD "home/+/+/cmd"
#define ACTUATOR_MQTT_TOPIC_STATUS "home/actuator/status"
#define ACTUATOR_RELAY_ON 1
#define ACTUATOR_RELAY_OFF 0

/**
 * @brief Actuator type enumerations.
 */
typedef enum {
    ACTUATOR_SERVO,      /**< Servo motor */
    ACTUATOR_FAN,        /**< DC fan */
    ACTUATOR_HEATER,     /**< PTC heater */
    ACTUATOR_HUMIDIFIER, /**< Ultrasonic humidifier */
    ACTUATOR_BUZZER      /**< Passive buzzer */
} actuator_type_t;

/**
 * @brief Actuator state structure.
 */
typedef struct {
    actuator_type_t type;    /**< Actuator type */
    room_id_t room;          /**< Associated room */
    uint8_t value;           /**< Current value in percentage (0-100%) */
    bool relay_state;        /**< Relay state (true=on, false=off) */
    uint32_t last_cmd_ms;    /**< Last command timestamp (ms since boot) */
} actuator_state_t;

/**
 * @brief Actuator configuration structure.
 */
typedef struct {
    uint8_t servo_gpio_pin;        /**< Servo GPIO pin */
    uint8_t fan_gpio_pin;          /**< Fan GPIO pin */
    uint8_t heater_relay_pin;      /**< Heater relay pin */
    uint8_t humidifier_relay_pin;  /**< Humidifier relay pin */
    uint8_t buzzer_gpio_pin;       /**< Buzzer GPIO pin */
} actuator_config_t;

/**
 * @brief Initializes actuator hardware.
 * @param cfg Pointer to actuator configuration.
 * @return Actuator status.
 */
actuator_status_t actuator_hal_init(const actuator_config_t *cfg);

/**
 * @brief Executes device command.
 * @param cmd Pointer to device command.
 * @return Actuator status.
 */
actuator_status_t actuator_hal_execute(const device_cmd_t *cmd);

/**
 * @brief Gets current state of actuator.
 * @param type Actuator type.
 * @param out Pointer to output state.
 * @return Actuator status.
 */
actuator_status_t actuator_hal_get_state(actuator_type_t type, actuator_state_t *out);

/**
 * @brief Sets servo position (0-100%).
 * @param room Target room.
 * @param position_pct Position percentage (0=0deg, 100=180deg).
 * @return Actuator status.
 */
actuator_status_t actuator_hal_set_servo(room_id_t room, uint8_t position_pct);

/**
 * @brief Sets fan speed (0-100%).
 * @param room Target room.
 * @param speed_pct Speed percentage (0=off, 100=max).
 * @return Actuator status.
 */
actuator_status_t actuator_hal_set_fan(room_id_t room, uint8_t speed_pct);

/**
 * @brief Sets relay state for device.
 * @param device Actuator type.
 * @param room Target room.
 * @param state Relay state.
 * @return Actuator status.
 */
actuator_status_t actuator_hal_set_relay(actuator_type_t device, room_id_t room, bool state);

/**
 * @brief Triggers alarm buzzer.
 * @param freq_hz Buzzer frequency in Hertz (typical: 2400 Hz for alarm).
 * @param duration_ms Duration in milliseconds (typical: 500 ms).
 */
void actuator_hal_trigger_alarm(uint16_t freq_hz, uint32_t duration_ms);

/**
 * @brief Silences alarm buzzer.
 */
void actuator_hal_silence_alarm(void);

/**
 * @brief Emergency stop for all actuators.
 */
void actuator_hal_emergency_stop(void);

#endif /* MOD02_ACTUATOR_HAL_H */