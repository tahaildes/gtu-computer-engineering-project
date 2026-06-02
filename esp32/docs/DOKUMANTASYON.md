# DARK FACTORY — ESP32 Donanım Dokümantasyonu
### Gebze Teknik Üniversitesi | CSE 396 | Karanlık Fabrika Projesi

---

## İÇİNDEKİLER
1. Sistem Genel Bakışı
2. Gerekli Parçalar Listesi
3. Arduino IDE Kurulumu
4. ESP32 #1 — Sensör Düğümü
5. ESP32 #2 — Aktüatör Kontrolcüsü
6. ESP32 #3 — Kompresör Simülasyonu
7. Kodları Yükleme
8. Test ve Doğrulama
9. Sık Karşılaşılan Hatalar

---

## 1. SİSTEM GENEL BAKIŞI

```
┌─────────────────────────────────────────────────────────┐
│                    DARK FACTORY                         │
│                                                         │
│  ESP32 #1          ESP32 #2          ESP32 #3           │
│  [Sensör]          [Aktüatör]        [Makine Sim]       │
│  BME280            Fan               Kompresör          │
│  MQ135i Modülü     SG90 Servo        Sentetik Veri      │
│  MQ2 Modülü        Buzzer            NORMAL→FAILURE     │
│                    LED                                  │
│                    Nemlendirici                         │
│     │                  │                  │             │
│     └──────────────────┴──────────────────┘             │
│                        │                               │
│                  USB (Serial)                          │
│                        │                               │
│               ┌─────────────────┐                      │
│               │  Raspberry Pi 4 │                      │
│               │  /dev/ttyUSB0   │ ← ESP32 #1           │
│               │  /dev/ttyUSB1   │ ← ESP32 #2           │
│               │  /dev/ttyUSB2   │ ← ESP32 #3           │
│               └─────────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

**Veri Akışı:**
- ESP32 #1 → Serial → RPi: Ortam sensör verileri (3 sn'de bir)
- ESP32 #2 ← Serial ← RPi: Aktüatör komutları (ihtiyaç anında)
- ESP32 #2 → Serial → RPi: Aktüatör durum bildirimi
- ESP32 #3 → Serial → RPi: Kompresör telemetri (2 sn'de bir)

---

## 2. GEREKLİ PARÇALAR LİSTESİ

### Temel Elektronik
| Parça | Adet | Notlar |
|-------|------|--------|
| ESP32 Dev Module | 3 | 38-pin veya 30-pin, fark etmez |
| BME280 modülü | 1 | I2C versiyonu (4 pin) |
| MQ135i modülü | 1 | Hava kalitesi — A-OUT + D-OUT + VCC + GND |
| MQ2 modülü | 1 | LPG/duman — A-OUT + D-OUT + VCC + GND |
| DC Fan | 1 | 5V, 0.11A, 3x3cm |
| Servo SG90 | 1 | Mikro servo, havalandırma kapağı |
| Pasif Buzzer | 1 | Aktif değil, pasif olmalı |
| LED | 1 | Herhangi renk |
| Ultrasonik Nemlendirici | 1 | Kendi 5V adaptörüyle gelir |
| Raspberry Pi 4 | 1 | 4GB RAM önerilir |

> **Not:** MCP3008 ADC entegreleri artık gerekmemektedir. MQ135i ve MQ2 modülleri
> doğrudan ESP32'nin dahili 12-bit ADC pinlerine bağlanır.

### Devre Elemanları
| Parça | Adet | Notlar |
|-------|------|--------|
| 2N2222 Transistör | 2 | Fan ve Nemlendirici için NPN transistör |
| 220Ω Direnç | 1 | LED için |
| 1kΩ Direnç | 2 | Fan ve Nemlendirici transistör base için |
| 1N4007 Diyot | 1 | Fan koruma (varsa ekle) |
| Breadboard | 2-3 | Bağlantılar için |
| Jumper kablo | çok | Erkek-erkek, erkek-dişi |
| USB kablo | 3 | Veri kablosu (şarj değil!) |

---

## 3. ARDUINO IDE KURULUMU

### Adım 1: ESP32 Board Desteği
1. Arduino IDE aç → **File → Preferences**
2. "Additional boards manager URLs" kutusuna ekle:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. **Tools → Board → Boards Manager** aç
4. "esp32" ara → **esp32 by Espressif Systems** → Install

### Adım 2: Kütüphaneler
**Sketch → Include Library → Manage Libraries** aç, sırayla yükle:

| Kütüphane | Kim tarafından | Hangi ESP |
|-----------|----------------|-----------|
| ArduinoJson | Benoit Blanchon | #1, #2, #3 |
| Adafruit BME280 Library | Adafruit | #1 |
| Adafruit Unified Sensor | Adafruit | #1 |
| ESP32Servo | Kevin Harrington | #2 |

> MQ135i ve MQ2 modülleri için ek kütüphane gerekmez —
> ESP32'nin dahili `analogRead()` ve `digitalRead()` fonksiyonları kullanılır.

### Adım 3: Board Ayarları
Her ESP32 yüklemeden önce:
- **Tools → Board → ESP32 Arduino → ESP32 Dev Module**
- **Tools → Upload Speed → 115200**
- **Tools → Port → COMx** (Device Manager'dan kontrol et)

---

## 4. ESP32 #1 — SENSÖR DÜĞÜMÜ

### Görev
Ortam sensörlerinden veri okur, her 3 saniyede JSON formatında Serial'a yazar.

### Pin Bağlantıları

#### BME280 (I2C - Sıcaklık/Nem/Basınç)
```
BME280 Pin    →   ESP32 Pin
──────────────────────────
VCC           →   3.3V
GND           →   GND
SDA           →   GPIO 21
SCL           →   GPIO 22
CSB           →   3.3V     (I2C modunda HIGH olmalı)
SDO           →   GND      (I2C adres = 0x76)
```
> SDO'yu 3.3V'a bağlarsan adres 0x77 olur. Kodu değiştirmen gerekmez,
> otomatik algılar.

#### MQ135i Modülü (Hava Kalitesi — CO2/NH3)
```
MQ135i Pin    →   ESP32 Pin
───────────────────────────
VCC           →   5V
GND           →   GND
A-OUT         →   GPIO 34  (ADC1_CH6 — sadece giriş pini)
D-OUT         →   GPIO 35  (sadece giriş pini — aktif-LOW)
```

> **Önemli:** GPIO 34 ve 35, ESP32'de sadece giriş olarak kullanılabilen
> pinlerdir, OUTPUT modu yoktur — ADC için idealdir.
>
> **Voltaj kontrolü:** MQ135i modülü 5V ile beslense de A-OUT pini
> genellikle 0–3.3V arasında çıkış verir. Yine de bağlamadan önce
> voltmetre ile ölç; 3.3V üzeri ESP32 ADC'yi kalıcı olarak hasar verir.
>
> **D-OUT mantığı:** Modül üzerindeki potansiyometre ile ayarlanan eşik
> aşıldığında D-OUT pini LOW'a düşer (aktif-LOW). Potansiyometre ile
> hassasiyet ayarlanabilir.

#### MQ2 Modülü (LPG / Duman)
```
MQ2 Pin       →   ESP32 Pin
───────────────────────────
VCC           →   5V
GND           →   GND
A-OUT         →   GPIO 32  (ADC1_CH4)
D-OUT         →   GPIO 33  (aktif-LOW — eşik alarmı)
```

> **Not:** MCP3008 SPI ADC entegreleri artık kullanılmamaktadır.
> Eski devrendeki MCP3008'leri ve SPI kablolarını (GPIO 5, 17, 18, 19, 23)
> söküp kaldır.

#### GND Ortak Bağlantı
```
ESP32 GND
  ├── BME280 GND
  ├── MQ135i GND
  └── MQ2 GND
```

### Çıktı Formatı
```json
{
  "node": "sensor",
  "ts_ms": 9021,
  "temp_c": 24.5,
  "humidity_pct": 58.2,
  "pressure_hpa": 1013.1,
  "co2_ppm": 420,
  "lpg_ppm": 115,
  "mq135i_raw": 1587,
  "mq2_raw": 1024,
  "mq135i_dout": false,
  "mq2_dout": false,
  "alarm": "OK"
}
```

**Alan açıklamaları:**
- `mq135i_raw` / `mq2_raw` → Ham 12-bit ADC değeri (0–4095), kalibrasyon için
- `mq135i_dout` / `mq2_dout` → `true` = D-OUT LOW (modül eşiği aşıldı)
- `alarm` değerleri: `"OK"` / `"WARNING"` / `"CRITICAL"`

**alarm mantığı:**
- `"CRITICAL"` → D-OUT alarm aktif VEYA CO2 > 1500ppm VEYA LPG > 500ppm
- `"WARNING"`  → CO2 > 800ppm VEYA LPG > 300ppm
- `"OK"`       → Normal

### MQ Sensörü Kalibrasyon Notu
MQ sensörleri ilk kullanımda **24-48 saat ısınma süresi** gerektirir.
İlk açılışta yüksek değerler normaldir. Kalibrasyon için:
1. Sensörü temiz havada 48 saat çalıştır
2. Serial Monitor'dan `mq135i_raw` ve `mq2_raw` değerlerini not al
3. `esp32_1_sensor.ino` dosyasında şu satırları güncelle:
   ```cpp
   #define MQ135I_R0_ADC  580  // buraya ölçtüğün değeri yaz (0-4095)
   #define MQ2_R0_ADC     420  // buraya ölçtüğün değeri yaz (0-4095)
   ```

---

## 5. ESP32 #2 — AKTÜATÖR KONTROLCÜSÜ

### Görev
Raspberry Pi'dan gelen JSON komutlarını okur, fan/servo/buzzer/LED/nemlendiriciyi kontrol eder. Her komut sonrasında durumu bildirir.

### Pin Bağlantıları

#### DC Fan (5V, 0.11A) — 2N2222 Transistör ile
```
DEVRE ŞEMASI:

ESP32 GPIO13 ──[1kΩ]──── 2N2222 BASE  (orta bacak)
                          2N2222 EMITTER (sol bacak) ───── GND
                          2N2222 COLLECTOR (sağ bacak) ─── Fan (-)
ESP32 5V ──────────────────────────────────────────────── Fan (+)

          2N2222 (düz yüzü sana bakarken)
          E   B   C
         GND BASE FAN(-)

1N4007 diyot (varsa — fan ile paralel, ters yönde):
Fan (+) ──── Diyot Katot (çizgili taraf)
Fan (-) ──── Diyot Anot
```

#### Servo SG90 (Havalandırma Kapağı)
```
SG90 Kablo Rengi   →   Bağlantı
──────────────────────────────
Kırmızı            →   ESP32 5V
Kahverengi/Siyah   →   ESP32 GND
Sarı/Turuncu       →   ESP32 GPIO 15

Açı anlamları:
  0°   = Havalandırma kapağı tamamen kapalı
  90°  = Yarı açık
  180° = Tamamen açık
```

#### Pasif Buzzer
```
Buzzer (+) → ESP32 GPIO 16
Buzzer (-) → ESP32 GND

NOT: Aktif buzzer değil, PASİF buzzer kullan!
Aktif buzzer tek ton çıkarır, pasif buzzer frekans ayarlanabilir.
```

#### LED
```
GPIO 2 ──[220Ω]──── LED Anot (+, uzun bacak)
GND    ──────────── LED Katot (-, kısa bacak)
```

#### Nemlendirici (2N2222 Transistör ile)
```
DEVRE ŞEMASI:

ESP32 GPIO14 ──[1kΩ]──── 2N2222 BASE  (orta bacak)
                          2N2222 EMITTER (sol bacak) ───── GND
                          2N2222 COLLECTOR (sağ bacak) ─── Nemlendirici (-)
5V ──────────────────────────────────────────────────── Nemlendirici (+)

          2N2222 (düz yüzü sana bakarken)
          E   B   C
         GND BASE NEMLENDİRİCİ(-)

1N4007 diyot (varsa — nemlendirici ile paralel, ters yönde):
Nemlendirici (+) ──── Diyot Katot (çizgili taraf)
Nemlendirici (-) ──── Diyot Anot

NOT: Fan devresiyle tamamen aynı transistör mantığı.
     GPIO14 HIGH → transistör iletir → nemlendirici açılır.
```

### Komut Formatı (Raspberry → ESP32 #2)
```json
{"cmd": "fan",         "value": 80}      // Fan %80 hız
{"cmd": "fan",         "value": 0}       // Fan kapat
{"cmd": "servo_sg90",  "angle": 90}      // Kapağı yarı aç
{"cmd": "servo_sg90",  "angle": 180}     // Kapağı tam aç
{"cmd": "buzzer",      "state": 1}       // Buzzer aç (1000Hz)
{"cmd": "buzzer",      "state": 1, "freq": 2000}  // 2kHz ile aç
{"cmd": "buzzer",      "state": 0}       // Buzzer kapat
{"cmd": "led",         "state": 1}       // LED aç
{"cmd": "led",         "state": 0}       // LED kapat
{"cmd": "mist",        "state": 1}       // Nemlendirici aç
{"cmd": "mist",        "state": 0}       // Nemlendirici kapat
{"cmd": "status"}                        // Mevcut durumu bildir
{"cmd": "reset"}                         // Her şeyi kapat
```

### Çıktı Formatı (ESP32 #2 → Raspberry)
```json
{
  "node": "actuator",
  "fan_pct": 80,
  "sg90_angle": 90,
  "buzzer": false,
  "buzzer_freq": 1000,
  "led": true,
  "mist": false,
  "ts_ms": 12043
}
```

---

## 6. ESP32 #3 — KOMPRESöR SİMÜLASYONU

### Görev
Fiziksel sensör bağlı değil. Tamamen yazılımsal olarak kompresör
telemetri verisi üretir. Her 2 saniyede Raspberry'ye JSON gönderir.

### Bağlantı
```
Sadece USB kablosu → Raspberry Pi /dev/ttyUSB2

Hiçbir harici devre veya sensör bağlama!
BOOT butonu (GPIO 0) zaten kart üzerinde mevcut.
```

### Durum Makinesi ve Metrik Aralıkları

```
DURUM      | temp_c  | rpm         | vibration_g | pressure_bar
───────────────────────────────────────────────────────────────
NORMAL     | 33-45   | 1420-1480   | 0.15-0.40   | 7.5-8.5
HEATING    | 45-70   | 1380-1460   | 0.30-0.65   | 7.0-8.5
DEGRADING  | 70-88   | 1300-1420   | 0.50-1.50   | 5.5-7.5
CRITICAL   | 88-105  | 1100-1300   | 1.50-3.50   | 3.0-5.5
FAILURE    | 100-115 | 0-1100      | 3.50-8.00   | 0.0-3.0
```

### Manuel Test
BOOT butonuna bas → anında FAILURE durumuna geçer.
20 döngü (40 sn) sonra otomatik NORMAL'e döner.

### Çıktı Formatı
```json
{
  "node": "compressor",
  "state": "NORMAL",
  "temp_c": 36.4,
  "rpm": 1457,
  "vibration_g": 0.28,
  "pressure_bar": 8.12,
  "oil_temp_c": 41.3,
  "airflow_lpm": 278,
  "power_w": 753,
  "ts_ms": 4021
}
```

---

## 7. KODLARI YÜKLEME

### Her ESP32 için adımlar:

1. Arduino IDE'de **File → Open** ile ilgili `.ino` dosyasını aç
2. ESP32'yi USB ile bağla
3. **Tools → Board → ESP32 Dev Module** seç
4. **Tools → Port** → doğru COM portunu seç
5. **Upload** butonuna bas (→)
6. `Connecting...` yazısı çıkınca **BOOT butonuna basılı tut**
7. `Writing at 0x...` başlayınca BOOT'u bırak
8. `Hard resetting via RTS pin...` görününce yükleme tamam

> Bazı kartlarda BOOT'a basmak gerekmez, otomatik yüklenir.
> Eğer `Write timeout` hatası alırsan BOOT'a bas.

### Yükleme Sırası Önerilir:
1. ESP32 #3 (Kompresör) — en basit, test için ideal
2. ESP32 #1 (Sensör) — sensörleri bağladıktan sonra
3. ESP32 #2 (Aktüatör) — devreyi kurduktan sonra

---

## 8. TEST VE DOĞRULAMA

### Serial Monitor Testi
1. **Tools → Serial Monitor** (veya Ctrl+Shift+M)
2. Sağ altta **115200 baud** seç
3. Beklenen çıktılar:

**ESP32 #1 ilk açılışta:**
```json
{"boot":"sensor_esp_ready","node":"sensor","bme280":"ok"}
```
Sonra her 3 saniyede:
```json
{"node":"sensor","ts_ms":3021,"temp_c":24.5,"humidity_pct":58.2,"pressure_hpa":1013.1,"co2_ppm":420,"lpg_ppm":115,"mq135i_raw":1587,"mq2_raw":1024,"mq135i_dout":false,"mq2_dout":false,"alarm":"OK"}
```

**ESP32 #2 ilk açılışta:**
```json
{"boot":"actuator_esp_ready","node":"actuator"}
{"node":"actuator","fan_pct":0,"sg90_angle":0,"buzzer":false,"buzzer_freq":1000,"led":false,"mist":false,"ts_ms":1204}
```

**ESP32 #3 ilk açılışta:**
```json
{"boot":"compressor_sim_ready","node":"compressor"}
{"node":"compressor","state":"NORMAL","temp_c":36.4,"rpm":1457,"vibration_g":0.28,"pressure_bar":8.12,"oil_temp_c":41.3,"airflow_lpm":278,"power_w":753,"ts_ms":2021}
```

### ESP32 #1 MQ Modülü Testi
- `mq135i_raw` ve `mq2_raw` → 0 ile 4095 arasında değer gelmeli (12-bit ADC)
- `mq135i_dout` ve `mq2_dout` → Normal ortamda `false` olmalı
- Modül üzerindeki potansiyometre ile D-OUT hassasiyeti ayarlanabilir

### ESP32 #2 Manuel Test
Serial Monitor'da (satır sonu "Newline" olarak ayarla):
```json
{"cmd":"led","state":1}
```
→ LED yanmalı, JSON durum bildirimi gelmeli.

```json
{"cmd":"fan","value":50}
```
→ Fan %50 hızda dönmeli.

```json
{"cmd":"reset"}
```
→ Her şey kapanmalı.

---

## 9. SIK KARŞILAŞILAN HATALAR

| Hata | Sebep | Çözüm |
|------|-------|-------|
| `Write timeout` | Port meşgul veya USB | Serial Monitor kapat, BOOT'a bas |
| `COM port not found` | Driver yok | CP2102 veya CH340 driver yükle |
| `BME280 not found` | Yanlış adres veya bağlantı | SDO pinini kontrol et, 0x76 vs 0x77 |
| MQ sensörü çok yüksek | Isınmadı | 48 saat bekle |
| `mq135i_raw` = 0 sürekli | Pin bağlı değil veya yanlış | GPIO 34'ü kontrol et |
| `mq135i_raw` = 4095 sürekli | A-OUT voltajı 3.3V üzeri | Voltmetre ile ölç, gerekirse direnç bölen ekle |
| D-OUT her zaman true | Potansiyometre hassasiyeti yüksek | Modül üzerindeki trimpot'u ayarla |
| Servo titriyor | Yetersiz güç | 5V hattı ayrı besleme kullan |
| Fan dönmüyor | Transistör ters | 2N2222 bacak sırasını kontrol et |
| Buzzer ses yok | Aktif buzzer | Pasif buzzer kullan |
| `ArduinoJson.h not found` | Kütüphane yok | Library Manager'dan yükle |

---

## GND ORTAK BAĞLANTI — KRİTİK!

Tüm devrelerin GND'si birbirine bağlı olmalı:
```
ESP32 GND
  ├── Breadboard GND hattı
  ├── BME280 GND
  ├── MQ135i GND
  ├── MQ2 GND
  ├── 2N2222 EMITTER (Fan devresi)
  ├── SG90 GND (kahverengi)
  ├── Buzzer (-)
  ├── LED Katot (-)
  └── Nemlendirici devresi GND (2N2222 EMITTER)
```

GND ortak değilse sensörler yanlış okur, servo titrer, fan çalışmaz.

---

*Dark Factory — Gebze Teknik Üniversitesi CSE 396*
