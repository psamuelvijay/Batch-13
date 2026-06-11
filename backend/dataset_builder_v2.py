import pandas as pd
import numpy as np

# ============================================================
# DATASET BUILDER v3.0 — LEAKAGE-FREE
#
# Key fixes vs v2:
#   1. uid_flag and firmware_flag REMOVED — trivial identity predictors
#   2. temp_out_of_range / humid_out_of_range REMOVED — thresholds
#      were hand-tuned to the attack pattern (zero false positives
#      by design = cheating)
#   3. Rolling window features computed PER-DEVICE, not globally
#   4. Dataset sorted by timestamp before windowing
#   5. Time-based train/test split (not random) enforced here
#      so the training script doesn't have to guess
#
# Features kept (pure behavioral signals):
#   temperature, humidity, interval (raw)
#   interval_deviation (abs distance from 5000ms — still useful,
#     but only as a continuous signal, not a binary flag)
#   interval_mean, interval_std  (per-device rolling)
#   temp_mean, temp_std          (per-device rolling)
#   humid_mean, humid_std        (per-device rolling)
# ============================================================

print("=" * 60)
print("DATASET BUILDER v3.0 — LEAKAGE-FREE")
print("=" * 60)

# ---------------- CONFIGURATION ----------------

WINDOW_SIZE = 10   # rolling window size per device
TRAIN_RATIO = 0.75  # first 75% of time → train, last 25% → test

# ---------------- STEP 1: LOAD RAW DATA ----------------

print("\n[1/7] Loading raw data from InfluxDB export...")

# InfluxDB CSV exports have 3 header rows before actual data
df = pd.read_csv("data.csv", skiprows=3, on_bad_lines='skip')

print(f"Raw shape: {df.shape}")
print(f"Raw columns: {list(df.columns)}")
print(df.head())

# ---------------- STEP 2: SELECT & CLEAN COLUMNS ----------------

print("\n[2/7] Cleaning columns...")

# Minimum required columns — source labels the device (legit/ghost)
required_cols = ["source", "humidity", "interval", "temperature", "verdict"]

# Check availability
available_cols = [c for c in required_cols if c in df.columns]
missing = set(required_cols) - set(available_cols)
if missing:
    print(f"WARNING: Missing columns: {missing}")
    print(f"Available: {list(df.columns)}")
    if len(available_cols) < 4:
        raise ValueError("Too many missing columns — check InfluxDB export query.")

# Keep timestamp if present (needed for time-based split)
if "_time" in df.columns:
    available_cols = ["_time"] + available_cols
elif "timestamp" in df.columns:
    available_cols = ["timestamp"] + available_cols

df = df[available_cols].copy()
df = df.dropna().drop_duplicates()

# Convert sensor columns to numeric
for col in ["humidity", "interval", "temperature"]:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df = df.dropna()
print(f"Clean rows after conversion: {len(df)}")

# ---------------- STEP 3: SORT BY TIME ----------------

print("\n[3/7] Sorting by time...")

time_col = "_time" if "_time" in df.columns else ("timestamp" if "timestamp" in df.columns else None)

if time_col:
    df = df.sort_values(time_col).reset_index(drop=True)
    print(f"Sorted by '{time_col}'")
else:
    print("WARNING: No timestamp column found — using row order as proxy.")
    print("Ensure data.csv is exported in chronological order from InfluxDB.")
    df = df.reset_index(drop=True)

# ---------------- STEP 4: FEATURE ENGINEERING ----------------

print("\n[4/7] Engineering features (no identity flags, no threshold flags)...")

# Raw behavioral signals only
df["interval_deviation"] = np.abs(df["interval"] - 5000)

# NOTE: We do NOT add uid_flag, firmware_flag, temp_out_of_range,
# humid_out_of_range. Those features perfectly encode the attack
# label and prevent the model from learning real behavioral patterns.

print("Added: interval_deviation")

# ---------------- STEP 5: PER-DEVICE ROLLING WINDOW FEATURES ----------------

print(f"\n[5/7] Computing per-device rolling window features (window={WINDOW_SIZE})...")

# CRITICAL FIX: group by source so ghost windows never contaminate legit windows
df = df.sort_values([time_col if time_col else df.index.name or "index"]).reset_index(drop=True)

groups = []
for source_val, group in df.groupby("source", sort=False):
    group = group.copy().reset_index(drop=True)

    # Rolling interval stats
    group["interval_mean"] = group["interval"].rolling(WINDOW_SIZE, min_periods=2).mean()
    group["interval_std"]  = group["interval"].rolling(WINDOW_SIZE, min_periods=2).std()

    # Rolling temperature stats
    group["temp_mean"]     = group["temperature"].rolling(WINDOW_SIZE, min_periods=2).mean()
    group["temp_std"]      = group["temperature"].rolling(WINDOW_SIZE, min_periods=2).std()

    # Rolling humidity stats
    group["humid_mean"]    = group["humidity"].rolling(WINDOW_SIZE, min_periods=2).mean()
    group["humid_std"]     = group["humidity"].rolling(WINDOW_SIZE, min_periods=2).std()

    groups.append(group)

df = pd.concat(groups).sort_values(time_col if time_col else df.index.name or "index").reset_index(drop=True)

# Drop rows with NaN windows (first few rows per device have no history)
df = df.dropna(subset=["interval_mean", "interval_std", "temp_mean",
                        "temp_std", "humid_mean", "humid_std"])

print(f"Rows after dropping incomplete windows: {len(df)}")

# ---------------- STEP 6: CONVERT VERDICTS TO LABELS ----------------

print("\n[6/7] Converting verdicts to labels...")

# CRITICAL: Use 'source' tag as binary ground truth, NOT verdict.
# Rule-based verdict misses stealthy ghost attacks (cases 0,2,3).
# source=ghost → attack regardless of what the rule engine said.
# verdict is still used for multi-class labeling (TAMPER/ANOMALY type).

def parse_verdict(v):
    v = str(v).upper()
    return {
        "is_clone":   1 if "CLONE"   in v else 0,
        "is_tamper":  1 if "TAMPER"  in v else 0,
        "is_anomaly": 1 if "ANOMALY" in v else 0,
        "is_trusted": 1 if v == "TRUSTED" else 0,
    }

labels = df["verdict"].apply(parse_verdict).apply(pd.Series)
df = pd.concat([df, labels], axis=1)

# Binary attack_flag: ground truth from source tag
# ghost = attack (1), legit = normal (0)
df["attack_flag"] = (df["source"] == "ghost").astype(int)

# For multi-class: use verdict for detected attacks,
# but any undetected ghost packet (verdict=TRUSTED but source=ghost)
# gets class 5 = STEALTHY (behavioral only, no rule trigger)
def get_attack_class(row):
    if row["source"] == "legit":       return 0  # TRUSTED/NORMAL
    if row["is_tamper"] and row["is_anomaly"]: return 1  # TAMPER+ANOMALY
    if row["is_clone"]  and row["is_anomaly"]: return 1  # CLONE+ANOMALY
    if row["is_tamper"]:               return 2  # TAMPER ONLY
    if row["is_anomaly"]:              return 3  # ANOMALY ONLY
    if row["is_clone"]:                return 4  # CLONE ONLY (rule caught it)
    return 5  # STEALTHY — ghost but rule-based missed it (behavioral only)

df["attack_class"] = df.apply(get_attack_class, axis=1)

print(f"Binary label (source-based):")
print(f"  Normal (legit):  {(df['attack_flag']==0).sum()}")
print(f"  Attack (ghost):  {(df['attack_flag']==1).sum()}")
print(f"\nMulti-class breakdown:")
class_names = {0:"NORMAL",1:"TAMPER+ANOMALY",2:"TAMPER",
               3:"ANOMALY",4:"CLONE",5:"STEALTHY"}
for cls, cnt in df["attack_class"].value_counts().sort_index().items():
    print(f"  {class_names.get(cls,'?')}: {cnt}")

# ---------------- STEP 7: TIME-BASED TRAIN/TEST SPLIT MARKER ----------------

print(f"\n[7/7] Marking time-based train/test split ({int(TRAIN_RATIO*100)}/{int((1-TRAIN_RATIO)*100)})...")

split_idx = int(len(df) * TRAIN_RATIO)
df["split"] = "test"
df.iloc[:split_idx, df.columns.get_loc("split")] = "train"

train_count = (df["split"] == "train").sum()
test_count  = (df["split"] == "test").sum()
print(f"Train rows: {train_count} | Test rows: {test_count}")

# Verify class balance in both splits
for split in ["train", "test"]:
    dist = df[df["split"] == split]["attack_flag"].value_counts()
    print(f"  {split} — Normal: {dist.get(0, 0)}, Attack: {dist.get(1, 0)}")

# ---------------- FINALIZE & SAVE ----------------

# Drop original text/identity columns — NOT used as features
# source is kept until labels are generated (above), now drop it
drop_cols = ["verdict", "source"]
if time_col and time_col in df.columns:
    drop_cols.append(time_col)

df = df.drop(columns=[c for c in drop_cols if c in df.columns])

output_file = "clean_dataset_v3.csv"
df.to_csv(output_file, index=False)

print(f"\n{'=' * 60}")
print(f"DATASET READY: '{output_file}'")
print(f"{'=' * 60}")

# ---------------- SUMMARY ----------------

feature_cols = [c for c in df.columns
                if not c.startswith("is_") and c not in
                ["attack_flag", "attack_class", "split"]]

print(f"\nTotal rows:     {len(df)}")
print(f"Feature count:  {len(feature_cols)}")
print(f"Features:       {feature_cols}")

print(f"\nLabel breakdown:")
print(f"  TRUSTED: {df['is_trusted'].sum()}")
print(f"  CLONE:   {df['is_clone'].sum()}")
print(f"  TAMPER:  {df['is_tamper'].sum()}")
print(f"  ANOMALY: {df['is_anomaly'].sum()}")

# ---------------- CORRELATION CHECK ----------------

print(f"\n{'=' * 60}")
print("FEATURE CORRELATION WITH attack_flag")
print(f"{'=' * 60}")

label_cols_drop = ["is_clone", "is_tamper", "is_anomaly",
                   "is_trusted", "attack_class", "split"]
numeric_df = df.drop(columns=[c for c in label_cols_drop if c in df.columns])
numeric_df = numeric_df.select_dtypes(include=[np.number])
corr = numeric_df.corr()["attack_flag"].drop("attack_flag").sort_values(ascending=False)

print(corr.to_string())

print("\nOVERFITTING CHECK:")
max_corr = corr.abs().max()
if max_corr > 0.95:
    print(f"CRITICAL: max correlation = {max_corr:.3f} — data leakage still present!")
elif max_corr > 0.80:
    print(f"WARNING:  max correlation = {max_corr:.3f} — review top features.")
else:
    print(f"OK:       max correlation = {max_corr:.3f} — no single feature dominates.")
    print("Expected model accuracy range: 85-95% (healthy)")

print(f"\nNext step: python train_models_v3_FIXED.py")
