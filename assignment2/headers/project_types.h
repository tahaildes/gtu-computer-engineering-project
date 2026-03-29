/**
 * @file project_types.h
 * @brief Shared data types and enumerations for all modules in the smart home automation system.
 * @author Emirhan Çalışkan (ID: 220104004955), Burak Kurtaran (ID: 210104004240), Ahmet Burak Çelebi (ID: 220104004885), Dilara Gözen (ID: 230104004065), Taha Emirhan İldeş (ID: 240104004995), Yunus Emre Manav (ID: 210104004024), Zeynep Sude Turan (ID: 220104004031), Mehmet Akif Pekşen (ID: 230104004013)
 * @date 2026-03-28
 * @version 0.1
 *
 * Changelog:
 * v0.1 (2026-03-28) - Initial shared types definition
 */

#ifndef PROJECT_TYPES_H
#define PROJECT_TYPES_H

#include <stdint.h>
#include <stdbool.h>

/**
 * @brief MQTT topic enumerations for device commands.
 */
typedef enum {
    HOME_ROOM_LIGHT,    /**< Light control topic */
    HOME_ROOM_FAN,      /**< Fan control topic */
    HOME_ROOM_HEATER,   /**< Heater control topic */
    HOME_ROOM_CURTAIN,  /**< Curtain control topic */
    HOME_ROOM_HUMIDITY, /**< Humidity control topic */
    HOME_ROOM_ALARM     /**< Alarm control topic */
} mqtt_topic_t;

/**
 * @brief Room identification enumerations.
 */
typedef enum {
    ROOM_LIVING,    /**< Living room */
    ROOM_BEDROOM,   /**< Bedroom */
    ROOM_KITCHEN,   /**< Kitchen */
    ROOM_BATHROOM   /**< Bathroom */
} room_id_t;

/**
 * @brief Sensor snapshot data structure.
 */
typedef struct {
    float temperature;      /**< Temperature in Celsius (-40 to +85°C) */
    float humidity;         /**< Relative humidity in percentage (0-100%) */
    float gas_ppm;          /**< Gas concentration in parts per million (0-10000 ppm) */
    float smoke_ppm;        /**< Smoke concentration in ppm (0-10000 ppm) */
    uint32_t timestamp_ms;  /**< Timestamp in milliseconds since system boot */
} sensor_snapshot_t;

/**
 * @brief Device command data structure.
 */
typedef struct {
    mqtt_topic_t topic;     /**< MQTT topic for the command */
    room_id_t room;         /**< Target room */
    uint8_t value;          /**< Command value in percentage (0-100%), or PWM duty cycle */
    uint8_t relay_state;    /**< Relay state (0=off, 1=on) */
} device_cmd_t;

/**
 * @brief User profile data structure.
 */
typedef struct {
    char profile_name[32];      /**< Profile name */
    room_id_t room;             /**< Associated room */
    float target_temp;          /**< Target temperature */
    float target_humidity;      /**< Target humidity */
    uint8_t light_level;        /**< Light level (0-100) */
    uint8_t curtain_position;   /**< Curtain position (0-100) */
} user_profile_t;

/**
 * @brief Intent data structure for parsed commands.
 */
typedef struct {
    char action[32];            /**< Action description */
    room_id_t room;             /**< Target room */
    device_cmd_t commands[8];   /**< Array of device commands */
    uint8_t cmd_count;          /**< Number of commands */
    uint8_t is_profile_recall;  /**< Flag for profile recall */
} intent_t;

/**
 * @brief System status enumerations.
 */
typedef enum {
    STATUS_OK = 0,          /**< Operation successful */
    STATUS_ERR_SENSOR,      /**< Sensor error */
    STATUS_ERR_LLM,         /**< LLM processing error */
    STATUS_ERR_MQTT,        /**< MQTT communication error */
    STATUS_ERR_STT,         /**< Speech-to-text error */
    STATUS_ALARM_TRIGGERED  /**< Alarm has been triggered */
} system_status_t;

/**
 * @brief Sensor-specific error codes (extends system_status_t).
 */
typedef enum {
    SENSOR_OK = 0,              /**< Operation successful */
    SENSOR_ERR_I2C_INIT,        /**< I2C bus initialization failed */
    SENSOR_ERR_I2C_TIMEOUT,     /**< I2C bus timeout */
    SENSOR_ERR_SPI_INIT,        /**< SPI bus initialization failed */
    SENSOR_ERR_READ_FAILED,     /**< Sensor read failed */
    SENSOR_ERR_CALIB_FAILED,    /**< Sensor calibration failed */
    SENSOR_ERR_TIMEOUT,         /**< Operation timeout */
    SENSOR_ERR_INVALID_PARAM    /**< Invalid parameter */
} sensor_status_t;

/**
 * @brief Actuator-specific error codes.
 */
typedef enum {
    ACTUATOR_OK = 0,           /**< Operation successful */
    ACTUATOR_ERR_PWM_INIT,     /**< PWM initialization failed */
    ACTUATOR_ERR_GPIO_INIT,    /**< GPIO initialization failed */
    ACTUATOR_ERR_INVALID_PARAM, /**< Invalid parameter */
    ACTUATOR_ERR_TIMEOUT       /**< Operation timeout */
} actuator_status_t;

#endif /* PROJECT_TYPES_H */