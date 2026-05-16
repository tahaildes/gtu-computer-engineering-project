#ifndef MOD05_API_DASHBOARD_H
#define MOD05_API_DASHBOARD_H

/**
 * @file    mod05_api_dashboard.h
 * @brief   Industrial API and Dashboard - REST, WebSocket, and React Interface
 * @author  Dark Factory Core Team
 * @date    2026-05-09
 * @version 0.1
 *
 * Changelog:
 * v0.1 - Initial draft: API endpoints, WebSocket broadcasting, and Manual Control.
 */

#include "factory_types.h"

/* -- Constants ------------------------------------------------------------ */
#define API_PORT_HTTP       8000  /**< FastAPI REST/WS Port */
#define API_PORT_FRONTEND   5173  /**< React/Vite Dev Port */

/* -- Data Types ----------------------------------------------------------- */

/** @brief Status codes for API operations */
typedef enum {
    API_OK              =  0,
    API_ERR_SERVER      = -1,
    API_ERR_WEBSOCKET   = -2
} api_status_t;

/* -- Public Functions (Backend Interface) --------------------------------- */

/**
 * @brief  Initializes the FastAPI backend server and prepares WebSocket routes.
 * @return API_OK on success.
 */
api_status_t api_server_init(void);

/**
 * @brief  Broadcasts the latest Digital Twin state to all connected React clients.
 * Uses WebSockets for real-time dashboard updates.
 * @param  current_state Pointer to the latest twin_state_t.
 * @return API_OK on successful broadcast.
 */
api_status_t api_broadcast_state(const twin_state_t *current_state);

/**
 * @brief  Broadcasts the latest LLM thought process and maintenance report.
 * Allows the operator to read the LLM reasoning live on the dashboard.
 * @param  report Pointer to the maintenance_report_t.
 * @return API_OK on success.
 */
api_status_t api_broadcast_llm_report(const maintenance_report_t *report);

/**
 * @brief  Handles incoming manual actuator commands from the React frontend.
 * Disables LLM autonomy for the targeted device and routes the command to MOD-03.
 * @param  cmd Command payload received via POST /actuator/cmd.
 * @return API_OK if the command is successfully parsed and routed.
 */
api_status_t api_handle_manual_override(const actuator_cmd_t *cmd);

#endif /* MOD05_API_DASHBOARD_H */