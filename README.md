# 🛡️ IoT Intrusion Detection System

A behavioral fingerprinting-based intrusion detection system for IoT devices. Instead of relying on identity checks (easily defeated by cloning), this system detects compromised or counterfeit devices by analyzing their behavioral patterns — sensor readings, timing intervals, and statistical deviations — using a three-layer detection pipeline: rule-based heuristics, ensemble ML models, and a cryptographic Merkle audit log backed by an optional Hyperledger Fabric blockchain.

---

## Key Features

- **Behavioral Fingerprinting** — Detects cloned/ghost devices even when UIDs and firmware hashes are spoofed, using interval timing and sensor deviation patterns
- **Three-Layer Detection** — Rule-based (CLONE/TAMPER/ANOMALY), ML inference (XGBoost + Random Forest + Isolation Forest), and quarantine auto-blocking
- **Cryptographic Audit Log** — SHA-256 Merkle tree chains every detection event; tampering is instantly detectable
- **Active Quarantine** — Devices with 3+ violations are automatically blocked for 5 minutes; admin release via dashboard
- **Real-Time Dashboard** — React UI polling the FastAPI backend every 2 seconds with live charts, device tables, and chain verification

---

## Results

| Metric | Value |
|--------|-------|
| Accuracy | **100%** (test set) |
| Precision | 100% |
| Recall | 100% |
| F1-Score | 1.0 |
| ROC-AUC | 1.0 |
| Inference Latency | **< 200ms** |
| False Positive Rate | 0% |

---

## Technologies

| Layer | Technology |
|-------|------------|
| Hardware | ESP32 × 2, DHT11 sensors |
| Firmware | Arduino IDE (C++) |
| Communication | MQTT via Mosquitto (port 1883) |
| Backend | Python 3.9+, FastAPI, Uvicorn |
| Time-Series DB | InfluxDB 2.x |
| ML | XGBoost, scikit-learn, SMOTE, SHAP |
| Dashboard | React 19, Recharts, Axios |
| Cryptographic Log | Merkle Tree (SHA-256) |
| Blockchain | Hyperledger Fabric (optional) |

---

## Quick Start

Run these 4 terminals simultaneously after setup:

```bash
# Terminal 1 — MQTT broker
mosquitto -v

# Terminal 2 — FastAPI backend
cd backend
python telemetry_api_v3.py

# Terminal 3 — React dashboard
cd dashboard
npm install && npm start

# Terminal 4 — InfluxDB
influxd
```

Open the dashboard at **http://localhost:3000**

---

## Project Structure

```
Mini Project/
├── README.md
├── .gitignore
│
├── backend/                    # Python backend
│   ├── telemetry_api_v3.py     # FastAPI + MQTT subscriber + detection pipeline
│   ├── dataset_builder_v2.py   # Feature engineering from InfluxDB CSV export
│   ├── train_models_v3_FIXED.py# ML training (XGBoost, RF, Isolation Forest)
│   ├── evaluate_results.py     # SHAP explainability + metrics
│   ├── merkle_logger.py        # SHA-256 Merkle tree logging
│   ├── hlf_client.py           # Hyperledger Fabric async client
│   ├── ids-chaincode.js        # HLF chaincode (audit log contract)
│   └── requirements.txt
│
├── hardware/                   # ESP32 Arduino sketches
│   ├── ESP_Legit_PERFECT.ino   # Legitimate device firmware
│   └── ESP_Ghost_PERFECT.ino   # Attacker/ghost device simulator
│
├── dashboard/                  # React frontend
│   ├── src/
│   │   ├── Dashboard.js        # Main dashboard component
│   │   ├── Dashboard.css
│   │   ├── App.js
│   │   └── index.js
│   ├── public/
│   └── package.json
│
├── models/                     # Trained ML model files (.pkl)
│   ├── xgboost_binary_v3.pkl
│   ├── random_forest_multiclass_v3.pkl
│   ├── isolation_forest_v3.pkl
│   ├── scaler_v3.pkl
│   └── metadata_v3.pkl
│
└── docs/                       # Documentation and visualizations
    ├── COMPLETE_DOCUMENTATION_FINAL.md
    ├── EXECUTION_GUIDE_30MIN.md
    ├── REACT_DASHBOARD_SETUP.md
    └── visualizations/
        ├── confusion_matrix_v3.png
        ├── feature_importance_v3.png
        ├── roc_curve_v3.png
        ├── shap_summary.png
        ├── shap_importance_bar.png
        └── precision_recall_curve.png
```

---

## Setup Guide

See [`docs/EXECUTION_GUIDE_30MIN.md`](docs/EXECUTION_GUIDE_30MIN.md) for full step-by-step setup.

See [`docs/REACT_DASHBOARD_SETUP.md`](docs/REACT_DASHBOARD_SETUP.md) for dashboard-specific configuration.

See [`docs/COMPLETE_DOCUMENTATION_FINAL.md`](docs/COMPLETE_DOCUMENTATION_FINAL.md) for architecture, API reference, and ML details.

---

## Authors

**Batch 13**  
IoT Intrusion Detection System — Mini Project
