#ifndef MOD02_MACHINE_SIM_H
#define MOD02_MACHINE_SIM_H

/**
 * @file    mod02_machine_sim.h
 * @brief   Machine Simulation Hardware Abstraction Layer
 * @author  Dilara Gözen (230104004065), Zeynep Sude Turan (220104004031) [cite: 102]
 * @date    2026-05-09
 * @version 0.1
 *
 * Changelog:
 * v0.1 - Initial draft: State machine, error injection, and synthetic telemetry.
 */

#include <stdint.h>
#include "factory_types.h" /* Shared canonical data structures */

/* -- Constants ------------------------------------------------------------ */
#define SIM_TELEMETRY_INTERVAL_MS 2000

/* -- Data Types ----------------------------------------------------------- */

/** @brief Operational states of the simulated machine [cite: 113] */
typedef enum {
    MACHINE_STATE_NORMAL    = 0,
    MACHINE_STATE_DEGRADING = 1,
    MACHINE_STATE_FAULT     = 2
} machine_state_t;

/** @brief Status codes for Simulation HAL */
typedef enum {
    MACHINE_SIM_OK       =  0,
    MACHINE_SIM_ERR_INIT = -1
} machine_sim_status_t;

/* -- Public Functions ----------------------------------------------------- */

/**
 * @brief  Initializes the simulation hardware (RGB LED, BOOT Button). [cite: 111, 114]
 * @return MACHINE_SIM_OK on success.
 */
machine_sim_status_t machine_sim_init(void);

/**
 * @brief  Starts the FreeRTOS task generating synthetic telemetry.
 * Generates rpm, vibration, power, and temp based on the current machine state.
 * @return MACHINE_SIM_OK on success.
 */
machine_sim_status_t machine_sim_start_task(void);

/**
 * @brief  Forces the state machine into a specific state (Error Injection). [cite: 106, 113]
 * Typically triggered by the BOOT button to simulate a sudden fault. [cite: 114]
 * @param  new_state The target state (e.g., MACHINE_STATE_FAULT).
 */
void machine_sim_set_state(machine_state_t new_state);

/**
 * @brief  Retrieves the current synthetic state of the machine.
 * @return Current machine_state_t enum value.
 */
machine_state_t machine_sim_get_state(void);

#endif /* MOD02_MACHINE_SIM_H */