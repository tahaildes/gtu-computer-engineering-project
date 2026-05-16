# MOD-02 — Makine Simülasyon HAL

## Modül Amacı
[cite_start]MOD-02, karanlık fabrikadaki makine düğümü olarak görev yapar ve herhangi bir fiziksel sensör barındırmaz[cite: 105]. [cite_start]Veriler tamamen yazılımsal olarak sahte (sentetik) üretilir ve sisteme kasıtlı hata enjeksiyonu (error injection) yapılarak kestirimci motorun test edilmesi sağlanır[cite: 106, 109].

## Yazarlar
* [cite_start]Dilara Gözen (230104004065) [cite: 102]
* [cite_start]Zeynep Sude Turan (220104004031) [cite: 102]

## Bağımlılıklar
* [cite_start]**Platform:** ESP-IDF v5.0 [cite: 101]
* [cite_start]**Donanım:** ESP32 #3, RGB LED (GPIO 4, 5, 6), Dokunmatik BOOT Butonu (GPIO 0) [cite: 101, 111]
* **Dosyalar:** `factory_types.h`

## API Özeti
| Fonksiyon | Parametreler | Dönüş Değeri | Açıklama |
| :--- | :--- | :--- | :--- |
| `machine_sim_init` | `void` | `machine_sim_status_t` | Simülasyon donanımını (LED, Buton) başlatır. |
| `machine_sim_start_task` | `void` | `machine_sim_status_t` | Sentetik telemetri üreten FreeRTOS görevini başlatır. |
| `machine_sim_set_state` | `machine_state_t` | `void` | Sistemi istenen duruma zorlar (Hata Enjeksiyonu). |
| `machine_sim_get_state` | `void` | `machine_state_t` | Mevcut makine durumunu (NORMAL, DEGRADING, FAULT) döndürür. |

## Entegrasyon Örneği
Aşağıdaki kod, simülasyonun nasıl başlatılacağını ve manuel bir hata durumunun nasıl tetikleneceğini gösterir:

```c
#include "mod02_machine_sim.h"

void app_main(void) {
    // 1. Simülasyon donanımlarını başlat
    if (machine_sim_init() == MACHINE_SIM_OK) {
        // 2. Sentetik veri üretimi task'ını başlat
        machine_sim_start_task();
    }

    // 3. (Örnek) Butona basıldığında manuel arıza enjeksiyonu
    // Gerçekte bu işlem ISR (Interrupt Service Routine) içinde yapılır.
    machine_sim_set_state(MACHINE_STATE_FAULT);
}