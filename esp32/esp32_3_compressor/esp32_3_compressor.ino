// ============================================================
//  DARK FACTORY — ESP32 #3  KOMPRESöR SİMÜLASYONU
//  Fiziksel sensör yok — tamamen sentetik veri üretimi
//  Çıktı: WiFi → Raspberry Pi HTTP API (POST /telemetry)
//         Serial 115200 → Debug / izleme
// ============================================================
//
//  GEREKLİ KÜTÜPHANELER:
//    1. ArduinoJson  (by Benoit Blanchon)
//    (WiFi ve HTTPClient ESP32 core ile birlikte gelir)
//
//  BAĞLANTILAR:
//    Sadece USB kablosu (güç için)
//    GPIO 0 (BOOT butonu) → manuel FAILURE tetikler
//    Hiçbir harici sensör veya devre BAĞLAMA!
//
// ============================================================
//  AYARLAR — BURAYA KENDİ BİLGİLERİNİZİ GİRİN
// ============================================================

#define WIFI_SSID      "emr"
#define WIFI_PASSWORD  "00000000"

// Raspberry Pi'ın sabit IP'si (router'dan sabitlemen önerilir)
#define API_HOST       "172.20.10.5"
#define API_PORT       8000
#define API_ENDPOINT   "/ingest/machine"
// ============================================================
//  DURUM MAKİNESİ
// ============================================================
//
//   ┌─────────┐  %1 şans    ┌─────────┐  20 döngü  ┌───────────┐
//   │ NORMAL  │ ──────────► │ HEATING │ ──────────► │ DEGRADING │
//   └─────────┘             └─────────┘             └───────────┘
//        ▲                                                │
//        │  reset (30 döngü)                         25 döngü
//        │                                                ▼
//   ┌─────────┐             ┌──────────┐  15 döngü  ┌──────────┐
//   │ NORMAL  │ ◄────────── │ FAILURE  │ ◄────────── │ CRITICAL │
//   └─────────┘             └──────────┘             └──────────┘
//
//   BOOT butonu basılı → anında FAILURE
//
// ============================================================
//  METRİK REFERANS TABLOSU
// ============================================================
//
//  Metrik        NORMAL       HEATING      DEGRADING    CRITICAL     FAILURE
//  temp_c        33-46        43-72        68-90        86-108       98-115
//  rpm           1415-1485    1370-1465    1290-1430    1080-1310    0-1120
//  vibration_g   0.10-0.45    0.28-0.70    0.45-1.60    1.40-3.60   3.20-8.00
//  pressure_bar  7.4-8.6      6.8-8.6      5.2-7.8      2.8-5.8     0.0-3.2
//  oil_temp_c    37-49        46-67        63-82        78-97        93-115
//  airflow_lpm   262-298      245-275      215-268      155-225      0-165
//  power_w       748-772      790-1020     980-1230     1080-1470    300-580
//
// ============================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <esp_task_wdt.h>

// ── Zamanlama ──────────────────────────────────────────────
#define SEND_INTERVAL_MS   2000
#define WDT_TIMEOUT_SEC      30
#define WIFI_TIMEOUT_MS    10000

// ── Durum Makinesi ─────────────────────────────────────────
enum MachineState { NORMAL, HEATING, DEGRADING, CRITICAL, FAILURE };
MachineState currentState  = NORMAL;
MachineState previousState = NORMAL;

// ── Kompresör Metrikleri ───────────────────────────────────
float machineTemp = 38.0f;
float rpm         = 1452.0f;
float vibration   = 0.22f;
float pressureBar = 8.1f;
float oilTemp     = 42.0f;
float airflowLpm  = 279.0f;
float powerW      = 754.0f;

// ── Sayaçlar ───────────────────────────────────────────────
int  stateCounter    = 0;
int  transitionTicks = 0;
bool manualFault     = false;

unsigned long lastSendTime = 0;

// ============================================================
//  Yardımcılar
// ============================================================
float frand(int minX10, int maxX10) {
  int range = maxX10 - minX10;
  if (range <= 0) return minX10 / 10.0f;
  return (minX10 + (int)(random(range + 1))) / 10.0f;
}

float softMove(float current, float target, float rate = 0.30f) {
  return current + (target - current) * rate;
}

const char* stateToString(MachineState s) {
  switch (s) {
    case NORMAL:    return "NORMAL";
    case HEATING:   return "HEATING";
    case DEGRADING: return "DEGRADING";
    case CRITICAL:  return "CRITICAL";
    case FAILURE:   return "FAILURE";
  }
  return "UNKNOWN";
}

void resetMetrics() {
  machineTemp     = 38.0f;
  rpm             = 1452.0f;
  vibration       = 0.22f;
  pressureBar     = 8.1f;
  oilTemp         = 42.0f;
  airflowLpm      = 279.0f;
  powerW          = 754.0f;
  stateCounter    = 0;
  transitionTicks = 0;
  manualFault     = false;
  previousState   = NORMAL;
}

// ============================================================
//  Watchdog
// ============================================================
void wdt_begin() {
  esp_task_wdt_config_t cfg = {
    .timeout_ms     = WDT_TIMEOUT_SEC * 1000,
    .idle_core_mask = 0,
    .trigger_panic  = true
  };
  esp_task_wdt_reconfigure(&cfg);
  esp_task_wdt_add(NULL);
}

// ============================================================
//  WiFi Bağlantısı
// ============================================================
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

// ============================================================
//  Durum Geçiş Mantığı
// ============================================================
void updateState() {
  if (digitalRead(0) == LOW) manualFault = true;

  if (manualFault && currentState != FAILURE) {
    previousState   = currentState;
    currentState    = FAILURE;
    stateCounter    = 0;
    transitionTicks = 0;
    return;
  }

  stateCounter++;

  switch (currentState) {
    case NORMAL:
      stateCounter = 0;
      if (random(1000) < 10) {
        previousState   = NORMAL;
        currentState    = HEATING;
        transitionTicks = 0;
      }
      break;

    case HEATING:
      if (stateCounter >= 20) {
        previousState   = HEATING;
        currentState    = DEGRADING;
        stateCounter    = 0;
        transitionTicks = 0;
      }
      break;

    case DEGRADING:
      if (stateCounter >= 25) {
        previousState   = DEGRADING;
        currentState    = CRITICAL;
        stateCounter    = 0;
        transitionTicks = 0;
      }
      break;

    case CRITICAL:
      if (stateCounter >= 15) {
        previousState   = CRITICAL;
        currentState    = FAILURE;
        stateCounter    = 0;
        transitionTicks = 0;
      }
      break;

    case FAILURE:
      if (stateCounter >= 30) {
        currentState = NORMAL;
        resetMetrics();
      }
      break;
  }
}

// ============================================================
//  Metrik Güncelleme
// ============================================================
void updateMetrics() {
  transitionTicks++;

  switch (currentState) {

    case NORMAL:
      machineTemp += frand(-3, 4) * 0.1f;
      rpm         += frand(-10, 10);
      vibration   += frand(-2, 2) * 0.01f;
      pressureBar += frand(-2, 2) * 0.04f;
      oilTemp     += frand(-2, 2) * 0.1f;
      airflowLpm  += frand(-4, 4);
      powerW       = 754.0f + (machineTemp - 38.0f) * 1.5f + frand(-3, 3);

      machineTemp = constrain(machineTemp,  33.0f,  46.0f);
      rpm         = constrain(rpm,        1415.0f, 1485.0f);
      vibration   = constrain(vibration,    0.10f,   0.45f);
      pressureBar = constrain(pressureBar,  7.40f,   8.60f);
      oilTemp     = constrain(oilTemp,     37.0f,   49.0f);
      airflowLpm  = constrain(airflowLpm, 262.0f,  298.0f);
      powerW      = constrain(powerW,     748.0f,  772.0f);
      break;

    case HEATING:
      if (transitionTicks <= 4) {
        machineTemp = softMove(machineTemp, 47.0f);
        oilTemp     = softMove(oilTemp,     49.0f);
        vibration   = softMove(vibration,   0.32f);
        airflowLpm  = softMove(airflowLpm, 268.0f);
        powerW      = softMove(powerW,     800.0f);
      } else {
        machineTemp += frand(1, 4) * 0.25f;
        oilTemp     += frand(1, 3) * 0.18f;
        rpm         += frand(-15, 8);
        vibration   += frand(0, 2) * 0.015f;
        pressureBar += frand(-2, 1) * 0.07f;
        airflowLpm  -= frand(0, 3);
        powerW       = 790.0f + (machineTemp - 43.0f) * 3.0f + frand(-5, 5);
      }

      machineTemp = constrain(machineTemp,  43.0f,  72.0f);
      oilTemp     = constrain(oilTemp,      46.0f,  67.0f);
      rpm         = constrain(rpm,        1370.0f, 1465.0f);
      vibration   = constrain(vibration,    0.28f,   0.70f);
      pressureBar = constrain(pressureBar,  6.80f,   8.60f);
      airflowLpm  = constrain(airflowLpm, 245.0f,  275.0f);
      powerW      = constrain(powerW,     790.0f, 1020.0f);
      break;

    case DEGRADING:
      if (transitionTicks <= 4) {
        machineTemp = softMove(machineTemp, 70.0f);
        oilTemp     = softMove(oilTemp,     65.0f);
        vibration   = softMove(vibration,   0.52f);
        pressureBar = softMove(pressureBar,  7.2f);
        airflowLpm  = softMove(airflowLpm, 262.0f);
        powerW      = softMove(powerW,     990.0f);
      } else {
        machineTemp += frand(2, 6) * 0.30f;
        oilTemp     += frand(2, 4) * 0.25f;
        rpm         -= frand(4, 15);
        vibration   += frand(1, 5) * 0.04f;
        pressureBar -= frand(1, 3) * 0.09f;
        airflowLpm  -= frand(2, 7);
        powerW       = 980.0f + (machineTemp - 68.0f) * 4.5f + frand(-8, 8);
      }

      machineTemp = constrain(machineTemp,  68.0f,  90.0f);
      oilTemp     = constrain(oilTemp,      63.0f,  82.0f);
      rpm         = constrain(rpm,        1290.0f, 1430.0f);
      vibration   = constrain(vibration,    0.45f,   1.60f);
      pressureBar = constrain(pressureBar,  5.20f,   7.80f);
      airflowLpm  = constrain(airflowLpm, 215.0f,  268.0f);
      powerW      = constrain(powerW,     980.0f, 1230.0f);
      break;

    case CRITICAL:
      if (transitionTicks <= 4) {
        machineTemp = softMove(machineTemp, 88.0f);
        oilTemp     = softMove(oilTemp,     80.0f);
        vibration   = softMove(vibration,   1.45f);
        pressureBar = softMove(pressureBar,  5.5f);
        airflowLpm  = softMove(airflowLpm, 222.0f);
        powerW      = softMove(powerW,    1090.0f);
      } else {
        machineTemp += frand(3, 8) * 0.40f;
        oilTemp     += frand(3, 6) * 0.35f;
        rpm         -= frand(8, 25);
        vibration   += frand(4, 10) * 0.06f;
        pressureBar -= frand(2, 6) * 0.12f;
        airflowLpm  -= frand(6, 13);
        powerW       = 1080.0f + (machineTemp - 86.0f) * 6.0f + frand(-10, 10);
      }

      machineTemp = constrain(machineTemp,  86.0f, 108.0f);
      oilTemp     = constrain(oilTemp,      78.0f,  97.0f);
      rpm         = constrain(rpm,        1080.0f, 1310.0f);
      vibration   = constrain(vibration,    1.40f,   3.60f);
      pressureBar = constrain(pressureBar,  2.80f,   5.80f);
      airflowLpm  = constrain(airflowLpm, 155.0f,  225.0f);
      powerW      = constrain(powerW,    1080.0f, 1470.0f);
      break;

    case FAILURE:
      if (transitionTicks <= 5) {
        machineTemp = softMove(machineTemp, 100.0f, 0.20f);
        vibration   = softMove(vibration,    3.30f, 0.20f);
        pressureBar = softMove(pressureBar,  2.80f, 0.20f);
        oilTemp     = softMove(oilTemp,      95.0f, 0.20f);
        airflowLpm  = softMove(airflowLpm,  158.0f, 0.20f);
        powerW      = softMove(powerW,      400.0f, 0.15f);
        rpm        -= frand(10, 30);
      } else {
        machineTemp += frand(0, 2) * 0.15f;
        oilTemp     += frand(1, 4) * 0.20f;
        rpm         -= frand(8, 25);
        vibration   += frand(4, 10) * 0.06f;
        pressureBar -= frand(2, 6) * 0.10f;
        airflowLpm  -= frand(4, 12);
        powerW      += frand(-15, 10);
      }

      machineTemp = constrain(machineTemp,  98.0f, 115.0f);
      oilTemp     = constrain(oilTemp,      93.0f, 115.0f);
      rpm         = constrain(rpm,           0.0f, 1120.0f);
      vibration   = constrain(vibration,     3.20f,  8.00f);
      pressureBar = constrain(pressureBar,   0.00f,  3.20f);
      airflowLpm  = constrain(airflowLpm,    0.00f, 165.0f);
      powerW      = constrain(powerW,      300.0f,  580.0f);
      break;
  }
}

// ============================================================
//  Telemetri Gönder — WiFi HTTP POST + Serial debug
// ============================================================
void sendTelemetry() {
  JsonDocument doc;
  doc["node"]         = "compressor";
  doc["state"]        = stateToString(currentState);
  doc["temp_c"]       = round(machineTemp * 10.0f) / 10.0f;
  doc["rpm"]          = (int)rpm;
  doc["vibration_g"]  = round(vibration   * 100.0f) / 100.0f;
  doc["pressure_bar"] = round(pressureBar * 100.0f) / 100.0f;
  doc["oil_temp_c"]   = round(oilTemp     * 10.0f) / 10.0f;
  doc["airflow_lpm"]  = (int)airflowLpm;
  doc["power_w"]      = (int)powerW;
  doc["ts_ms"]        = millis();

  String payload;
  serializeJson(doc, payload);

  Serial.println(payload);   // ekle

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String url = "http://" + String(API_HOST) + ":" + String(API_PORT) + API_ENDPOINT;
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(payload);
    Serial.print("HTTP: "); Serial.println(code);   // ekle
    http.end();
  } else {
    connectWiFi();
  }
}

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(115200);   // ekle

  wdt_begin();

  pinMode(0, INPUT_PULLUP);
  randomSeed(analogRead(34) + analogRead(35) + millis());

  connectWiFi();
  Serial.print("WiFi OK: ");   // ekle
  Serial.println(WiFi.localIP());   // ekle
}

// ============================================================
//  LOOP
// ============================================================
void loop() {
  esp_task_wdt_reset();

  unsigned long now = millis();
  if (now - lastSendTime >= SEND_INTERVAL_MS) {
    lastSendTime = now;
    updateState();
    updateMetrics();
    sendTelemetry();
  }
}