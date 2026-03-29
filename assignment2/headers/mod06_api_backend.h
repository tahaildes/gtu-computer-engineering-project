/**
 * @file mod06_api_backend.h
 * @brief REST API and WebSocket Server interface specification.
 * @author Primary: Dilara Gözen, Secondary: Yunus Emre Manav, Zeynep Sude Turan
 * @date 2026-03-28
 * @version 0.1
 *
 * Changelog:
 * v0.1 (2026-03-28) - Initial API backend interface
 */

#ifndef MOD06_API_BACKEND_H
#define MOD06_API_BACKEND_H

#include <stdint.h>
#include <stdbool.h>
#include "project_types.h"
#include "mod04_intent_engine.h"  /* for intent_result_t */

/* Constants */
#define API_HOST "0.0.0.0"
#define API_PORT 8000
#define API_WS_BROADCAST_INTERVAL_MS 1000
#define API_DB_PATH "/var/smartHome/smartHome.db"
#define API_LOG_MAX_ENTRIES 10000
#define API_MAX_PROFILE_NAME_LEN 32
#define API_MAX_PROFILES_PER_ROOM 10
#define API_VERSION "0.1"

/**
 * @brief API status enumerations.
 */
typedef enum {
    API_OK = 0,         /**< Operation successful */
    API_ERR_DB,         /**< Database error */
    API_ERR_NOT_FOUND,  /**< Resource not found */
    API_ERR_INVALID,    /**< Invalid input */
    API_ERR_NGROK       /**< Ngrok error */
} api_status_t;

/**
 * @brief Text command request structure.
 */
typedef struct {
    char text[512];     /**< Command text */
    room_id_t room;     /**< Target room */
    char user_id[64];   /**< User ID */
} text_cmd_request_t;

/**
 * @brief WebSocket event enumerations.
 */
typedef enum {
    WS_SENSOR_UPDATE,   /**< Sensor data update */
    WS_CMD_ACK,         /**< Command acknowledgment */
    WS_ALARM,           /**< Alarm event */
    WS_PROFILE_CHANGED  /**< Profile change */
} ws_event_t;

/**
 * @brief WebSocket message structure.
 */
typedef struct {
    ws_event_t event;           /**< Event type */
    sensor_snapshot_t sensor_data; /**< Sensor data */
    char payload_json[1024];    /**< JSON payload */
    uint32_t timestamp_ms;      /**< Timestamp */
} ws_message_t;

/**
 * @brief Command log entry structure.
 */
typedef struct {
    uint32_t id;                /**< Log entry ID */
    char user_text[512];        /**< Original user text */
    intent_t parsed_intent;     /**< Parsed intent */
    api_status_t result;        /**< Result status */
    uint32_t timestamp_ms;      /**< Timestamp */
} cmd_log_entry_t;

/**
 * @brief Initializes API backend.
 * @param db_path Database path.
 * @param port Server port.
 * @return API status.
 */
api_status_t api_init(const char *db_path, uint16_t port);

/**
 * @brief Starts FastAPI server and Ngrok.
 * @return API status.
 */
api_status_t api_start(void);

/**
 * @brief Handles text command request.
 * @param req Pointer to request.
 * @param out Pointer to output result.
 * @return API status.
 */
api_status_t api_handle_text_cmd(const text_cmd_request_t *req, intent_result_t *out);

/**
 * @brief Saves user profile to database.
 * @param profile Pointer to profile.
 * @return API status.
 */
api_status_t api_save_profile(const user_profile_t *profile);

/**
 * @brief Loads user profile from database.
 * @param name Profile name.
 * @param room Room ID.
 * @param out Pointer to output profile.
 * @return API status.
 */
api_status_t api_load_profile(const char *name, room_id_t room, user_profile_t *out);

/**
 * @brief Lists profiles for a room.
 * @param room Room ID.
 * @param profiles Pointer to profiles array.
 * @param count Pointer to count.
 * @return API status.
 */
api_status_t api_list_profiles(room_id_t room, user_profile_t *profiles, uint8_t *count);

/**
 * @brief Deletes user profile.
 * @param name Profile name.
 * @param room Room ID.
 * @return API status.
 */
api_status_t api_delete_profile(const char *name, room_id_t room);

/**
 * @brief Logs command to database.
 * @param entry Pointer to log entry.
 * @return API status.
 */
api_status_t api_log_command(const cmd_log_entry_t *entry);

/**
 * @brief Broadcasts message via WebSocket.
 * @param msg Pointer to message.
 * @return API status.
 */
api_status_t api_ws_broadcast(const ws_message_t *msg);

/**
 * @brief Shuts down API backend.
 */
void api_shutdown(void);

#endif /* MOD06_API_BACKEND_H */