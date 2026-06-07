#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ============================================================
// GHOST DEVICE - REALISTIC ATTACKS (READS REAL DHT11!)
// ============================================================

// ---------------- WIFI CONFIG ----------------
const char* ssid = "shashank";
const char* password = "shashank123";

// ---------------- MQTT CONFIG ----------------
const char* mqtt_server = "10.57.146.169";

WiFiClient espClient;
PubSubClient client(espClient);

// ---------------- DHT11 SENSOR CONFIG ----------------
#define DHTPIN 4          // GPIO4 - Connect DHT11 data pin here
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ---------------- DEVICE INFO ----------------
String device_id = "ESP32_GHOST";
String LEGIT_UID = "D00061FE8CE0";
String FAKE_UID = "FAKE1234ABCD";  // Different from legit

String LEGIT_FIRMWARE = "dfc2dcd4";
String BAD_FIRMWARE = "BADFIRMWARE";

unsigned long lastPacket = 0;
unsigned long bootTime = 0;

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

// ---------------- SENSOR READING (REAL DHT11!) ----------------

float readRealTemperature() {
  float t = dht.readTemperature();
  if (isnan(t)) {
    Serial.println("DHT11 read failed, using fallback");
    return 30.0 + random(-20, 30) / 10.0;  // Fallback: 28-33°C
  }
  return t;
}

float readRealHumidity() {
  float h = dht.readHumidity();
  if (isnan(h)) {
    Serial.println("DHT11 read failed, using fallback");
    return 50.0 + random(-100, 100) / 10.0;  // Fallback: 40-60%
  }
  return h;
}

// ---------------- ATTACK SENSOR FUNCTIONS ----------------

float normalTemperature() {
  // Use REAL sensor reading
  return readRealTemperature();
}

float normalHumidity() {
  // Use REAL sensor reading
  return readRealHumidity();
}

float abnormalTemperature() {
  // Read real sensor, then manipulate slightly
  float real = readRealTemperature();
  
  // Add realistic manipulation: +5 to +10°C
  return real + random(50, 100) / 10.0;
}

float abnormalHumidity() {
  // Read real sensor, then manipulate slightly
  float real = readRealHumidity();
  
  // Subtract 10-20% to simulate dry attack
  return real - random(100, 200) / 10.0;
}

// ---------------- SETUP ----------------

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("======================================");
  Serial.println("GHOST ESP32 - ADVANCED ATTACK SIMULATOR");
  Serial.println("======================================");

  // Initialize DHT sensor
  dht.begin();
  Serial.println("DHT11 sensor initialized");

  connectWiFi();
  
  client.setServer(mqtt_server, 1883);

  randomSeed(analogRead(0));
  bootTime = millis();
  
  Serial.println("Ghost device ready");
  Serial.println("Attack types: CLONE, TAMPER, ANOMALY, CLONE+ANOMALY, FULL");
}

// ---------------- MAIN LOOP ----------------

void loop() {

  if (!client.connected())
    reconnectMQTT();

  client.loop();

  // Randomly select attack type
  int attack_type = random(0, 5);

  String device_uid;
  String firmware_hash;
  float temperature;
  float humidity;
  int delay_time = 5000;

  switch(attack_type) {

    case 0: // CLONE ONLY - VERY STEALTHY
      device_uid = FAKE_UID;
      firmware_hash = LEGIT_FIRMWARE;
      temperature = normalTemperature();   // Real sensor
      humidity = normalHumidity();         // Real sensor
      delay_time = 5000 + random(-80, 80); // 4920-5080ms (overlaps with legit!)
      Serial.println("ATTACK: CLONE ONLY (STEALTHY)");
      break;

    case 1: // TAMPER ONLY - VERY STEALTHY
      device_uid = LEGIT_UID;
      firmware_hash = BAD_FIRMWARE;
      temperature = normalTemperature();   // Real sensor
      humidity = normalHumidity();         // Real sensor
      delay_time = 5000 + random(-80, 80); // 4920-5080ms
      Serial.println("ATTACK: TAMPER ONLY (STEALTHY)");
      break;

    case 2: // ANOMALY ONLY - BEHAVIORAL
      device_uid = LEGIT_UID;
      firmware_hash = LEGIT_FIRMWARE;
      temperature = abnormalTemperature(); // Manipulated real reading
      humidity = abnormalHumidity();       // Manipulated real reading
      delay_time = random(4700, 5300);     // 4700-5300ms (moderate overlap)
      Serial.println("ATTACK: ANOMALY ONLY");
      break;

    case 3: // CLONE + ANOMALY - MODERATE SOPHISTICATION
      device_uid = FAKE_UID;
      firmware_hash = LEGIT_FIRMWARE;
      temperature = abnormalTemperature(); // Manipulated
      humidity = abnormalHumidity();       // Manipulated
      delay_time = random(4500, 5200);     // 4500-5200ms
      Serial.println("ATTACK: CLONE + ANOMALY");
      break;

    case 4: // FULL ATTACK - OBVIOUS/AGGRESSIVE
      device_uid = FAKE_UID;
      firmware_hash = BAD_FIRMWARE;
      temperature = abnormalTemperature(); // Manipulated
      humidity = abnormalHumidity();       // Manipulated
      delay_time = random(3500, 4500);     // 3500-4500ms (clearly different!)
      Serial.println("ATTACK: FULL ATTACK (AGGRESSIVE)");
      break;
  }

  // Calculate interval
  unsigned long now = millis();
  unsigned long interval = now - lastPacket;

  if (lastPacket == 0) {
    // Skip first packet (no valid interval)
    lastPacket = now;
    delay(delay_time);
    return;
  }

  lastPacket = now;

  // Build JSON payload
  StaticJsonDocument<256> doc;

  doc["device_id"] = device_id;
  doc["device_uid"] = device_uid;
  doc["firmware_hash"] = firmware_hash;
  doc["temperature"] = round(temperature * 10) / 10.0;  // 1 decimal place
  doc["humidity"] = round(humidity * 10) / 10.0;        // 1 decimal place
  doc["interval"] = interval;
  doc["timestamp"] = now;
  doc["source"] = "ghost";

  char buffer[256];
  serializeJson(doc, buffer);

  Serial.println("Sending:");
  Serial.println(buffer);

  client.publish("iot/telemetry", buffer);

  delay(delay_time);
}
