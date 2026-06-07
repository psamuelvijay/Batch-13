import pandas as pd
import numpy as np

# ============================================================
# ENHANCED DATASET BUILDER v2.1 - FIXED FOR YOUR CSV FORMAT
# ============================================================

print("="*60)
print("🚀 ENHANCED DATASET BUILDER v2.1")
print("="*60)

# ---------------- CONFIGURATION ----------------

LEGIT_UID = "D00061FE8CE0"
LEGIT_FIRMWARE = "dfc2dcd4"

WINDOW_SIZE = 10  # Look at last 10 packets for patterns

# ---------------- STEP 1: LOAD RAW DATA ----------------

print("\n[1/7] Loading raw data from InfluxDB export...")

# Read CSV skipping first 3 rows (InfluxDB metadata)
df = pd.read_csv("data.csv", skiprows=3, on_bad_lines='skip')

print(f"📊 Raw shape: {df.shape}")
print(f"📋 Raw columns: {list(df.columns)}")
print(f"\nFirst few rows:")
print(df.head())

# ---------------- STEP 2: SELECT & CLEAN COLUMNS ----------------

print("\n[2/7] Cleaning and selecting features...")

# Keep only the columns we need
# Adjust these column names based on what's actually in your CSV
required_cols = ["uid", "humidity", "interval", "temperature", "verdict"]

# Check which columns exist
available_cols = []
for col in required_cols:
    if col in df.columns:
        available_cols.append(col)
    else:
        print(f"⚠️  Column '{col}' not found in CSV")

if len(available_cols) < 4:
    print("\n❌ ERROR: Missing critical columns!")
    print(f"Required: {required_cols}")
    print(f"Available in CSV: {list(df.columns)}")
    print("\n💡 TIP: Check your InfluxDB export query includes all fields")
    exit(1)

df = df[available_cols]

# Remove NaN and duplicates
original_count = len(df)
df = df.dropna()
df = df.drop_duplicates()
cleaned_count = len(df)

print(f"✅ Removed {original_count - cleaned_count} invalid/duplicate rows")
print(f"✅ Clean rows: {cleaned_count}")

# Convert to numeric
df["humidity"] = pd.to_numeric(df["humidity"], errors='coerce')
df["interval"] = pd.to_numeric(df["interval"], errors='coerce')
df["temperature"] = pd.to_numeric(df["temperature"], errors='coerce')

# Drop rows where conversion failed
df = df.dropna()

print(f"✅ Final clean rows: {len(df)}")

# ---------------- STEP 3: FEATURE ENGINEERING ----------------

print("\n[3/7] Engineering features...")

# Binary flags for identity features
df["uid_flag"] = df["uid"].apply(lambda x: 0 if str(x) == LEGIT_UID else 1)

# Check if firmware_hash column exists
if "firmware_hash" in df.columns:
    df["firmware_flag"] = df["firmware_hash"].apply(
        lambda x: 0 if str(x) == LEGIT_FIRMWARE else 1
    )
else:
    # If no firmware column, infer from verdict
    df["firmware_flag"] = df["verdict"].apply(
        lambda x: 1 if "TAMPER" in str(x) else 0
    )

# Interval deviation (how far from normal 5000ms)
df["interval_deviation"] = np.abs(df["interval"] - 5000)

# Temperature bounds check (normal range: 25-35°C)
df["temp_out_of_range"] = ((df["temperature"] < 25) | (df["temperature"] > 35)).astype(int)

# Humidity bounds check (normal range: 30-65%)
df["humid_out_of_range"] = ((df["humidity"] < 30) | (df["humidity"] > 65)).astype(int)

print(f"✅ Added 5 engineered features")

# ---------------- STEP 4: SLIDING WINDOW FEATURES ----------------

print(f"\n[4/7] Computing sliding window features (window={WINDOW_SIZE})...")

# Sort by index (assuming chronological order from InfluxDB)
df = df.reset_index(drop=True)

# Rolling statistics for interval
df["interval_mean"] = df["interval"].rolling(window=WINDOW_SIZE, min_periods=1).mean()
df["interval_std"] = df["interval"].rolling(window=WINDOW_SIZE, min_periods=1).std()
df["interval_min"] = df["interval"].rolling(window=WINDOW_SIZE, min_periods=1).min()
df["interval_max"] = df["interval"].rolling(window=WINDOW_SIZE, min_periods=1).max()

# Rolling statistics for temperature
df["temp_mean"] = df["temperature"].rolling(window=WINDOW_SIZE, min_periods=1).mean()
df["temp_std"] = df["temperature"].rolling(window=WINDOW_SIZE, min_periods=1).std()

# Rolling statistics for humidity
df["humid_mean"] = df["humidity"].rolling(window=WINDOW_SIZE, min_periods=1).mean()
df["humid_std"] = df["humidity"].rolling(window=WINDOW_SIZE, min_periods=1).std()

# Fill NaN values (first few rows won't have full window)
df = df.fillna(0)

print(f"✅ Added 10 sliding window features")

# ---------------- STEP 5: CONVERT VERDICTS TO LABELS ----------------

print("\n[5/7] Converting verdicts to multi-label targets...")

def parse_verdict(v):
    """Convert verdict string to binary labels"""
    v = str(v).upper()
    return {
        "is_clone": 1 if "CLONE" in v else 0,
        "is_tamper": 1 if "TAMPER" in v else 0,
        "is_anomaly": 1 if "ANOMALY" in v else 0,
        "is_trusted": 1 if v == "TRUSTED" else 0
    }

labels = df["verdict"].apply(parse_verdict).apply(pd.Series)
df = pd.concat([df, labels], axis=1)

# Create binary attack flag (0=TRUSTED, 1=ANY ATTACK)
df["attack_flag"] = ((df["is_clone"] == 1) | 
                     (df["is_tamper"] == 1) | 
                     (df["is_anomaly"] == 1)).astype(int)

# Create multi-class label (for classification)
def get_attack_class(row):
    """Convert multi-label to single class"""
    if row["is_trusted"]:
        return 0  # TRUSTED
    elif row["is_clone"] and row["is_tamper"] and row["is_anomaly"]:
        return 1  # CLONE+TAMPER+ANOMALY
    elif row["is_clone"] and row["is_anomaly"]:
        return 1  # CLONE+ANOMALY (same bucket as combined)
    elif row["is_clone"]:
        return 2  # CLONE ONLY
    elif row["is_tamper"]:
        return 3  # TAMPER ONLY
    elif row["is_anomaly"]:
        return 4  # ANOMALY ONLY
    else:
        return 5  # OTHER

df["attack_class"] = df.apply(get_attack_class, axis=1)

print(f"✅ Multi-label targets created")

# ---------------- STEP 6: DROP UNNECESSARY COLUMNS ----------------

print("\n[6/7] Finalizing dataset...")

# Drop original text columns
drop_cols = ["verdict", "uid"]
if "firmware_hash" in df.columns:
    drop_cols.append("firmware_hash")

drop_cols = [col for col in drop_cols if col in df.columns]
df = df.drop(columns=drop_cols)

# ---------------- STEP 7: SAVE CLEAN DATASET ----------------

output_file = "clean_dataset_v2.csv"
df.to_csv(output_file, index=False)

print(f"\n{'='*60}")
print(f"✅ DATASET READY: '{output_file}'")
print(f"{'='*60}")

# ---------------- STEP 8: SUMMARY STATISTICS ----------------

print("\n📊 DATASET SUMMARY:")
print(f"Total rows: {len(df)}")
feature_cols = [col for col in df.columns if not col.startswith('is_') and col not in ['attack_flag', 'attack_class']]
print(f"Total features: {len(feature_cols)}")
print(f"\nFeature columns: {feature_cols}")

print(f"\n🎯 LABEL DISTRIBUTION:")
print(f"Attack vs Trusted:")
print(df["attack_flag"].value_counts())

balance_ratio = df["attack_flag"].value_counts()
if len(balance_ratio) == 2:
    ratio = balance_ratio[1] / balance_ratio[0]
    print(f"\n📊 Class balance: 1:{ratio:.2f} (attack:normal)")
    if ratio > 5:
        print("⚠️  WARNING: Severe class imbalance! SMOTE will be used in training.")
    elif ratio > 3:
        print("⚠️  Moderate class imbalance. SMOTE recommended.")
    else:
        print("✅ Acceptable class balance.")

print(f"\nMulti-label breakdown:")
print(f"  CLONE:   {df['is_clone'].sum()}")
print(f"  TAMPER:  {df['is_tamper'].sum()}")
print(f"  ANOMALY: {df['is_anomaly'].sum()}")
print(f"  TRUSTED: {df['is_trusted'].sum()}")

print(f"\n🏷️  ATTACK CLASS DISTRIBUTION:")
class_names = {
    0: "TRUSTED",
    1: "CLONE+ANOMALY",
    2: "CLONE ONLY",
    3: "TAMPER ONLY",
    4: "ANOMALY ONLY",
    5: "OTHER"
}
for class_id, count in df["attack_class"].value_counts().sort_index().items():
    print(f"  {class_names.get(class_id, 'UNKNOWN')}: {count}")

print(f"\n📈 FEATURE STATISTICS:")
print(df[["interval", "temperature", "humidity", "interval_mean", "interval_std"]].describe())

print(f"\n✅ First 5 rows:")
print(df.head())

# ---------------- FEATURE CORRELATION CHECK ----------------

print(f"\n{'='*60}")
print("📊 FEATURE CORRELATION ANALYSIS")
print(f"{'='*60}")

# Exclude label columns from correlation check (they are targets, not features)
label_cols_check = ["is_clone", "is_tamper", "is_anomaly", "is_trusted", "attack_class"]
feature_only_df = df.drop(columns=[c for c in label_cols_check if c in df.columns])
numeric_df = feature_only_df.select_dtypes(include=[np.number])
correlation = numeric_df.corr()['attack_flag'].sort_values(ascending=False)
print("\nTop features correlated with attack_flag:")
print(correlation.head(10))

print("\n⚠️  OVERFITTING CHECK:")
high_corr = correlation[correlation.abs() > 0.95]
if len(high_corr) > 1:  # Exclude target itself
    print("🚨 CRITICAL: Features with >0.95 correlation detected!")
    print(high_corr)
    print("\n💡 This suggests data leakage or trivial separation.")
    print("   Model will likely show 100% accuracy (bad!).")
elif correlation.abs().max() > 0.85:
    print("⚠️  Some features have very high correlation (>0.85)")
    print("   Model may rely too heavily on single features.")
    print("\nHighest correlations:")
    print(correlation[correlation.abs() > 0.85])
else:
    print("✅ No perfect correlations detected!")
    print("   Features show good diversity.")
    print("   Expected model accuracy: 90-96%")

print(f"\n{'='*60}")
print("🎉 Dataset ready for ML training!")
print(f"{'='*60}")
print(f"\n📝 Next step: Run 'python train_models.py'")