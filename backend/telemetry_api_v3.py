"""
IoT Intrusion Detection System - Complete Backend v3.0 FINAL
Features:
- Rule-based detection
- ML inference (XGBoost)
- Merkle tree cryptographic logging
- Hyperledger Fabric blockchain integration
- QUARANTINE system (active defense)
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
import joblib
import numpy as np
import json
from collections import defaultdict, deque
import os

# Import custom modules
from merkle_logger import MerkleTreeLogger
from hlf_client import HyperledgerFabricClient

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="IoT IDS Backend v3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# CONFIGURATION
# ============================================================

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "dZP6P1b6EcCSQsDAaFG5MWqg9eEJdb3ZrNDftQS8Z90sE2qhaAOE4uO0txEtIxezdvzikR3jJxd3Hd6Z8RJ1eQ=="
INFLUX_ORG = "iot-lab"
INFLUX_BUCKET = "telemetry_v2"

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "iot/telemetry"

LEGIT_UID = "D00061FE8CE0"
LEGIT_FIRMWARE = "dfc2dcd4"

# ML Model paths
MODEL_DIR = "models"
SCALER_PATH = f"{MODEL_DIR}/scaler_v3.pkl"
XGBOOST_PATH = f"{MODEL_DIR}/xgboost_binary_v3.pkl"
METADATA_PATH = f"{MODEL_DIR}/metadata_v3.pkl"

TRAINING_MODE = True   # Set to False for demo
HLF_ENABLED   = False  # Set to True only when Hyperledger Fabric is installed (requires Linux/WSL2)

# QUARANTINE Configuration
QUARANTINE_THRESHOLD = 3  # Block after 3 violations
QUARANTINE_DURATION = 300  # 5 minutes in seconds

# ============================================================
# GLOBAL STATE
# ============================================================

app = FastAPI(title="IoT IDS Backend v3.0")

# InfluxDB client
influx_client = None
write_api = None

# ML Models
scaler = None
xgb_model = None
feature_names = None

# Device state tracking
device_history = defaultdict(lambda: deque(maxlen=10))  # Last 10 packets per device
violation_counts = defaultdict(int)  # Track violations per UID
quarantine_list = {}  # {uid: expiry_timestamp}

# Logging systems
merkle_logger = MerkleTreeLogger()
hlf_client = HyperledgerFabricClient(
    network_path="~/fabric-iot-ids/fabric-samples/test-network"
)

# ============================================================
# MODELS
# ============================================================

class TelemetryPacket(BaseModel):
    device_id: str
    device_uid: str
    firmware_hash: str
    temperature: float
    humidity: float
    interval: int
    timestamp: int
    source: str = "unknown"

# ============================================================
# STARTUP / SHUTDOWN
# ============================================================

@app.on_event("startup")
async def startup():
    global influx_client, write_api, scaler, xgb_model, feature_names
    
    print("="*70)
    print("🚀 STARTING IOT IDS BACKEND v3.0")
    print("="*70)
    
    # Initialize InfluxDB
    print("\n[1/5] Connecting to InfluxDB...")
    influx_client = InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG
    )
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    print("✅ InfluxDB connected")
    
    # Load ML models
    print("\n[2/5] Loading ML models...")
    if os.path.exists(SCALER_PATH) and os.path.exists(XGBOOST_PATH):
        scaler = joblib.load(SCALER_PATH)
        xgb_model = joblib.load(XGBOOST_PATH)
        metadata = joblib.load(METADATA_PATH)
        feature_names = metadata['feature_names']
        print(f"✅ ML models loaded ({len(feature_names)} features)")
    else:
        print("⚠️  ML models not found - using rule-based detection only")
    
    # Initialize Merkle logger
    print("\n[3/5] Initializing Merkle logger...")
    print("✅ Merkle logger ready")
    
    # Initialize HLF client
    print("\n[4/5] Initializing blockchain client...")
    if HLF_ENABLED:
        hlf_client.start()
        print("✅ HLF client ready")
    else:
        print("⚠️  HLF disabled (set HLF_ENABLED=True when Fabric is available)")
    
    # Start MQTT listener
    print("\n[5/5] Starting MQTT subscriber...")
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
    print("✅ MQTT subscribed to:", MQTT_TOPIC)
    
    print("\n" + "="*70)
    print("✅ SYSTEM READY - Detection + Quarantine + Merkle + Blockchain")
    print("="*70)

@app.on_event("shutdown")
async def shutdown():
    print("\n🛑 Shutting down...")
    if influx_client:
        influx_client.close()
    if HLF_ENABLED:
        hlf_client.stop()
    print("✅ Shutdown complete")

# ============================================================
# MQTT CALLBACKS
# ============================================================

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        print(f"✅ MQTT connected: {MQTT_TOPIC}")
    else:
        print(f"❌ MQTT connection failed: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        packet = TelemetryPacket(**payload)
        process_telemetry(packet)
    except Exception as e:
        print(f"❌ Error processing message: {e}")

# ============================================================
# QUARANTINE SYSTEM
# ============================================================

def is_quarantined(uid: str) -> bool:
    """Check if device is quarantined"""
    if uid in quarantine_list:
        expiry = quarantine_list[uid]
        if datetime.utcnow().timestamp() < expiry:
            return True
        else:
            # Quarantine expired
            del quarantine_list[uid]
            violation_counts[uid] = 0
            print(f"🔓 Quarantine expired for {uid}")
    return False

def quarantine_device(uid: str):
    """Add device to quarantine list"""
    expiry = datetime.utcnow().timestamp() + QUARANTINE_DURATION
    quarantine_list[uid] = expiry
    
    print(f"🚨 DEVICE QUARANTINED: {uid} for {QUARANTINE_DURATION}s")
    
    # Log to InfluxDB
    point = Point("quarantine_events") \
        .tag("uid", uid) \
        .field("action", "quarantined") \
        .field("duration", QUARANTINE_DURATION) \
        .field("violations", violation_counts[uid]) \
        .time(datetime.utcnow())
    
    write_api.write(bucket=INFLUX_BUCKET, record=point)
    
    # Log to Merkle chain
    entry = merkle_logger.create_signed_entry({
        "uid": uid,
        "firmware": "UNKNOWN",
        "verdict": "QUARANTINED",
        "temperature": 0,
        "humidity": 0,
        "interval": 0,
        "timestamp_iso": datetime.utcnow().isoformat(),
    })

    log_entries.append(entry)

# ============================================================
# CORE PROCESSING PIPELINE
# ============================================================
log_entries = []
def process_telemetry(packet: TelemetryPacket):
    """
    Main processing pipeline:
    Step 0: Check quarantine
    Step 1: Rule-based detection
    Step 2: ML inference (if available)
    Step 3: Combine verdicts
    Step 4: Update device history
    Step 5: Track violations & quarantine if needed
    Step 6: Write to 3 layers (InfluxDB, Merkle, HLF)
    """
    
    uid = packet.device_uid
    
    # ========================================
    # STEP 0: QUARANTINE CHECK (SKIP IN TRAINING MODE)
    # ========================================
    
    if not TRAINING_MODE:  # Only enforce in production mode
        if is_quarantined(uid):
            print(f"🚫 BLOCKED (QUARANTINED): {uid}")
            return  # Drop packet immediately!
    
    # ========================================
    # STEP 1: RULE-BASED DETECTION
    # ========================================
    
    verdicts = []
    
    # Check UID
    if uid != LEGIT_UID:
        verdicts.append("CLONE")
    
    # Check firmware
    if packet.firmware_hash != LEGIT_FIRMWARE:
        verdicts.append("TAMPER")
    
    # Check sensor ranges
    if packet.temperature < 25 or packet.temperature > 40:
        verdicts.append("ANOMALY")
    
    if packet.humidity < 20 or packet.humidity > 70:
        if "ANOMALY" not in verdicts:
            verdicts.append("ANOMALY")
    
    # Check interval
    if packet.interval < 4000 or packet.interval > 6000:
        if "ANOMALY" not in verdicts:
            verdicts.append("ANOMALY")
    
    rule_verdict = "|".join(verdicts) if verdicts else "TRUSTED"
    
    # ========================================
    # STEP 2: ML INFERENCE (IF AVAILABLE)
    # ========================================
    
    ml_verdict = None
    ml_confidence = 0.0
    
    if scaler and xgb_model:
        features = extract_features(packet, uid)
        
        if features is not None:
            try:
                # Scale features
                features_scaled = scaler.transform([features])
                
                # Predict
                prediction = xgb_model.predict(features_scaled)[0]
                confidence = xgb_model.predict_proba(features_scaled)[0]
                
                ml_verdict = "ATTACK" if prediction == 1 else "NORMAL"
                ml_confidence = float(confidence[1])  # Probability of attack
                
            except Exception as e:
                print(f"⚠️  ML inference failed: {e}")
    
    # ========================================
    # STEP 3: COMBINE VERDICTS
    # ========================================
    
    # Final verdict is rule-based (more interpretable)
    # But we log ML confidence for analysis
    final_verdict = rule_verdict
    
    # If ML strongly disagrees with rules, note it
    if ml_verdict == "ATTACK" and rule_verdict == "TRUSTED" and ml_confidence > 0.8:
        final_verdict = "ANOMALY|ML_FLAGGED"
    
    # ========================================
    # STEP 4: UPDATE DEVICE HISTORY
    # ========================================
    
    device_history[uid].append({
        "temperature": packet.temperature,
        "humidity": packet.humidity,
        "interval": packet.interval,
        "timestamp": packet.timestamp
    })
    
    # ========================================
    # STEP 5: VIOLATION TRACKING & QUARANTINE
    # ========================================
    
    if final_verdict != "TRUSTED":
        violation_counts[uid] += 1
        print(f"⚠️  Violation #{violation_counts[uid]} for {uid}: {final_verdict}")
        
        if not TRAINING_MODE:  # Only quarantine in production mode
            if violation_counts[uid] >= QUARANTINE_THRESHOLD:
                quarantine_device(uid)
                return  # Stop processing this packet
    
    # ========================================
    # STEP 6: WRITE TO 3 LAYERS
    # ========================================
    
    # Layer 1: InfluxDB (fast metrics)
    point = Point("telemetry") \
        .tag("device_id", packet.device_id) \
        .tag("source", packet.source) \
        .tag("uid", uid) \
        .tag("verdict", final_verdict) \
        .field("temperature", packet.temperature) \
        .field("humidity", packet.humidity) \
        .field("interval", packet.interval) \
        .field("ml_confidence", ml_confidence) \
        .time(datetime.utcnow())
    
    write_api.write(bucket=INFLUX_BUCKET, record=point)
    
    # Layer 2: Merkle logger (crypto proof)
    entry_data = {
        "uid": uid,
        "firmware": packet.firmware_hash,
        "verdict": final_verdict,
        "temperature": packet.temperature,
        "humidity": packet.humidity,
        "interval": packet.interval,
        "ml_confidence": ml_confidence,
        "timestamp_iso": datetime.utcnow().isoformat(),
    }
    
    entry = merkle_logger.create_signed_entry(entry_data)
    log_entries.append(entry)
    print(f"✅ Signed: {uid} → {final_verdict}")
    
    # Layer 3: Blockchain (async audit trail)
    if HLF_ENABLED:
        hlf_client.submit_verdict({
            "deviceId": packet.device_id,
            "uid": uid,
            "firmware": packet.firmware_hash,
            "verdict": final_verdict,
            "temperature": packet.temperature,
            "humidity": packet.humidity,
            "interval": packet.interval,
            "timestamp": packet.timestamp
        })
        print(f"📝 Queued for HLF: {uid}")

# ============================================================
# FEATURE EXTRACTION FOR ML
# ============================================================

def extract_features(packet: TelemetryPacket, uid: str):
    """Extract 11 features for ML model"""
    
    history = list(device_history[uid])
    
    if len(history) < 2:
        return None  # Need at least 2 packets for window features
    
    # Base features
    humidity = packet.humidity
    interval = packet.interval
    temperature = packet.temperature
    uid_flag = 0 if uid == LEGIT_UID else 1
    firmware_flag = 0 if packet.firmware_hash == LEGIT_FIRMWARE else 1
    
    # Engineered features
    interval_deviation = abs(interval - 5000)
    temp_out_of_range = 1 if (temperature < 25 or temperature > 35) else 0
    humid_out_of_range = 1 if (humidity < 30 or humidity > 65) else 0
    
    # Sliding window features (mean only, no std/min/max to avoid leakage)
    intervals = [h['interval'] for h in history]
    temps = [h['temperature'] for h in history]
    humids = [h['humidity'] for h in history]
    
    interval_mean = np.mean(intervals)
    temp_mean = np.mean(temps)
    humid_mean = np.mean(humids)
    
    # Return features in exact order expected by model
    features = [
        humidity,
        interval,
        temperature,
        uid_flag,
        firmware_flag,
        interval_deviation,
        temp_out_of_range,
        humid_out_of_range,
        interval_mean,
        temp_mean,
        humid_mean
    ]
    
    return features

# ============================================================
# REST API ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return {
        "service": "IoT IDS Backend v3.0",
        "status": "online",
        "features": ["rules", "ml", "merkle", "blockchain", "quarantine"]
    }

@app.get("/stats")
async def stats():
    """System statistics"""
    
    merkle_stats = merkle_logger.get_statistics(log_entries)
    
    return {
        "devices_tracked": len(device_history),
        "violations": dict(violation_counts),
        "quarantined_devices": list(quarantine_list.keys()),
        "merkle_chain": {
            "total_entries": merkle_stats['total_entries'],
            "chain_valid": merkle_stats['chain_valid'],
            "merkle_root": merkle_stats['merkle_root']
        },
        "hlf_queue_size": hlf_client.queue.qsize() if HLF_ENABLED else 0
    }

@app.get("/verify-logs")
async def verify_logs():
    is_valid, msg = merkle_logger.verify_chain(log_entries)
    return {
        "chain_valid": is_valid,
        "message": msg
    }

@app.get("/quarantine/{uid}")
async def get_quarantine_status(uid: str):
    """Check if device is quarantined"""
    if uid in quarantine_list:
        expiry = quarantine_list[uid]
        remaining = max(0, expiry - datetime.utcnow().timestamp())
        return {
            "quarantined": True,
            "uid": uid,
            "remaining_seconds": int(remaining),
            "violations": violation_counts.get(uid, 0)
        }
    return {
        "quarantined": False,
        "uid": uid
    }

@app.post("/quarantine/{uid}/release")
async def release_quarantine(uid: str):
    """Manually release device from quarantine (admin)"""
    if uid in quarantine_list:
        del quarantine_list[uid]
        violation_counts[uid] = 0
        
        # Log release
        point = Point("quarantine_events") \
            .tag("uid", uid) \
            .field("action", "released") \
            .time(datetime.utcnow())
        
        write_api.write(bucket=INFLUX_BUCKET, record=point)
        
        return {"message": f"Released {uid} from quarantine"}
    
    raise HTTPException(status_code=404, detail="Device not quarantined")

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)