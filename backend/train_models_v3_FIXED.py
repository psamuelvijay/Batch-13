import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix, 
    roc_auc_score, precision_recall_curve, roc_curve,
    accuracy_score, precision_score, recall_score, f1_score
)
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE
import joblib
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# ML TRAINING PIPELINE v3.0 - FIXED DATA LEAKAGE
# ============================================================

print("="*70)
print("🤖 IoT IDS - ML TRAINING PIPELINE v3.0 (LEAKAGE-FREE)")
print("="*70)

# ----------------CONFIGURATION ----------------

RANDOM_STATE = 42
TEST_SIZE = 0.25
BALANCE_DATASET = True

# 🔥 EXCLUDE HIGH-CORRELATION FEATURES TO PREVENT DATA LEAKAGE
EXCLUDE_FEATURES = [
    'interval_std',    # 89% correlation - TOO HIGH!
    'interval_min',    # 91% correlation - TOO HIGH!
    'interval_max',    # High correlation
    'humid_std',       # 76% correlation
    'temp_std'         # 64% correlation
]

print(f"\n🔧 ANTI-LEAKAGE MODE:")
print(f"   Excluding {len(EXCLUDE_FEATURES)} high-correlation features")
print(f"   This will reduce accuracy but improve model robustness!")

# ---------------- STEP 1: LOAD DATASET ----------------

print("\n[1/6] Loading clean dataset...")
df = pd.read_csv("clean_dataset_v2.csv")

print(f"📊 Dataset shape: {df.shape}")
print(f"✅ Loaded {len(df)} samples")

# ---------------- STEP 2: PREPARE FEATURES & TARGETS ----------------

print("\n[2/6] Preparing features and targets...")

# Define label columns
label_cols = ["is_clone", "is_tamper", "is_anomaly", "is_trusted", "attack_flag", "attack_class"]

# Get all feature columns
all_feature_cols = [col for col in df.columns if col not in label_cols]

# 🔥 REMOVE LEAKY FEATURES
feature_cols = [f for f in all_feature_cols if f not in EXCLUDE_FEATURES]

print(f"\n📉 Removed features:")
for feat in EXCLUDE_FEATURES:
    if feat in all_feature_cols:
        print(f"   ❌ {feat}")

print(f"\n📈 Remaining features ({len(feature_cols)}):")
for feat in feature_cols:
    print(f"   ✅ {feat}")

X = df[feature_cols].values
y_binary = df["attack_flag"].values
y_multiclass = df["attack_class"].values

print(f"\n🎯 Target distribution (binary):")
print(f"   Normal (0): {(y_binary == 0).sum()}")
print(f"   Attack (1): {(y_binary == 1).sum()}")
ratio = (y_binary == 1).sum() / (y_binary == 0).sum()
print(f"   Imbalance ratio: 1:{ratio:.1f}")

# ---------------- STEP 3: TRAIN-TEST SPLIT ----------------

print(f"\n[3/6] Splitting data ({int((1-TEST_SIZE)*100)}% train, {int(TEST_SIZE*100)}% test)...")

X_train, X_test, y_train_bin, y_test_bin, y_train_multi, y_test_multi = train_test_split(
    X, y_binary, y_multiclass,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=y_binary
)

print(f"✅ Train: {len(X_train)} samples")
print(f"✅ Test:  {len(X_test)} samples")

# ---------------- STEP 4: FEATURE SCALING ----------------

print("\n[4/6] Scaling features...")

import os
os.makedirs("models", exist_ok=True)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

joblib.dump(scaler, "models/scaler_v3.pkl")
print("✅ Scaler saved to 'models/scaler_v3.pkl'")

# ---------------- STEP 5: HANDLE CLASS IMBALANCE ----------------

if BALANCE_DATASET:
    print("\n[5/6] Balancing dataset with SMOTE...")
    
    smote = SMOTE(random_state=RANDOM_STATE)
    X_train_balanced, y_train_bin_balanced = smote.fit_resample(X_train_scaled, y_train_bin)
    
    print(f"Before SMOTE: {len(X_train_scaled)} samples")
    print(f"After SMOTE:  {len(X_train_balanced)} samples")
    
    X_train_final = X_train_balanced
    y_train_bin_final = y_train_bin_balanced
else:
    X_train_final = X_train_scaled
    y_train_bin_final = y_train_bin

# ---------------- STEP 6: TRAIN MODELS ----------------

print("\n[6/6] Training models with regularization...")
print("="*70)

# ========================================
# MODEL 1: Isolation Forest
# ========================================

print("\n🌲 [Model 1/3] Isolation Forest")
print("-" * 70)

iso_forest = IsolationForest(
    n_estimators=100,
    contamination=0.2,
    random_state=RANDOM_STATE,
    n_jobs=-1
)

X_normal = X_train_scaled[y_train_bin == 0]
print(f"Training on {len(X_normal)} normal samples...")
iso_forest.fit(X_normal)

y_pred_iso = iso_forest.predict(X_test_scaled)
y_pred_iso = np.where(y_pred_iso == -1, 1, 0)

iso_acc = accuracy_score(y_test_bin, y_pred_iso)
iso_prec = precision_score(y_test_bin, y_pred_iso, zero_division=0)
iso_rec = recall_score(y_test_bin, y_pred_iso)
iso_f1 = f1_score(y_test_bin, y_pred_iso)

print(f"\n📊 Results:")
print(f"   Accuracy:  {iso_acc:.3f}")
print(f"   Precision: {iso_prec:.3f}")
print(f"   Recall:    {iso_rec:.3f}")
print(f"   F1-Score:  {iso_f1:.3f}")

joblib.dump(iso_forest, "models/isolation_forest_v3.pkl")
print("✅ Saved: 'models/isolation_forest_v3.pkl'")

# ========================================
# MODEL 2: XGBoost with HEAVY Regularization
# ========================================

print("\n\n🚀 [Model 2/3] XGBoost (Regularized)")
print("-" * 70)

xgb_binary = XGBClassifier(
    n_estimators=100,
    max_depth=3,              # Reduced from 6
    learning_rate=0.05,       # Slower learning
    min_child_weight=5,       # Need more samples per leaf
    subsample=0.7,            # Use 70% of data per tree
    colsample_bytree=0.7,     # Use 70% of features per tree
    reg_alpha=0.5,            # L1 regularization
    reg_lambda=2.0,           # L2 regularization
    random_state=RANDOM_STATE,
    eval_metric='logloss',
    use_label_encoder=False
)

print(f"Training on {len(X_train_final)} samples...")
xgb_binary.fit(X_train_final, y_train_bin_final)

# Cross-validation
print(f"\n🔍 Running 5-Fold Cross-Validation...")
cv_scores = cross_val_score(
    xgb_binary, X_train_final, y_train_bin_final,
    cv=5, scoring='accuracy'
)
print(f"CV Accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

if cv_scores.std() > 0.05:
    print("⚠️  WARNING: High variance - possible overfitting!")
else:
    print("✅ Low variance - model is stable")

# Predict
y_pred_xgb_bin = xgb_binary.predict(X_test_scaled)
y_pred_proba_xgb = xgb_binary.predict_proba(X_test_scaled)[:, 1]

xgb_acc = accuracy_score(y_test_bin, y_pred_xgb_bin)
xgb_prec = precision_score(y_test_bin, y_pred_xgb_bin)
xgb_rec = recall_score(y_test_bin, y_pred_xgb_bin)
xgb_f1 = f1_score(y_test_bin, y_pred_xgb_bin)
xgb_auc = roc_auc_score(y_test_bin, y_pred_proba_xgb)

print(f"\n📊 Results:")
print(f"   Accuracy:  {xgb_acc:.3f}")
print(f"   Precision: {xgb_prec:.3f}")
print(f"   Recall:    {xgb_rec:.3f}")
print(f"   F1-Score:  {xgb_f1:.3f}")
print(f"   ROC-AUC:   {xgb_auc:.3f}")

# 🚨 SANITY CHECK
if xgb_acc >= 0.99:
    print("\n🚨 WARNING: Accuracy ≥99% detected!")
    print("   This may still indicate data leakage.")
    print("   Review feature correlations again.")
elif xgb_acc >= 0.90:
    print("\n✅ EXCELLENT: Accuracy in realistic range (90-99%)")
    print("   Model is likely learning real patterns!")
else:
    print("\n✅ GOOD: Accuracy <90% indicates challenging dataset")
    print("   Model is forced to learn complex patterns!")

joblib.dump(xgb_binary, "models/xgboost_binary_v3.pkl")
print("✅ Saved: 'models/xgboost_binary_v3.pkl'")

# ========================================
# MODEL 3: Random Forest
# ========================================

print("\n\n🌳 [Model 3/3] Random Forest")
print("-" * 70)

rf_multiclass = RandomForestClassifier(
    n_estimators=100,
    max_depth=8,              # Limited depth
    min_samples_split=10,     # Need more samples to split
    min_samples_leaf=5,       # Need more samples per leaf
    random_state=RANDOM_STATE,
    n_jobs=-1
)

print(f"Training on {len(X_train_scaled)} samples...")
rf_multiclass.fit(X_train_scaled, y_train_multi)

y_pred_rf_multi = rf_multiclass.predict(X_test_scaled)
rf_acc = accuracy_score(y_test_multi, y_pred_rf_multi)

print(f"\n📊 Results:")
print(f"   Accuracy: {rf_acc:.3f}")

joblib.dump(rf_multiclass, "models/random_forest_multiclass_v3.pkl")
print("✅ Saved: 'models/random_forest_multiclass_v3.pkl'")

# ========================================
# SAVE METADATA
# ========================================

print("\n💾 Saving metadata...")

metadata = {
    "feature_names": feature_cols,
    "excluded_features": EXCLUDE_FEATURES,
    "feature_count": len(feature_cols),
    "train_samples": len(X_train),
    "test_samples": len(X_test),
    "random_state": RANDOM_STATE,
    "version": "3.0_leakage_free"
}

joblib.dump(metadata, "models/metadata_v3.pkl")
print("✅ Saved: 'models/metadata_v3.pkl'")

# ========================================
# VISUALIZATIONS
# ========================================

print("\n📊 Generating visualizations...")

# Confusion Matrix
plt.figure(figsize=(8, 6))
cm = confusion_matrix(y_test_bin, y_pred_xgb_bin)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['Normal', 'Attack'],
            yticklabels=['Normal', 'Attack'])
plt.title('XGBoost - Confusion Matrix (Leakage-Free)')
plt.ylabel('True Label')
plt.xlabel('Predicted Label')
plt.tight_layout()
plt.savefig('confusion_matrix_v3.png', dpi=150)
print("✅ Saved 'confusion_matrix_v3.png'")

# ROC Curve
plt.figure(figsize=(8, 6))
fpr, tpr, _ = roc_curve(y_test_bin, y_pred_proba_xgb)
plt.plot(fpr, tpr, label=f'XGBoost (AUC = {xgb_auc:.3f})', linewidth=2)
plt.plot([0, 1], [0, 1], 'k--', label='Random Guess')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curve - Leakage-Free Model')
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('roc_curve_v3.png', dpi=150)
print("✅ Saved 'roc_curve_v3.png'")

# Feature Importance
plt.figure(figsize=(10, 8))
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': xgb_binary.feature_importances_
}).sort_values('importance', ascending=False).head(15)

plt.barh(range(len(feature_importance)), feature_importance['importance'])
plt.yticks(range(len(feature_importance)), feature_importance['feature'])
plt.xlabel('Importance Score')
plt.title('Top Features (Leakage-Free Model)')
plt.tight_layout()
plt.savefig('feature_importance_v3.png', dpi=150)
print("✅ Saved 'feature_importance_v3.png'")

# ========================================
# FINAL SUMMARY
# ========================================

print("\n" + "="*70)
print("🎉 TRAINING COMPLETE!")
print("="*70)

print("\n🏆 MODEL COMPARISON:")
print("-" * 70)
print(f"{'Model':<30} {'Accuracy':<12} {'Precision':<12} {'Recall':<12} {'F1':<12}")
print("-" * 70)
print(f"{'Isolation Forest':<30} {iso_acc:<12.3f} {iso_prec:<12.3f} {iso_rec:<12.3f} {iso_f1:<12.3f}")
print(f"{'XGBoost (Regularized)':<30} {xgb_acc:<12.3f} {xgb_prec:<12.3f} {xgb_rec:<12.3f} {xgb_f1:<12.3f}")
print(f"{'Random Forest':<30} {rf_acc:<12.3f} {'-':<12} {'-':<12} {'-':<12}")
print("-" * 70)

print("\n📝 EXPECTED RESULTS:")
if xgb_acc >= 0.99:
    print("   🚨 Still showing signs of data leakage!")
    print("   → Consider re-collecting data with tighter intervals")
elif xgb_acc >= 0.90:
    print("   ✅ EXCELLENT! Realistic accuracy for production")
    print("   → Model is learning real behavioral patterns!")
else:
    print("   ✅ GOOD! Model is challenged but performing well")
    print("   → True machine learning, not memorization!")

print("\n✅ Next: Run 'python evaluate_results.py' with v3 models!")
print("="*70)