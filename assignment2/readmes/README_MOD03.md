# MOD03 Audio & STT Pipeline

One-sentence purpose: Provides a pipeline for wake word detection using Porcupine and speech-to-text using Whisper.

**Note**: This module's header (mod03_stt_pipeline.h) specifies C interfaces, but the actual implementation is Python-based. The C headers define the contract for embedded system integration; Python implementation provides Whisper/Porcupine processing.

## Authors

- Taha Emirhan İldeş (ID: 240104004995)
- Yunus Emre Manav (ID: -)
- Zeynep Sude Turan (ID: 220104004031)

## Dependencies

**Module Dependencies:** None  
**External Dependencies:**
- Python 3.8+
- Libraries: `porcupine`, `openai-whisper`, `pyaudio`
- `project_types.h` (for interface specification)

## Quick Start

```python
from mod03_stt_pipeline import stt_init, stt_start_listening

cfg = {
    "sample_rate": 16000,
    "channels": 1,
    "whisper_model": "base",
    "language": "tr",
    "wake_word_sensitivity": 0.7,
    "max_record_duration_ms": 10000,
    "on_result": my_callback
}

stt_init(cfg)
stt_start_listening()
# Wake word detection starts, callbacks on transcription
```

## C-Python Integration

Since this module presents C header interfaces but runs Python implementation:
- **Callbacks**: STT results (stt_result_t) are returned via Python callback functions.
- **MQTT Bridge**: Python sends results to MOD04 via in-process callback or MQTT topic.
- **Code Linking**: Embedding projects should use ctypes or CFFI to wrap Python functions, or define a REST/Socket bridge layer.
- **Example**: For Raspberry Pi integration, MOD03 Python output → MQTT `home/audio/stt` → MOD04 listens and parses.

## API Summary

| Function              | Parameters                                | Return         | Notes                             |
| --------------------- | ----------------------------------------- | -------------- | --------------------------------- |
| `stt_init`            | `const stt_config_t *cfg`                 | `stt_status_t` | Initializes microphone and models |
| `stt_start_listening` | (none)                                    | `stt_status_t` | Starts wake word detection loop   |
| `stt_stop`            | (none)                                    | `void`         | Stops pipeline                    |
| `stt_transcribe_file` | `const char *wav_path, stt_result_t *out` | `stt_status_t` | Transcribes WAV file              |
| `stt_get_state`       | (none)                                    | `stt_state_t`  | Gets current state                |
| `stt_set_wake_word`   | `const char *keyword_path`                | `stt_status_t` | Loads custom wake word model      |

## Known Limitations

- Requires internet connection for Whisper API if not using local model
- Wake word detection may have false positives in noisy environments
- Turkish language support limited to Whisper's training data
- Maximum recording duration fixed at 10 seconds

## TODOs

- Add support for multiple wake words
- Implement noise reduction preprocessing
- Add voice activity detection (VAD) for better segmentation
- Support for additional languages beyond Turkish

## Version History

- v0.1 (2026-03-28) - Initial STT pipeline implementation
