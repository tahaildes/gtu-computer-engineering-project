#ifndef MOD01_AMBIENT_HAL_H
#define MOD01_AMBIENT_HAL_H

/**
 * @file    mod01_ambient_hal.h
 * @brief   Ambient Environment Hardware Abstraction Layer
 * @author  Emirhan Çalışkan (220104004955), Mehmet Akif Pekşen (230104004013)
 * @date    2026-05-09
 * @version 0.1
 *
 * Changelog:
 * v0.1 - Initial draft: Core initialization, read tasks, and execution functions.
 */

#include <stdint.h>
#include "factory_types.h" /* Shared canonical data structures */

/* -- Constants ------------------------------------------------------------ */
/** @brief Periodic sensor reading interval in milliseconds */
#define AMBIENT_READ_INTERVAL_MS 3000

/* -- Data Types ----------------------------------------------------------- */
/** @brief Status codes for Ambient HAL operations */
typedef enum {
    AMBIENT_OK       =  0,
    AMBIENT_ERR_INIT = -1,
    AMBIENT_ERR_I2C  = -2,
    AMBIENT_ERR_SPI  = -3
} ambient_status_t;

/** @brief Configuration structure for HAL initialization */
typedef struct {
    uint8_t i2c_sda_pin;
    uint8_t i2c_scl_pin;
    uint8_t spi_cs_pin;
} ambient_config_t;

/* -- Public Functions ----------------------------------------------------- */

/**
 * @brief  Initializes I2C and SPI buses for environmental sensors.
 * @param  config Pointer to hardware configuration pins.
 * @return AMBIENT_OK on success, or an error code on failure.
 */
ambient_status_t ambient_hal_init(const ambient_config_t *config);

/**
 * @brief  Starts the FreeRTOS periodic sensor reading task.
 * Reads BME280 and MQ sensors, applies calibration, and publishes to MQTT.
 * @return AMBIENT_OK on success.
 */
ambient_status_t ambient_hal_start_periodic(void);

/**
 * @brief  Executes an incoming actuator command (Fan, Servo, Mist Maker, Buzzer).
 * @param  cmd Pointer to the actuator command struct received via MQTT.
 * @return AMBIENT_OK on successful execution.
 */
ambient_status_t ambient_hal_execute(const actuator_cmd_t *cmd);

/**
 * @brief  Directly controls the DC Fan speed via PWM.
 * @param  duty_pct Fan speed percentage (0-100).
 */
void ambient_hal_set_fan(uint8_t duty_pct);

/**
 * @brief  Directly controls the ventilation servo motor angle.
 * @param  open_pct Opening percentage (0-100).
 */
void ambient_hal_set_servo(uint8_t open_pct);

/**
 * @brief  Toggles the ultrasonic mist maker relay.
 * @param  state 1 for ON, 0 for OFF.
 */
void ambient_hal_set_mist_maker(uint8_t state);

/**
 * @brief  Triggers the local buzzer alarm tone.
 * @param  state 1 for ON, 0 for OFF.
 */
void ambient_hal_trigger_alarm(uint8_t state);

#endif /* MOD01_AMBIENT_HAL_H */