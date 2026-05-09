#ifndef MOD04_PREDICTIVE_ENGINE_H
#define MOD04_PREDICTIVE_ENGINE_H

/**
 * @file    mod04_predictive_engine.h
 * @brief   Cognitive Predictive Engine - LLM-based anomaly detection and maintenance
 * @author  Ahmet Burak Çelebi (220104004885), Burak Kurtaran (210104004240)
 * @date    2026-05-09
 * @version 0.1
 *
 * Changelog:
 * v0.1 - Initial draft: LLM inference orchestration and priority logic.
 */

#include "factory_types.h"

/* -- Constants ------------------------------------------------------------ */
/** @brief LLM Inference frequency in seconds (Normal cycle) */
#define LLM_ANALYSIS_INTERVAL_SEC 60

/* -- Data Types ----------------------------------------------------------- */

typedef enum {
    LLM_OK                =  0,
    LLM_ERR_OLLAMA_CONN   = -1,
    LLM_ERR_VALIDATION    = -2, /**< Invalid JSON or schema mismatch */
    LLM_ERR_TIMEOUT       = -3
} llm_status_t;

/* -- Public Functions ----------------------------------------------------- */

/**
 * @brief  Initializes the LLM engine and checks connection to Ollama API.
 * Loads Qwen 2.5 3B model into memory.
 * @return LLM_OK on success.
 */
llm_status_t llm_engine_init(void);

/**
 * @brief  Main entry point for analyzing factory state.
 * Orchestrates prompt construction with context window (last 30 snapshots).
 * @param  state The latest twin_state_t snapshot.
 * @param  out_report Pointer to store the generated maintenance_report_t.
 * @return LLM_OK on successful inference.
 */
llm_status_t llm_analyze_state(const twin_state_t *state, maintenance_report_t *out_report);

/**
 * @brief  Priority Logic: Checks if real-world anomalies should override simulation.
 * Ensures the system focuses on real sensor data over MOD-02 synthetic data.
 * @param  state Current factory state.
 * @return True if real-world issues are prioritized.
 */
uint8_t llm_check_priority_logic(const twin_state_t *state);

/**
 * @brief  Validates the LLM output against the maintenance_report_t schema.
 * @param  json_response Raw string from LLM.
 * @return LLM_OK if valid.
 */
llm_status_t llm_validate_output(const char *json_response);

#endif /* MOD04_PREDICTIVE_ENGINE_H */