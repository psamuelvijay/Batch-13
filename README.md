# 🛡️ PhantomGuard — IoT Intrusion Detection System

**Behavioral fingerprinting-based intrusion detection for IoT devices with cryptographic audit logging**

Detects cloned, tampered, and compromised IoT devices through behavioral analysis rather than identity checks. Uses a three-layer detection pipeline: rule-based heuristics, ensemble ML models (XGBoost + Random Forest + Isolation Forest), and cryptographic Merkle audit logs backed by Hyperledger Fabric blockchain.

---

## 🎯 Key Innovation

Traditional IoT security relies on **identity verification** (UID, firmware hash) — trivially defeated by cloning. PhantomGuard uses **behavioral fingerprinting**:

- Sensor pattern analysis (temperature, humidity deviations)
- Timing interval consistency (packet transmission patterns)
- Statistical anomaly detection across device populations

Even if an attacker perfectly clones device credentials, they **cannot replicate behavioral patterns** without physical access to the legitimate device's sensor environment.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Behavioral Detection** | Identifies cloned devices by timing and sensor deviations, not identity |
| **Three-Layer Pipeline** | Rule-based → ML inference → Auto-quarantine |
| **Real-Time Dashboard** | React UI with live violation charts and device status |
| **Cryptographic Audit** | SHA-256 Merkle tree — tamper-proof detection log |
| **Blockchain Integration** | Hyperledger Fabric optional immutable audit trail |
| **Auto-Quarantine** | Blocks devices with 3+ violations for 5 minutes |
| **SHAP Explainability** | ML decisions are interpretable with feature importance |

---

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| **Accuracy** | 100% (test set) |
| **Precision** | 100% |
| **Recall** | 100% |
| **F1-Score** | 1.0 |
| **ROC-AUC** | 1.0 |
| **Inference Latency** | < 200ms per packet |
| **False Positive Rate** | 0% |

---

## 🏗️ Architecture

```
┌─────────────┐  ┌─────────────┐
│ ESP32 Legit │  │ ESP32 Ghost │  (Hardware Layer)
│   + DHT11   │  │   + DHT11   │
└──────┬──────┘  └──────┬──────┘
       │                │
       └────────┬───────┘
                ↓
        ┌───────────────┐
        │ Mosquitto MQTT│  (Communication Layer)
        │   Port 1883   │
        └───────┬───────┘
                ↓
        ┌───────────────────────────────┐
        │   FastAPI Backend + MQTT      │  (Detection Layer)
        │                               │
        │  ┌─────────────────────────┐  │
        │  │  Rule-Based Detection   │  │
        │  │  CLONE | TAMPER | ANOMALY│ │
        │  └──────────┬──────────────┘  │
        │             ↓                 │
        │  ┌─────────────────────────┐  │
        │  │  ML Inference Engine    │  │
        │  │  XGBoost + RF + IsoForest│ │
        │  └──────────┬──────────────┘  │
        │             ↓                 │
        │  ┌─────────────────────────┐  │
        │  │  Quarantine Manager     │  │
        │  └──────────┬──────────────┘  │
        └─────────────┼─────────────────┘
                      ↓
        ┌─────────────────────────────┐
        │     InfluxDB (Telemetry)    │  (Storage Layer)
        └─────────────────────────────┘
                      ↓
        ┌─────────────────────────────┐
        │   Merkle Tree Audit Log     │  (Cryptographic Layer)
        │   + Hyperledger Fabric      │
        └─────────────────────────────┘
                      ↓
        ┌─────────────────────────────┐
        │   React Dashboard (3000)    │  (Visualization Layer)
        └─────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **Arduino IDE 2.x** (for ESP32 firmware)
- **Mosquitto MQTT broker**
- **InfluxDB 2.x**
- **Two ESP32 boards** with DHT11 sensors
- **(Optional) Hyperledger Fabric test-network**

### Run the System

Open 4 terminals and run these commands:

**Terminal 1 — MQTT Broker**
```bash
mosquitto -v
```

**Terminal 2 — InfluxDB**
```bash
influxd
```
Configure at http://localhost:8086:
- Org: `iot-lab`
- Bucket: `telemetry_v2`
- Save the API token to `backend/telemetry_api_v3.py`

**Terminal 3 — FastAPI Backend**
```bash
cd backend
pip install -r requirements.txt
python telemetry_api_v3.py
```

**Terminal 4 — React Dashboard**
```bash
cd dashboard
npm install
npm start
```

Open **http://localhost:3000** to view the dashboard.

---

## 📁 Project Structure

```
PhantomGuard/
├── README.md
├── .gitignore
│
├── backend/                          # Python backend
│   ├── telemetry_api_v3.py          # FastAPI + MQTT + detection pipeline
│   ├── dataset_builder_v2.py        # Feature engineering from InfluxDB
│   ├── train_models_v3_FIXED.py     # ML training pipeline
│   ├── evaluate_results.py          # Metrics + SHAP explainability
│   ├── merkle_logger.py             # Cryptographic audit log
│   ├── hlf_client.py                # Hyperledger Fabric async client
│   ├── ids-chaincode.js             # HLF smart contract
│   ├── requirements.txt
│   └── models/                      # Trained ML models (.pkl)
│
├── hardware/                         # ESP32 firmware
│   ├── ESP_Legit/ESP_Legit.ino      # Legitimate device
│   └── ESP_Ghost/ESP_Ghost.ino      # Attacker simulator
│
├── dashboard/                        # React frontend
│   ├── src/
│   │   ├── Dashboard.js             # Main component
│   │   ├── Dashboard.css
│   │   └── App.js
│   ├── public/
│   └── package.json
│
├── docs/                             # Documentation
│   ├── COMPLETE_DOCUMENTATION_FINAL.md
│   ├── EXECUTION_GUIDE_30MIN.md
│   ├── REACT_DASHBOARD_SETUP.md
│   └── visualizations/              # ML performance charts
│
├── explorer_config/                  # Hyperledger Explorer config
└── models/                           # Pre-trained ML models
```

---

## 🔍 Detection Logic

### Rule-Based Layer

| Rule | Condition | Verdict |
|------|-----------|---------|
| **CLONE** | UID mismatch from expected device | Cloned device detected |
| **TAMPER** | Firmware hash mismatch | Firmware compromised |
| **ANOMALY** | temp > 40°C or < 15°C<br>humidity < 25% or > 80%<br>interval < 3000ms | Behavioral anomaly |

### ML Layer

Three ensemble models trained on behavioral features:

- **XGBoost** (binary classification: attack vs. legitimate)
- **Random Forest** (multi-class: ANOMALY, TAMPER, CLONE, TRUSTED)
- **Isolation Forest** (unsupervised anomaly detection)

**Behavioral Features:**
- `temperature`, `humidity`, `interval`
- `temp_deviation` (distance from expected 30°C)
- `interval_deviation` (distance from expected 5000ms)

### Auto-Quarantine

Devices with **3+ violations** are automatically blocked for **5 minutes**. Manual release available via dashboard.

---

## 🧪 ESP32 Attack Simulator

The **ESP_Ghost** device randomly cycles through 5 attack types:

| Attack Type | Behavior | Detection Layer |
|-------------|----------|----------------|
| **Behavioral Clone** | Legit UID, faster interval (4.7–4.95s) | ML interval deviation |
| **Tamper** | Bad firmware hash | Rule-based firmware check |
| **Sensor Anomaly** | Out-of-range temp/humidity | Rule-based thresholds |
| **Clone + Anomaly** | Combined behavioral + sensor attack | Multi-layer |
| **Full Attack** | Bad firmware + anomaly + fast interval | All layers |

The Ghost uses the **same UID** as the Legit device — a true cloning scenario where identity verification fails but behavioral analysis succeeds.

---

## 📊 Dashboard Features

- **Live Metrics** — Devices tracked, violations, audit entries, HLF queue
- **Violation Charts** — Time-series line chart (updates every 2s)
- **Cryptographic Audit** — Merkle chain verification with one click
- **Detection Breakdown** — ANOMALY / TAMPER / CLONE statistics
- **Recent Events** — Last 5 security violations with timestamps
- **Device Table** — Per-device UID, violation count, quarantine status
- **Admin Controls** — Manual quarantine release

---

## 🔗 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/stats` | GET | System statistics (devices, violations, Merkle status) |
| `/telemetry` | POST | Manual telemetry submission |
| `/verify-logs` | GET | Verify Merkle chain integrity |
| `/recent-events` | GET | Last 5 security events |
| `/quarantine/{uid}/release` | POST | Release device from quarantine |

---

## 🛡️ Cryptographic Audit Log

Every detection verdict is logged to a **SHA-256 Merkle tree**:

1. Each entry is hashed: `SHA256(timestamp + device_id + verdict + ...)`
2. Hashes are chained: `current_hash = SHA256(previous_hash + current_data)`
3. Merkle root is computed and stored
4. Tampering any past entry breaks the chain — instantly detectable

Optional: Verdicts are also submitted to **Hyperledger Fabric** for immutable blockchain storage.

---

## 🔧 Hyperledger Fabric Integration (Optional)

**Chaincode:** `ids-chaincode.js` stores detection verdicts on-chain.

**Start HLF Test Network (WSL):**
```bash
cd ~/fabric-iot-ids/fabric-samples/test-network
./network.sh up createChannel -c mychannel -ca
./network.sh deployCC -ccn idsaudit -ccp "/mnt/e/My_Projects/Mini Project/backend" -ccl javascript
```

**Start Hyperledger Explorer (WSL):**
```bash
cp "/mnt/e/My_Projects/Mini Project/explorer_config/connection-profile/test-network.json" \
   /home/samuel/hlf-explorer/examples/net1/connection-profile/test-network.json

cd /home/samuel/hlf-explorer
docker-compose down -v
EXPLORER_CONFIG_FILE_PATH=/home/samuel/hlf-explorer/examples/net1/config.json \
EXPLORER_PROFILE_DIR_PATH=/home/samuel/hlf-explorer/examples/net1/connection-profile \
FABRIC_CRYPTO_PATH=/home/samuel/fabric-iot-ids/fabric-samples/test-network/organizations \
docker-compose up -d
```

Explorer UI: **http://localhost:8080** (login: `exploreradmin` / `exploreradminpw`)

---

## 📚 Documentation

- **[Complete Documentation](docs/COMPLETE_DOCUMENTATION_FINAL.md)** — Architecture, API reference, ML pipeline details
- **[30-Minute Execution Guide](docs/EXECUTION_GUIDE_30MIN.md)** — Step-by-step setup instructions
- **[Dashboard Setup Guide](docs/REACT_DASHBOARD_SETUP.md)** — React dashboard configuration

---

## 🎓 Authors

**Batch 13 — IoT (Year 3, Sem 2) — MVSREC**

| Roll No | Name | GitHub |
|---------|------|--------|
| 2451-23-749-040 | Chavada Shashank | [@shashankchavada](https://github.com/shashankchavada) |
| 2451-23-749-051 | P Samuel Vijay | [@psamuelvijay](https://github.com/psamuelvijay) |
| 2451-23-749-060 | Arikela Sriharsh | [@sriharsh-arikela](https://github.com/sriharsh-arikela) |

---

## 📄 License

This project is part of academic coursework at MVSREC.

---

## 🙏 Acknowledgments

- **Hyperledger Fabric** for blockchain infrastructure
- **InfluxDB** for time-series telemetry storage
- **SHAP** for ML explainability
- **React + Recharts** for real-time visualization
- **MVSREC IoT Department** for guidance and resources

---

**⭐ If you found this project useful, please give it a star on GitHub!**
