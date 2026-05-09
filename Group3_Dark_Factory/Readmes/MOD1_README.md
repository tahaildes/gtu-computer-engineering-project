# MOD-01 — Ambient Control HAL

## Modül Amacı
[cite_start]Bu modül, fabrikanın fiziksel ortamını izlemek ve kontrol etmekten sorumlu Donanım Soyutlama Katmanıdır (HAL)[cite: 79, 80]. [cite_start]Sıcaklık, nem ve hava kalitesi verilerini toplar; fan, havalandırma kapağı ve sis üretici gibi aktüatörleri yönetir[cite: 81].

## Yazarlar
* [cite_start]Emirhan Çalışkan (220104004955) [cite: 77]
* [cite_start]Mehmet Akif Pekşen (230104004013) [cite: 77]

## Bağımlılıklar
* [cite_start]**Platform:** ESP-IDF v5.0 [cite: 76]
* [cite_start]**Donanım:** ESP32, BME280, MQ-135, MQ-2, Servo, DC Fan, Sis Üretici 
* [cite_start]**Dosyalar:** `factory_types.h` [cite: 43]

## API Özeti
| Fonksiyon | Parametreler | Dönüş Değeri | Açıklama |
| :--- | :--- | :--- | :--- |
| `ambient_hal_init` | `const ambient_config_t*` | `ambient_status_t` | [cite_start]I2C ve SPI buslarını başlatır[cite: 86]. |
| `ambient_hal_start_periodic` | `void` | `ambient_status_t` | [cite_start]Periyodik sensör okuma görevini başlatır[cite: 87]. |
| `ambient_hal_execute` | `const actuator_cmd_t*` | `ambient_status_t` | [cite_start]Gelen aktüatör komutunu icra eder[cite: 89, 98]. |
| `ambient_hal_set_fan` | `uint8_t duty_pct` | `void` | [cite_start]Fan hızını PWM ile ayarlar[cite: 98]. |

## Entegrasyon Örneği
Aşağıdaki kod parçası, modülün nasıl başlatılacağını ve bir komutun nasıl işleneceğini gösterir:

```c
#include "mod01_ambient_hal.h"

void app_main(void) {
    // 1. Donanım yapılandırması
    ambient_config_t cfg = { .i2c_sda_pin = 21, .i2c_scl_pin = 22 };
    
    // 2. Başlatma
    if (ambient_hal_init(&cfg) == AMBIENT_OK) {
        ambient_hal_start_periodic(); // Sensör okumaya başla
    }

    // 3. Örnek komut işleme (Fan %80)
    actuator_cmd_t cmd = { .device_type = DEV_FAN, .value_pct = 80, .state = 1 };
    ambient_hal_execute(&cmd);
}