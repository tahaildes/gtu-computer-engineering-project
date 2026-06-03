// ============================================================
//  DARK FACTORY — ESP32 #2  AKTÜATÖR KONTROLCÜ
//  Donanım : DC Fan + Buzzer + LED + Nemlendirici (Transistör Pulse)
//  Giriş   : WiFi → GET /cmd/ZONE_A (komut poll)
//  Çıktı   : WiFi → POST /cmd/ZONE_A/ack (komut onay)
// ============================================================
//
//  GEREKLİ KÜTÜPHANELER (Arduino IDE → Library Manager):
//    1. ArduinoJson  (by Benoit Blanchon)
//    (WiFi ve HTTPClient ESP32 core ile birlikte gelir)
//
// ============================================================
//  PIN BAĞLANTILARI VE DEVRE ŞEMASI
// ============================================================
//
//  ── DC Fan (5V, 0.11A) ────────────────────────────────────
//   ESP32 GPIO13 ──── 1kΩ direnç ──── 2N2222 BASE  (orta bacak)
//                                     2N2222 EMITTER (sol bacak) ── GND
//                                     2N2222 COLLECTOR(sağ bacak) ── Fan (-)
//   ESP32 5V ─────────────────────────────────────── Fan (+)
//
//  ── Pasif Buzzer ──────────────────────────────────────────
//   Buzzer (+) →  ESP32 GPIO 16
//   Buzzer (-) →  ESP32 GND
//
//  ── LED ───────────────────────────────────────────────────
//   GPIO 2  ──── 220Ω direnç ──── LED Anot (+)
//   GND     ─────────────────── LED Katot (-)
//
//  ── Nemlendirici (2N2222 Transistör — Pulse ile Toggle) ──
//   ESP32 GPIO14 ──── 1kΩ direnç ──── 2N2222 BASE  (orta bacak)
//                                     2N2222 EMITTER (sol bacak) ── Buton bacak 1
//                                     2N2222 COLLECTOR(sağ bacak) ── Buton bacak 2
//
// ============================================================
//  AYARLAR — BURAYA KENDİ BİLGİLERİNİZİ GİRİN
// ============================================================

#define WIFI_SSID      "ZeynepS25"
#define WIFI_PASSWORD  "zeynep123"

#define API_HOST       "10.161.35.114"
#define API_PORT       8000
#define ZONE_ID        "ZONE_A"

// ============================================================
//  Komut poll aralığı
// ============================================================
#define POLL_INTERVAL_MS   1000

// ============================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <esp_task_wdt.h>

// ── Pin Tanımları ──────────────────────────────────────────
#define PIN_FAN     13
#define PIN_BUZZER  16
#define PIN_LED      2
#define PIN_MIST    14

// ── Fan PWM ────────────────────────────────────────────────
#define FAN_PWM_FREQ   25000
#define FAN_PWM_RES        8

// ── Nemlendirici Pulse ─────────────────────────────────────
#define MIST_PULSE_MS  100

// ── Zamanlama ──────────────────────────────────────────────
#define WDT_TIMEOUT_SEC   30
#define WIFI_TIMEOUT_MS   10000

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

// ── Mevcut Durum ───────────────────────────────────────────
int  fanSpeed   = 0;
bool buzzerOn   = false;
int  buzzerFreq = 1000;
bool ledOn      = false;
bool mistOn     = false;

unsigned long lastPollTime = 0;

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
  Serial.print("WiFi OK: ");
  Serial.println(WiFi.localIP());
}

// ============================================================
//  Fan
// ============================================================
void setFan(int percent) {
  percent  = constrain(percent, 0, 100);
  fanSpeed = percent;
  ledcWrite(PIN_FAN, map(percent, 0, 100, 0, 255));
}

// ============================================================
//  Buzzer
// ============================================================
void setBuzzer(bool on, int freq = -1) {
  buzzerOn = on;
  if (freq > 0) buzzerFreq = freq;
  if (on) {
    ledcAttach(PIN_BUZZER, buzzerFreq, 8);
    ledcWrite(PIN_BUZZER, 128);
  } else {
    ledcWrite(PIN_BUZZER, 0);
    ledcDetach(PIN_BUZZER);
    pinMode(PIN_BUZZER, OUTPUT);
    digitalWrite(PIN_BUZZER, LOW);
  }
}

// ============================================================
//  LED
// ============================================================
void setLED(bool on) {
  ledOn = on;
  digitalWrite(PIN_LED, on ? HIGH : LOW);
}

// ============================================================
//  Nemlendirici
// ============================================================
void mistPulse() {
  digitalWrite(PIN_MIST, HIGH);
  delay(MIST_PULSE_MS);
  digitalWrite(PIN_MIST, LOW);
}

void setMist(bool on) {
  if (mistOn == on) return;
  mistOn = on;
  if (on) {
    mistPulse();
  } else {
    mistPulse();
    delay(300);
    mistPulse();
  }
}

// ============================================================
//  Reset
// ============================================================
void resetAll() {
  setFan(0);
  setBuzzer(false);
  setLED(false);
  if (mistOn) setMist(false);
}

// ============================================================
//  Komutu API'den Oku ve Çalıştır
// ============================================================
void pollAndExecute() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    return;
  }

  HTTPClient http;
  String url = "http://" + String(API_HOST) + ":" + String(API_PORT) + "/cmd/" + ZONE_ID;
  http.begin(url);
  int code = http.GET();

  if (code == 200) {
    String body = http.getString();
    Serial.print("CMD: "); Serial.println(body);
    http.end();

    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, body);
    if (err) return;

    String cmdId      = doc["cmd_id"]      | "";
    String deviceType = doc["device_type"] | "";
    float  valuePct   = doc["value_pct"]   | 0.0f;
    bool   relayState = doc["relay_state"] | false;

    // Komutu çalıştır
    if (deviceType == "DEV_FAN") {
      setFan((int)valuePct);
      Serial.print("FAN: "); Serial.println((int)valuePct);

    } else if (deviceType == "DEV_BUZZER") {
      setBuzzer(relayState);
      Serial.print("BUZZER: "); Serial.println(relayState);

    } else if (deviceType == "DEV_VENT") {
      setFan((int)valuePct);
      Serial.print("VENT: "); Serial.println((int)valuePct);

    } else if (deviceType == "DEV_MIST_MAKER") {
      setMist(relayState);
      Serial.print("MIST: "); Serial.println(relayState);

    } else if (deviceType == "DEV_LED") {    // ← buraya ekle
      setLED(relayState);
      Serial.print("LED: "); Serial.println(relayState);
    }
    else if (deviceType == "DEV_COOLER") {
      setFan((int)valuePct);
      Serial.print("COOLER: "); Serial.println((int)valuePct);
    }

    // Komutu onayla
    if (cmdId.length() > 0) {
      JsonDocument ackDoc;
      ackDoc["cmd_id"] = cmdId;
      ackDoc["status"] = "OK";
      String ackPayload;
      serializeJson(ackDoc, ackPayload);

      HTTPClient ackHttp;
      String ackUrl = "http://" + String(API_HOST) + ":" + String(API_PORT) + "/cmd/" + ZONE_ID + "/ack";
      ackHttp.begin(ackUrl);
      ackHttp.addHeader("Content-Type", "application/json");
      ackHttp.POST(ackPayload);
      ackHttp.end();
      Serial.print("ACK: "); Serial.println(cmdId);
    }

  } else {
    http.end();
  }
}

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(115200);

  wdt_begin();

  ledcAttach(PIN_FAN, FAN_PWM_FREQ, FAN_PWM_RES);
  setFan(0);

  pinMode(PIN_LED,  OUTPUT);
  pinMode(PIN_MIST, OUTPUT);
  setLED(false);
  digitalWrite(PIN_MIST, LOW);
  setBuzzer(false);

  for (int i = 0; i < 2; i++) {
    setLED(true);  delay(200);
    setLED(false); delay(200);
  }

  connectWiFi();
}

// ============================================================
//  LOOP
// ============================================================
void loop() {
  esp_task_wdt_reset();

  unsigned long now = millis();
  if (now - lastPollTime >= POLL_INTERVAL_MS) {
    lastPollTime = now;
    pollAndExecute();
  }
}