#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ============================================================
// LEGITIMATE DEVICE (WITH REALISTIC JITTER)
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

// ---------------- DEVICE INFO (LEGITIMATE) ----------------
String device_id = "ESP32_LEGIT";
String device_uid = "D00061FE8CE0";  // Legit UID
String firmware_hash = "dfc2dcd4";   // Legit firmware hash

unsigned long lastPacket = 0;

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
    if (client.connect("ESP32_LEGIT_CLIENT")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.println(client.state());
      delay(2000);
    }
  }
}

// ---------------- SETUP ----------------

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("======================================");
  Serial.println("LEGITIMATE ESP32 DEVICE");
  Serial.println("======================================");

  // Initialize DHT11
  dht.begin();
  Serial.println("DHT11 sensor initialized");

  connectWiFi();
  
  client.setServer(mqtt_server, 1883);
  
  randomSeed(analogRead(0));

  Serial.println("Legitimate device ready");
  Serial.print("UID: ");
  Serial.println(device_uid);
  Serial.print("Firmware: ");
  Serial.println(firmware_hash);
}

// ---------------- MAIN LOOP ----------------

void loop() {

  if (!client.connected())
    reconnectMQTT();

  client.loop();

  // Read real sensor values
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  // Fallback if sensor fails
  if (isnan(temperature)) {
    temperature = 30.0;
    Serial.println("DHT read failed, using default temp");
  }
  
  if (isnan(humidity)) {
    humidity = 50.0;
    Serial.println("DHT read failed, using default humidity");
  }

  // Calculate interval
  unsigned long now = millis();
  unsigned long interval = now - lastPacket;

  if (lastPacket == 0) {
    // Skip first packet (no valid interval)
    lastPacket = now;
    delay(5000);
    return;
  }

  lastPacket = now;

  // Build JSON payload
  StaticJsonDocument<256> doc;

  doc["device_id"] = device_id;
  doc["device_uid"] = device_uid;
  doc["firmware_hash"] = firmware_hash;
  doc["temperature"] = round(temperature * 10) / 10.0;
  doc["humidity"] = round(humidity * 10) / 10.0;
  doc["interval"] = interval;
  doc["timestamp"] = now;
  doc["source"] = "legit";

  char buffer[256];
  serializeJson(doc, buffer);

  Serial.println("Sending:");
  Serial.println(buffer);

  client.publish("iot/telemetry", buffer);

  // REALISTIC JITTER: 5000ms ± 50ms = 4950-5050ms
  // This simulates real-world network delays, WiFi latency, OS scheduling
  int jitter = random(-50, 50);
  delay(5000 + jitter);
}
