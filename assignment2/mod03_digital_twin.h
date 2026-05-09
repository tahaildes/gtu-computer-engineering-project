#ifndef MOD03_DIGITAL_TWIN_H
#define MOD03_DIGITAL_TWIN_H

/**
 * @file    mod03_digital_twin.h
 * @brief   Digital Twin Core - Data aggregation, SQLite persistence and Rule Engine
 * @author  Taha Emirhan İldeş (240104004995), Yunus Emre Manav (210104004024) [cite: 117]
 * @date    2026-05-09
 * @version 0.1
 *
 * Changelog:
 * v0.1 - Initial draft: Twin instantiation, database integration, emergency triggers.
 */

#include "factory_types.h"

/* -- Data Types ----------------------------------------------------------- */

/** @brief Status codes for Digital Twin operations */
typedef enum {
    TWIN_OK         =  0,
    TWIN_ERR_DB     = -1,
    TWIN_ERR_MQTT   = -2
} twin_status_t;

/* -- Callback Types (For inter-module communication) ---------------------- */

/** * @brief Callback registered by MOD-04 to receive state updates.
 * In the Python implementation, this represents an in-process callback.
 */
typedef void (*twin_state_cb_t)(const twin_state_t *current_state);

/* -- Public Functions ----------------------------------------------------- */

/**
 * @brief  Initializes the Digital Twin module, connects to SQLite and MQTT broker.
 * @return TWIN_OK on success.
 */
twin_status_t twin_init(void);

/**
 * @brief  Registers a callback to be triggered when a new snapshot is generated.
 * @param  cb Callback function pointer.
 */
void twin_register_update_callback(twin_state_cb_t cb);

/**
 * @brief  Updates the twin state with new ambient sensor data from MOD-01.
 * @param  zone The zone where the data originated.
 * @param  data The newly arrived ambient_snapshot_t.
 */
void twin_update_ambient(zone_id_t zone, const ambient_snapshot_t *data);

/**
 * @brief  Updates the twin state with new machine telemetry from MOD-02.
 * @param  data The newly arrived machine_snapshot_t.
 */
void twin_update_machine(const machine_snapshot_t *data);

/**
 * @brief  Retrieves the most recent synchronized snapshot of the entire factory.
 * @param  out_state Pointer to caller-owned twin_state_t struct.
 * @return TWIN_OK if valid state is available.
 */
twin_status_t twin_get_state(twin_state_t *out_state);

/**
 * @brief  Rule Engine: Evaluates hardcoded thresholds and bypasses LLM if needed.
 * Triggers emergency actuator commands directly via MQTT (Priority Logic)[cite: 131].
 * @param  current_state The state to evaluate.
 */
void twin_trigger_emergency(const twin_state_t *current_state);

#endif /* MOD03_DIGITAL_TWIN_H */