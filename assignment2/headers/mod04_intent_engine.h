/**
 * @file mod04_intent_engine.h
 * @brief LLM Intent parsing API specification using Qwen 2.5 3B.
 * @author Taha Emirhan İldeş (ID: 240104004995), Yunus Emre Manav (ID: 210104004024), Ahmet Burak Çelebi (ID: 220104004885)
 * @date 2026-03-28
 * @version 0.1
 *
 * Changelog:
 * v0.1 (2026-03-28) - Initial intent engine interface
 */

#ifndef MOD04_INTENT_ENGINE_H
#define MOD04_INTENT_ENGINE_H

#include <stdint.h>
#include <stdbool.h>
#include "project_types.h"

/* Constants */
#define INTENT_LLM_MODEL "qwen2.5:3b"
#define INTENT_MAX_TOKENS 256
#define INTENT_TEMPERATURE 0.1f
#define INTENT_TIMEOUT_MS 10000
#define INTENT_MAX_COMMANDS_PER_INTENT 8
#define INTENT_ACCURACY_TARGET 0.85f
#define INTENT_OLLAMA_URL "http://localhost:11434/api/chat"

/**
 * @brief Intent status enumerations.
 */
typedef enum {
    INTENT_OK = 0,              /**< Operation successful */
    INTENT_ERR_LLM_TIMEOUT,     /**< LLM timeout */
    INTENT_ERR_VALIDATION,      /**< Validation error */
    INTENT_ERR_UNKNOWN_CMD,     /**< Unknown command */
    INTENT_ERR_OLLAMA           /**< Ollama error */
} intent_status_t;

/**
 * @brief LLM request structure.
 */
typedef struct {
    char user_text[512];        /**< User input text */
    sensor_snapshot_t sensor_ctx; /**< Sensor context */
    user_profile_t active_profile; /**< Active user profile */
    char room_hint[32];         /**< Room hint */
} llm_request_t;

/**
 * @brief Intent result structure.
 */
typedef struct {
    intent_t intent;            /**< Parsed intent */
    intent_status_t status;     /**< Status */
    uint32_t inference_ms;      /**< Inference time */
    float confidence;           /**< Confidence score */
} intent_result_t;

/* Callback typedef */
typedef void (*intent_cb_t)(const intent_result_t *result);

/**
 * @brief Initializes intent engine.
 * @param model_name LLM model name.
 * @param ollama_url Ollama URL.
 * @return Intent status.
 */
intent_status_t intent_engine_init(const char *model_name, const char *ollama_url);

/**
 * @brief Parses text to intent.
 * @param req Pointer to LLM request.
 * @param out Pointer to output result.
 * @return Intent status.
 */
intent_status_t intent_engine_parse(const llm_request_t *req, intent_result_t *out);

/**
 * @brief Loads few-shot examples.
 * @param json_path Path to JSON file.
 * @return Intent status.
 */
intent_status_t intent_engine_load_few_shots(const char *json_path);

/**
 * @brief Sets latest sensor data.
 * @param snap Pointer to sensor snapshot.
 */
void intent_engine_set_sensor_context(const sensor_snapshot_t *snap);

/**
 * @brief Sets active user profile.
 * @param profile Pointer to user profile.
 */
void intent_engine_set_active_profile(const user_profile_t *profile);

/**
 * @brief Validates JSON string to intent.
 * @param json_str JSON string.
 * @param out Pointer to output intent.
 * @return Intent status.
 */
intent_status_t intent_engine_validate(const char *json_str, intent_t *out);

/**
 * @brief Shuts down intent engine.
 */
void intent_engine_shutdown(void);

#endif /* MOD04_INTENT_ENGINE_H */