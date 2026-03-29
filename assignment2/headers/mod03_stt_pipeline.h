/**
 * @file mod03_stt_pipeline.h
 * @brief Pipeline for Audio & Speech-to-Text using Porcupine & Whisper.
 * @author Taha Emirhan İldeş (ID: 240104004995), Yunus Emre Manav (ID: 210104004024), Zeynep Sude Turan (ID: 220104004031)
 * @date 2026-03-28
 * @version 0.1
 *
 * Changelog:
 * v0.1 (2026-03-28) - Initial STT pipeline interface
 */

#ifndef MOD03_STT_PIPELINE_H
#define MOD03_STT_PIPELINE_H

#include <stdint.h>
#include <stdbool.h>

/* Constants */
#define STT_SAMPLE_RATE_HZ 16000
#define STT_CHANNELS 1
#define STT_CHUNK_DURATION_MS 30
#define STT_WHISPER_MODEL "base"
#define STT_LANGUAGE "tr"
#define STT_MAX_RECORD_DURATION_S 10
#define STT_SILENCE_TIMEOUT_MS 1500
#define STT_WAKE_WORD_SENSITIVITY 0.7f
#define STT_WER_TARGET 0.15f

/**
 * @brief STT state enumerations.
 */
typedef enum {
    STT_IDLE,           /**< Idle state */
    STT_LISTENING_WAKE, /**< Listening for wake word */
    STT_RECORDING,      /**< Recording audio */
    STT_TRANSCRIBING,   /**< Transcribing audio */
    STT_ERROR           /**< Error state */
} stt_state_t;

/**
 * @brief STT status enumerations.
 */
typedef enum {
    STT_OK = 0,         /**< Operation successful */
    STT_ERR_MIC_INIT,   /**< Microphone initialization error */
    STT_ERR_WAKE_WORD,  /**< Wake word detection error */
    STT_ERR_WHISPER,    /**< Whisper transcription error */
    STT_ERR_TIMEOUT     /**< Timeout error */
} stt_status_t;

/**
 * @brief STT result structure.
 */
typedef struct {
    char transcription[512]; /**< Transcribed text */
    float confidence;        /**< Confidence score */
    uint32_t duration_ms;    /**< Recording duration */
    stt_status_t status;     /**< Status */
} stt_result_t;

/**
 * @brief STT configuration structure.
 */
typedef struct {
    uint16_t sample_rate;                    /**< Sample rate */
    uint8_t channels;                        /**< Audio channels */
    char whisper_model[16];                  /**< Whisper model name */
    char language[8];                        /**< Language code */
    float wake_word_sensitivity;             /**< Wake word sensitivity */
    uint32_t max_record_duration_ms;         /**< Max recording duration */
    void (*on_result)(const stt_result_t *result); /**< Result callback */
} stt_config_t;

/* Callback typedef */
typedef void (*stt_result_cb_t)(const stt_result_t *result);

/**
 * @brief Initializes STT pipeline.
 * @param cfg Pointer to STT configuration.
 * @return STT status.
 */
stt_status_t stt_init(const stt_config_t *cfg);

/**
 * @brief Starts continuous wake word detection loop.
 * @return STT status.
 */
stt_status_t stt_start_listening(void);

/**
 * @brief Stops STT pipeline.
 */
void stt_stop(void);

/**
 * @brief Transcribes audio from WAV file.
 * @param wav_path Path to WAV file.
 * @param out Pointer to output result.
 * @return STT status.
 */
stt_status_t stt_transcribe_file(const char *wav_path, stt_result_t *out);

/**
 * @brief Gets current STT state.
 * @return Current state.
 */
stt_state_t stt_get_state(void);

/**
 * @brief Loads Porcupine wake word model.
 * @param keyword_path Path to keyword file.
 * @return STT status.
 */
stt_status_t stt_set_wake_word(const char *keyword_path);

#endif /* MOD03_STT_PIPELINE_H */