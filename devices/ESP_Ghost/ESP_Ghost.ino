#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ============================================================
// GHOST DEVICE - REALISTIC BEHAVIORAL ATTACK SIMULATOR
//
// FIX: Clone attacks now use the LEGIT UID (real cloning).
//      Detection must come from behavioral signals only.
//      Removed trivially detectable FAKE_UID for clone cases.
// ============================================================

// ---------------- WIFI CONFIG ----------------
const char* ssid = "shashank";
const char* password = "shashank123";

// ---------------- MQTT CONFIG ----------------
const char* mqtt_server = "10.57.146.169";

WiFiClient espClient;
PubSubClient client(espClient);

// ---------------- DHT11 SENSOR CONFIG ----------------
#define DHTPIN 4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ---------------- DEVICE INFO ----------------
String device_id = "ESP32_GHOST";

// FIX: Clone attacks use the LEGIT UID — real cloning scenario.
// The IDS must detect this purely from behavioral patterns (interval, sensors).
String LEGIT_UID      = "D00061FE8CE0";
String LEGIT_FIRMWARE = "dfc2dcd4";
String BAD_FIRMWARE   = "BADFIRMWARE";

unsigned long lastPacket = 0;
unsigned long bootTime   = 0;

// ---------------- WIFI CONNECTION ----------------

void connectWiFi() {
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("ESP IP: ");
  Serial.println(WiFi.localIP());
}

// ---------------- MQTT CONNECTION ----------------

void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    if (client.connect("ESP32_GHOST_CLIENT")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.println(client.state());
      delay(2000);
    }
  }
}

// ---------------- SENSOR READING ----------------

float readRealTemperature() {
  float t = dht.readTemperature();
  if (isnan(t)) {
    return 28.0 + random(-20, 30) / 10.0;
  }
  return t;
}

float readRealHumidity() {
  float h = dht.readHumidity();
  if (isnan(h)) {
    return 50.0 + random(-100, 100) / 10.0;
  }
  return h;
}

// ---- Manipulated readings (subtle — stays near legit range to force ML work) ----

float subtlyHighTemp() {
  // +3 to +6°C above real reading — stays in ambiguous zone
  float real = readRealTemperature();
  return real + random(30, 60) / 10.0;
}

float subtlyLowHumidity() {
  // -5 to -12% below real reading — stays in ambiguous zone
  float real = readRealHumidity();
  return real - random(50, 120) / 10.0;
}

// ---------------- SETUP ----------------

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("======================================");
  Serial.println("GHOST ESP32 - BEHAVIORAL ATTACK SIM");
  Serial.println("======================================");
  Serial.println("NOTE: All clone attacks use LEGIT UID.");
  Serial.println("Detection relies on behavioral patterns only.");

  dht.begin();
  connectWiFi();
  client.setServer(mqtt_server, 1883);
  randomSeed(analogRead(0));
  bootTime = millis();
  Serial.println("Ghost device ready");
}

// ---------------- MAIN LOOP ----------------

void loop() {

  if (!client.connected())
    reconnectMQTT();

  client.loop();

  // Randomly select attack type each packet
  int attack_type = random(0, 5);

  String device_uid;
  String firmware_hash;
  float  temperature;
  float  humidity;
  int    delay_time = 5000;

  switch (attack_type) {

    case 0:
      // --------------------------------------------------------
      // CLONE ONLY — uses LEGIT UID + LEGIT FIRMWARE + real sensors
      // Interval slightly faster than legit (subtle behavioral tell)
      // Legit: 4950–5050ms. Ghost clone: 4700–4950ms (faster, overlaps edge)
      // --------------------------------------------------------
      device_uid    = LEGIT_UID;
      firmware_hash = LEGIT_FIRMWARE;
      temperature   = readRealTemperature();
      humidity      = readRealHumidity();
      delay_time    = random(4700, 4950);
      Serial.println("ATTACK: BEHAVIORAL CLONE (legit UID, faster interval)");
      break;

    case 1:
      // --------------------------------------------------------
      // TAMPER ONLY — uses LEGIT UID, bad firmware, real sensors
      // Interval slightly irregular but overlapping
      // --------------------------------------------------------
      device_uid    = LEGIT_UID;
      firmware_hash = BAD_FIRMWARE;
      temperature   = readRealTemperature();
      humidity      = readRealHumidity();
      delay_time    = 5000 + random(-120, 120);
      Serial.println("ATTACK: TAMPER (legit UID, bad firmware, irregular interval)");
      break;

    case 2:
      // --------------------------------------------------------
      // ANOMALY ONLY — legit identity, clearly manipulated sensors
      // Temperature pushed above 40°C so rule-based catches it too
      // giving the dataset labeled ANOMALY examples
      // --------------------------------------------------------
      device_uid    = LEGIT_UID;
      firmware_hash = LEGIT_FIRMWARE;
      temperature   = readRealTemperature() + random(80, 130) / 10.0; // +8 to +13°C → clearly > 40
      humidity      = readRealHumidity()    - random(150, 250) / 10.0; // -15 to -25% → may go < 20
      delay_time    = random(4600, 5400);
      Serial.println("ATTACK: SENSOR ANOMALY (clear out-of-range manipulation)");
      break;

    case 3:
      // --------------------------------------------------------
      // CLONE + ANOMALY — legit UID, clearly anomalous sensors + faster interval
      // --------------------------------------------------------
      device_uid    = LEGIT_UID;
      firmware_hash = LEGIT_FIRMWARE;
      temperature   = readRealTemperature() + random(80, 130) / 10.0;
      humidity      = readRealHumidity()    - random(150, 250) / 10.0;
      delay_time    = random(4400, 4900);
      Serial.println("ATTACK: CLONE + SENSOR ANOMALY (clear manipulation)");
      break;

    case 4:
      // --------------------------------------------------------
      // FULL ATTACK — bad firmware + clear sensor anomaly + fast interval
      // All three detection signals active simultaneously
      // --------------------------------------------------------
      device_uid    = LEGIT_UID;
      firmware_hash = BAD_FIRMWARE;
      temperature   = readRealTemperature() + random(100, 150) / 10.0; // +10 to +15°C
      humidity      = readRealHumidity()    - random(200, 300) / 10.0; // -20 to -30%
      delay_time    = random(3800, 4600);
      Serial.println("ATTACK: FULL (bad firmware + clear anomaly + fast interval)");
      break;
  }

  // Calculate actual measured interval
  unsigned long now      = millis();
  unsigned long interval = now - lastPacket;

  if (lastPacket == 0) {
    lastPacket = now;
    delay(delay_time);
    return;
  }

  // Apply the delay BEFORE recording lastPacket so the measured
  // interval on the NEXT packet correctly reflects this attack's timing
  delay(delay_time);

  lastPacket = millis();  // record after delay so next interval is accurate

  // Build JSON payload
  StaticJsonDocument<256> doc;
  doc["device_id"]     = device_id;
  doc["device_uid"]    = device_uid;
  doc["firmware_hash"] = firmware_hash;
  doc["temperature"]   = round(temperature * 10) / 10.0;
  doc["humidity"]      = round(humidity    * 10) / 10.0;
  doc["interval"]      = (unsigned long)delay_time;  // report intended interval — no lag
  doc["timestamp"]     = millis();
  doc["source"]        = "ghost";

  char buffer[256];
  serializeJson(doc, buffer);

  Serial.println("Sending:");
  Serial.println(buffer);

  client.publish("iot/telemetry", buffer);
}
