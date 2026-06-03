// ============================================================
//  DARK FACTORY — ESP32 #1  SENSÖR DÜĞÜMÜ
//  Donanım : BME280 + MQ135i Modülü + MQ2 Modülü
//  Çıktı   : WiFi → Raspberry Pi HTTP API (POST /ingest/ambient)
//  Format  : Her 3 saniyede bir
// ============================================================
//
//  GEREKLİ KÜTÜPHANELER (Arduino IDE → Library Manager):
//    1. Adafruit BME280 Library   (by Adafruit)
//    2. Adafruit Unified Sensor   (by Adafruit)
//    3. ArduinoJson               (by Benoit Blanchon)
//
// ============================================================
//  PIN BAĞLANTILARI
// ============================================================
//
//  ── BME280 (I2C) ──────────────────────────────────────────
//  BME280 VCC   →  ESP32 3.3V
//  BME280 GND   →  ESP32 GND
//  BME280 SDA   →  ESP32 GPIO 21
//  BME280 SCL   →  ESP32 GPIO 22
//  BME280 CSB   →  ESP32 3.3V
//  BME280 SDO   →  ESP32 GND   (adres 0x76)
//
//  ── MQ135i Modülü (Hava Kalitesi — CO2/NH3) ──────────────
//  MQ135i VCC   →  ESP32 5V
//  MQ135i GND   →  ESP32 GND
//  MQ135i A-OUT →  ESP32 GPIO 34
//  MQ135i D-OUT →  ESP32 GPIO 35
//
//  ── MQ2 Modülü (LPG / Duman) ─────────────────────────────
//  MQ2 VCC      →  ESP32 5V
//  MQ2 GND      →  ESP32 GND
//  MQ2 A-OUT    →  ESP32 GPIO 32
//  MQ2 D-OUT    →  ESP32 GPIO 33
//
// ============================================================
//  AYARLAR — BURAYA KENDİ BİLGİLERİNİZİ GİRİN
// ============================================================

#define WIFI_SSID      "ZeynepS25"
#define WIFI_PASSWORD  "zeynep123"

#define API_HOST       "10.161.35.114"
#define API_PORT       8000
#define API_ENDPOINT   "/ingest/ambient"
#define ZONE_ID        "ZONE_A"

// ============================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_BME280.h>
#include <Adafruit_Sensor.h>
#include <ArduinoJson.h>
#include <esp_task_wdt.h>

// ── Pin Tanımları ──────────────────────────────────────────
#define PIN_MQ135I_AOUT   34
#define PIN_MQ135I_DOUT   35
#define PIN_MQ2_AOUT      32
#define PIN_MQ2_DOUT      33

// ── Zamanlama ──────────────────────────────────────────────
#define READ_INTERVAL_MS  3000
#define WDT_TIMEOUT_SEC   30
#define WIFI_TIMEOUT_MS   10000

// ── ADC ────────────────────────────────────────────────────
#define ADC_MAX   4095
#define ADC_VREF  3.3f

// ── Alarm Eşikleri ─────────────────────────────────────────
#define CO2_WARN_PPM   800
#define CO2_ALARM_PPM  1500
#define LPG_WARN_PPM   300
#define LPG_ALARM_PPM  500

// ── Kalibrasyon ────────────────────────────────────────────
#define MQ135I_R0_ADC  1100
#define MQ2_R0_ADC     1472

// ── BME280 ─────────────────────────────────────────────────
Adafruit_BME280 bme;
bool bmeOk = false;

unsigned long lastReadTime = 0;

// ── Watchdog ───────────────────────────────────────────────
void wdt_begin() {
  esp_task_wdt_config_t cfg = {
    .timeout_ms     = WDT_TIMEOUT_SEC * 1000,
    .idle_core_mask = 0,
    .trigger_panic  = true
  };
  esp_task_wdt_reconfigure(&cfg);
  esp_task_wdt_add(NULL);
}

// ── WiFi Bağlantısı ────────────────────────────────────────
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - start > WIFI_TIMEOUT_MS) return;
    delay(500);
    esp_task_wdt_reset();
  }
}

// ── ADC → PPM ──────────────────────────────────────────────
float adcToPPM_MQ135i(int adcVal) {
  if (adcVal <= 0) return 0;
  float voltage = adcVal * (ADC_VREF / ADC_MAX);
  if (voltage >= ADC_VREF) return 9999;
  float rs = ((ADC_VREF - voltage) / voltage) * 10.0f;
  float r0Voltage = MQ135I_R0_ADC * (ADC_VREF / ADC_MAX);
  float r0 = ((ADC_VREF - r0Voltage) / r0Voltage) * 10.0f;
  if (r0 <= 0) return 400;
  float ppm = 400.0f * pow(rs / r0, -2.0f);
  return constrain(ppm, 400.0f, 9999.0f);
}

float adcToPPM_MQ2(int adcVal) {
  if (adcVal <= 0) return 0;
  float voltage = adcVal * (ADC_VREF / ADC_MAX);
  if (voltage >= ADC_VREF) return 9999;
  float rs = ((ADC_VREF - voltage) / voltage) * 10.0f;
  float r0Voltage = MQ2_R0_ADC * (ADC_VREF / ADC_MAX);
  float r0 = ((ADC_VREF - r0Voltage) / r0Voltage) * 10.0f;
  if (r0 <= 0) return 100;
  float ratio = rs / r0;
  float ppm = 100.0f * pow(ratio, -2.222f);
  return constrain(ppm, 0.0f, 9999.0f);
}

// ── Alarm Seviyesi ─────────────────────────────────────────
String alarmLevel(float co2, float lpg) {
  if (lpg > LPG_ALARM_PPM || co2 > CO2_ALARM_PPM)  return "CRITICAL";
  if (lpg > LPG_WARN_PPM  || co2 > CO2_WARN_PPM)   return "WARNING";
  return "OK";
}

// ── SETUP ──────────────────────────────────────────────────
void setup() {
  wdt_begin();

  pinMode(PIN_MQ135I_DOUT, INPUT_PULLUP);
  pinMode(PIN_MQ2_DOUT,    INPUT_PULLUP);

  analogReadResolution(12);

  Wire.begin(21, 22);
  if      (bme.begin(0x76)) bmeOk = true;
  else if (bme.begin(0x77)) bmeOk = true;
  else                       bmeOk = false;

  if (bmeOk) {
    bme.setSampling(
      Adafruit_BME280::MODE_NORMAL,
      Adafruit_BME280::SAMPLING_X1,
      Adafruit_BME280::SAMPLING_X1,
      Adafruit_BME280::SAMPLING_X1,
      Adafruit_BME280::FILTER_OFF,
      Adafruit_BME280::STANDBY_MS_1000
    );
  }

  connectWiFi();
}

// ── LOOP ───────────────────────────────────────────────────
void loop() {
  esp_task_wdt_reset();

  unsigned long now = millis();
  if (now - lastReadTime < READ_INTERVAL_MS) return;
  lastReadTime = now;

  // BME280
  float temp     = bmeOk ? bme.readTemperature()       : 0;
  float humidity = bmeOk ? bme.readHumidity()          : 0;
  float pressure = bmeOk ? bme.readPressure() / 100.0f : 0;
  bool  bmeValid = bmeOk && !isnan(temp) && !isnan(humidity) && !isnan(pressure);

  // MQ sensörleri
  int   mq135iRaw = analogRead(PIN_MQ135I_AOUT);
  int   mq2Raw    = analogRead(PIN_MQ2_AOUT);
  float co2Ppm    = adcToPPM_MQ135i(mq135iRaw);
  float lpgPpm    = adcToPPM_MQ2(mq2Raw);
  String alarm    = alarmLevel(co2Ppm, lpgPpm);

  // JSON payload — lpg_ppm ve pressure_hpa eklendi
  JsonDocument doc;
  doc["zone_id"]       = ZONE_ID;
  doc["temperature_c"] = bmeValid ? round(temp     * 10.0f) / 10.0f : 0.0f;
  doc["humidity_pct"]  = bmeValid ? round(humidity * 10.0f) / 10.0f : 0.0f;
  doc["pressure_hpa"]  = bmeValid ? round(pressure * 10.0f) / 10.0f : 0.0f;
  doc["co2_ppm"]       = (float)(int)co2Ppm;
  doc["lpg_ppm"]       = (float)(int)lpgPpm;
  doc["timestamp_ms"]  = (unsigned long long)millis();

  String payload;
  serializeJson(doc, payload);

  // HTTP POST
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String url = "http://" + String(API_HOST) + ":" + String(API_PORT) + API_ENDPOINT;
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(payload);
    Serial.println(payload);
    http.end();
  } else {
    connectWiFi();
  }

  // Alarm varsa /ingest/alarm endpoint'ine de gönder
  if (alarm != "OK") {
    JsonDocument alarmDoc;
    alarmDoc["source_module"] = "MOD-01";
    alarmDoc["zone_id"]       = ZONE_ID;
    alarmDoc["timestamp_ms"]  = (unsigned long long)millis();

    String alarmField;
    float  alarmValue;
    float  alarmThreshold;

    if (co2Ppm > CO2_ALARM_PPM) {
      alarmField     = "co2_ppm";
      alarmValue     = co2Ppm;
      alarmThreshold = CO2_ALARM_PPM;
    } else if (lpgPpm > LPG_ALARM_PPM) {
      alarmField     = "lpg_ppm";
      alarmValue     = lpgPpm;
      alarmThreshold = LPG_ALARM_PPM;
    } else if (co2Ppm > CO2_WARN_PPM) {
      alarmField     = "co2_ppm";
      alarmValue     = co2Ppm;
      alarmThreshold = CO2_WARN_PPM;
    } else {
      alarmField     = "lpg_ppm";
      alarmValue     = lpgPpm;
      alarmThreshold = LPG_WARN_PPM;
    }

    alarmDoc["sensor_field"] = alarmField;
    alarmDoc["value"]        = alarmValue;
    alarmDoc["threshold"]    = alarmThreshold;

    String alarmPayload;
    serializeJson(alarmDoc, alarmPayload);

    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      String url = "http://" + String(API_HOST) + ":" + String(API_PORT) + "/ingest/alarm";
      http.begin(url);
      http.addHeader("Content-Type", "application/json");
      http.POST(alarmPayload);
      http.end();
    }
  }
}