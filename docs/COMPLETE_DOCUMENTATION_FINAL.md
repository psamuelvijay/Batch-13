# 🛡️ IoT IDS — Complete Documentation

## System Architecture

```
ESP32 Legit + ESP32 Ghost
    → MQTT (Mosquitto, local broker, port 1883)
    → FastAPI Backend (port 8000)
        → Rule-based detection (CLONE / TAMPER / ANOMALY)
        → ML Detection Engine (Isolation Forest, XGBoost, Random Forest)
        → Quarantine System (auto-block after 3 violations)
    → InfluxDB (time-series storage, port 8086)
    → React Dashboard (port 3000)
    → Merkle Tree (tamper-proof local logging)
    → Hyperledger Fabric (optional blockchain audit trail)
```

## Detection Layers

### Layer 1 — Rule-Based
| Rule | Condition | Verdict |
|------|-----------|---------|
| UID Check | device_uid ≠ D00061FE8CE0 | CLONE |
| Firmware Check | firmware_hash ≠ dfc2dcd4 | TAMPER |
| Temp Range | < 25°C or > 40°C | ANOMALY |
| Humidity Range | < 20% or > 70% | ANOMALY |
| Interval Range | < 4000ms or > 6000ms | ANOMALY |

### Layer 2 — ML Models
| Model | Type | Purpose |
|-------|------|---------|
| XGBoost | Binary classifier | Attack vs Normal (primary) |
| Random Forest | Multi-class | Attack type classification |
| Isolation Forest | Anomaly detector | Unsupervised outlier detection |

### Layer 3 — Quarantine
- Tracks violations per device UID
- Auto-quarantines after 3 violations (5-minute block)
- Admin can release manually via dashboard or API

## ML Features (11 total)

| Feature | Description |
|---------|-------------|
| humidity | Raw humidity reading |
| interval | Packet interval (ms) |
| temperature | Raw temperature reading |
| uid_flag | 0=legit UID, 1=fake UID |
| firmware_flag | 0=legit firmware, 1=modified |
| interval_deviation | abs(interval - 5000) |
| temp_out_of_range | 1 if temp < 25 or > 35 |
| humid_out_of_range | 1 if humidity < 30 or > 65 |
| interval_mean | Rolling 10-packet mean of interval |
| temp_mean | Rolling 10-packet mean of temperature |
| humid_mean | Rolling 10-packet mean of humidity |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Health check |
| GET | /stats | System statistics |
| GET | /verify-logs | Merkle chain verification |
| GET | /quarantine/{uid} | Quarantine status |
| POST | /quarantine/{uid}/release | Release from quarantine |

## Telemetry Payload Schema

```json
{
  "device_id": "ESP32_LEGIT",
  "device_uid": "D00061FE8CE0",
  "firmware_hash": "dfc2dcd4",
  "temperature": 30.6,
  "humidity": 40.0,
  "interval": 5036,
  "timestamp": 12345678,
  "source": "legit"
}
```

## Model Performance

| Metric | Value |
|--------|-------|
| Accuracy | 100% (test set) |
| Precision | 100% |
| Recall | 100% |
| F1-Score | 1.0 |
| ROC-AUC | 1.0 |
| False Positive Rate | 0% |

> Note: Perfect scores are expected due to the deterministic nature of the behavioral differences between legit and ghost devices in the controlled lab environment.

## Merkle Tree Logging

Each log entry contains:
- SHA-256 hash of entry data
- Reference to previous entry hash (chain link)
- Timestamp (Unix + ISO 8601)
- Detection verdict and device metadata

The Merkle root provides a single cryptographic commitment to all log entries, enabling efficient tamper detection.

## Hyperledger Fabric Integration

- Channel: `mychannel`
- Chaincode: `idsaudit`
- Async submission (background queue, non-blocking)
- Supports: `storeVerdict`, `queryRecord`, `queryRecordsByDevice`, `getAttackRecords`, `getRecordCount`
