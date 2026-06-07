# ⚡ 30-Minute Execution Guide

Get the full IoT IDS stack running in 30 minutes.

## Prerequisites

- Python 3.9+
- Node.js 18+
- Arduino IDE 2.x
- Mosquitto MQTT broker
- InfluxDB 2.x
- Two ESP32 boards with DHT11 sensors

## Step 1 — Install Python Dependencies (3 min)

```bash
cd backend
pip install -r requirements.txt
```

## Step 2 — Start Infrastructure (5 min)

**Terminal A — Mosquitto MQTT broker:**
```bash
mosquitto -v
```

**Terminal B — InfluxDB:**
```bash
# Windows: Start InfluxDB service or run influxd.exe
influxd
```

Configure InfluxDB at http://localhost:8086:
- Org: `iot-lab`
- Bucket: `telemetry_v2`
- Copy the generated API token into `backend/telemetry_api_v3.py` → `INFLUX_TOKEN`

## Step 3 — Flash ESP32 Devices (10 min)

1. Open Arduino IDE
2. Install libraries: `PubSubClient`, `ArduinoJson`, `DHT sensor library`
3. Flash `hardware/ESP_Legit_PERFECT.ino` to first ESP32
4. Flash `hardware/ESP_Ghost_PERFECT.ino` to second ESP32
5. Update `ssid`, `password`, and `mqtt_server` (your PC's local IP) in both sketches

## Step 4 — Start Backend (2 min)

**Terminal C:**
```bash
cd backend
python telemetry_api_v3.py
```

Expected output:
```
✅ InfluxDB connected
✅ ML models loaded (11 features)
✅ MQTT subscribed to: iot/telemetry
✅ SYSTEM READY
```

## Step 5 — Start Dashboard (5 min)

**Terminal D:**
```bash
cd dashboard
npm install
npm start
```

Open http://localhost:3000

## Step 6 — Generate Training Data (5 min)

If you need to retrain models:
```bash
cd backend
# Export data from InfluxDB as data.csv first, then:
python dataset_builder_v2.py
python train_models_v3_FIXED.py
python evaluate_results.py
```

## Verification

- Dashboard shows devices tracked and violation counts
- MQTT logs show packets from both ESP32s
- InfluxDB shows telemetry data in `telemetry_v2` bucket
- Click "Verify Chain" in dashboard to confirm Merkle integrity

## Common Issues

| Issue | Fix |
|-------|-----|
| ESP32 can't connect to MQTT | Use PC local IP (not 127.0.0.1), check firewall |
| ML models not found | Run `train_models_v3_FIXED.py` first |
| InfluxDB connection failed | Check token in `telemetry_api_v3.py` |
| Dashboard shows error | Ensure FastAPI is running on port 8000 |
