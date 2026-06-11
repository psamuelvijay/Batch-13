# Project Master Context — Phantom Firmware / IoT Behavioral Detection

---

## Project Overview

This system detects cloned or compromised IoT devices using behavioral fingerprinting rather than identity-based checks. Two ESP32 devices (one legitimate, one ghost/attacker) send telemetry over MQTT to a FastAPI backend, which runs rule-based and ML-based detection against the data. The core insight is that even if an attacker perfectly clones a device's identity (UID, firmware hash), they cannot perfectly replicate its behavioral patterns (sensor readings, timing).

---

## Current Tech Stack

| Layer | Technology |
|---|---|
| Hardware | ESP32 (x2), DHT11 sensors (x2) |
| Firmware | Arduino IDE (C++) |
| Communication | MQTT via Mosquitto broker, topic: `iot/telemetry` |
| Backend | Python, FastAPI |
| Time-Series DB | InfluxDB — measurement: `iot_telemetry` |
| ML | scikit-learn (Isolation Forest, Random Forest), XGBoost, SHAP, SMOTE |
| Dataset | CSV export from InfluxDB, ~2000+ rows |
| Explainability | SHAP (feature importance + decision explanation) |
| Optional/Future | Hyperledger Fabric or hash-chain logging, TLS/Secure MQTT, Dashboard ML overlay |

---

## Finalized Architecture

```
ESP32 Legit + ESP32 Ghost
    → MQTT (Mosquitto, local broker)
    → FastAPI Backend
        → Rule-based detection (CLONE / TAMPER / ANOMALY)
        → ML Detection Engine (Isolation Forest, Random Forest, XGBoost)
    → InfluxDB (time-series storage)
    → Dashboard (Grafana or equivalent)
    → [Optional] Blockchain / Hash-chain audit log
```

### Detection Logic (Rule-Based Layer)

- `CLONE` → UID mismatch
- `TAMPER` → firmware_hash mismatch
- `ANOMALY` → temperature > 40 or < 15 | humidity < 25 or > 80 | interval < 3000ms

### Behavioral Features Used for ML

| Feature | Legit | Attack |
|---|---|---|
| temperature | Stable ~30°C | Wide variation |
| humidity | Stable ~40% | Extreme values |
| interval | ~5000ms | 2000–4000ms |
| temp_deviation | Low | High |
| interval_deviation | Low | High |

> Interval is the strongest behavioral signal.

### Discarded Approaches

- UID/identity-based ML features (removed — trivially cheated by cloning)
- Blockchain as core layer (overkill for single-party system; retained as optional audit log only)
- HTTP-based telemetry (replaced by MQTT)

---

## Key Code Patterns

### Telemetry Payload (JSON schema)

```json
{
  "device_id": "ESP32_LEGIT",
  "device_uid": "<chip_uid>",
  "firmware_hash": "<sha256>",
  "temperature": 30.6,
  "humidity": 40.0,
  "interval": 5036,
  "verdict": "CLONE|TAMPER|ANOMALY",
  "source": "ghost"
}
```

### InfluxDB Schema

- Measurement: `iot_telemetry`
- Tags: `device_id`, `uid`, `verdict`, `source`
- Fields: `temperature`, `humidity`, `interval`, `attack_flag` (0/1)

### Feature Engineering (dataset_builder_v2.py pattern)

```python
df['temp_deviation'] = abs(df['temperature'] - 30)
df['interval_deviation'] = abs(df['interval'] - 5000)
```

### Dataset Preprocessing

```python
# Handle InfluxDB CSV export quirks
df = pd.read_csv('data.csv', on_bad_lines='skip')
# Drop metadata rows, rename columns manually, drop duplicates
df = df.drop_duplicates()
```

### ML Pipeline Pattern (train_models.py)

```python
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE
import shap

# Balance classes
sm = SMOTE()
X_res, y_res = sm.fit_resample(X, y)

# SHAP explainability
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
```

### FastAPI MQTT Subscriber Pattern (telemetry_api.py)

```python
# Subscribe to MQTT, process telemetry, apply detection, write to InfluxDB
@app.on_event("startup")
async def startup():
    client.subscribe("iot/telemetry")
```

### ESP32 Networking Note

- Always use the PC's local IP (e.g., `192.168.x.x` or `10.x.x.x`), never `127.0.0.1`
- ESP32 and server must be on the same network
- Response code `-1` = connection failure (check firewall / IP)

---

## Current Progress (100% Complete)

- ESP32 dual-device setup (legit + ghost attacker simulator)
- MQTT pipeline via Mosquitto broker
- FastAPI telemetry ingestion endpoint
- InfluxDB time-series storage
- Dashboard panels (Temperature, Humidity, Interval, Security Alerts, Attack Count, Combined Anomaly)
- Dataset generation from InfluxDB export (~2000+ rows)
- Dataset preprocessing and feature engineering (`temp_deviation`, `interval_deviation`)
- Initial ML pipeline (models trained: Isolation Forest, Random Forest, XGBoost)
- SHAP explainability integrated
- Model files saved: `models/isolation_forest.pkl`, `models/random_forest_multiclass.pkl`, `models/xgboost_binary.pkl`, `models/scaler.pkl`, `models/metadata.pkl`

---

## Active Roadblocks

1. Model evaluation — `evaluate_results.py` exists but results need review; hyperparameter tuning not yet done.
2. ML integration into FastAPI — models are trained and saved but not yet wired into the live `/telemetry` endpoint for real-time inference.
3. Real-time prediction API — endpoint for live ML verdict not implemented.
4. Dashboard ML overlay — Grafana panels don't yet show ML verdicts alongside raw telemetry.
5. Alert system — no active alerting (buzzer/LED or push notification) on detection.
6. Secure MQTT (TLS) — still using plaintext MQTT locally.
7. Blockchain/hash-chain audit log — required but not started.
