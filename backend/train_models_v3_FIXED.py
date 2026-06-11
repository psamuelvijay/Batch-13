import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix, roc_curve
)
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.model_selection import StratifiedKFold, cross_validate
import joblib
import warnings
warnings.filterwarnings('ignore')

import os
os.makedirs("models", exist_ok=True)

# ============================================================
# ML TRAINING PIPELINE v4.0 — PROPERLY LEAKAGE-FREE
#
# Fixes vs v3:
#   1. Uses clean_dataset_v3.csv (no uid_flag, firmware_flag,
#      temp_out_of_range, humid_out_of_range)
#   2. TIME-BASED split — train on first 75%, test on last 25%
#      (no random shuffling across time)
#   3. SMOTE applied INSIDE cross-validation folds only,
#      not on the full training set
#   4. No excluded features needed — leaky features are gone
#      from the dataset itself
#   5. evaluate_results.py now loads v4 models
# ============================================================

RANDOM_STATE = 42

print("=" * 70)
print("IoT IDS — ML TRAINING PIPELINE v4.0 (PROPERLY LEAKAGE-FREE)")
print("=" * 70)

# ============================================================
# STEP 1: LOAD DATASET
# ============================================================

print("\n[1/6] Loading clean dataset...")

try:
    df = pd.read_csv("clean_dataset_v3.csv")
except FileNotFoundError:
    raise FileNotFoundError(
        "clean_dataset_v3.csv not found.\n"
        "Run dataset_builder_v2.py first to generate it."
    )

print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")

# ============================================================
# STEP 2: FEATURE / LABEL SPLIT
# ============================================================

print("\n[2/6] Separating features and labels...")

label_cols    = ["is_clone", "is_tamper", "is_anomaly", "is_trusted",
                 "attack_flag", "attack_class", "split"]
feature_cols  = [c for c in df.columns if c not in label_cols]

print(f"Features ({len(feature_cols)}): {feature_cols}")

# Sanity check — none of the known leaky features should be present
FORBIDDEN = ["uid_flag", "firmware_flag", "temp_out_of_range",
             "humid_out_of_range", "source", "verdict", "_time", "timestamp"]
leaky = [f for f in feature_cols if f in FORBIDDEN]
if leaky:
    raise ValueError(
        f"Leaky features still in dataset: {leaky}\n"
        "Re-run dataset_builder_v2.py."
    )

X          = df[feature_cols].values
y_binary   = df["attack_flag"].values
y_multi    = df["attack_class"].values
split_mask = df["split"].values  # "train" or "test"

# ============================================================
# STEP 3: TIME-BASED TRAIN/TEST SPLIT
# ============================================================

print("\n[3/6] Applying time-based train/test split...")

train_mask = split_mask == "train"
test_mask  = split_mask == "test"

X_train, X_test         = X[train_mask],       X[test_mask]
y_train_bin, y_test_bin = y_binary[train_mask], y_binary[test_mask]
y_train_mul, y_test_mul = y_multi[train_mask],  y_multi[test_mask]

print(f"Train: {len(X_train)} rows | Test: {len(X_test)} rows")
print(f"Train attack rate: {y_train_bin.mean():.2%}")
print(f"Test  attack rate: {y_test_bin.mean():.2%}")

# ============================================================
# STEP 4: SCALE
# ============================================================

print("\n[4/6] Scaling features...")

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)

joblib.dump(scaler, "models/scaler_v4.pkl")
print("Saved: models/scaler_v4.pkl")

# ============================================================
# STEP 5: CROSS-VALIDATION (SMOTE INSIDE FOLDS)
# ============================================================
#
# We use imblearn Pipeline so SMOTE is fit only on training folds,
# never on validation folds. This gives honest CV scores.

print("\n[5/6] Cross-validating XGBoost with SMOTE inside folds...")

xgb_base = XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    min_child_weight=5,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=1.0,
    reg_lambda=2.0,
    random_state=RANDOM_STATE,
    eval_metric='logloss',
    use_label_encoder=False,
)

cv_pipeline = ImbPipeline([
    ("smote",  SMOTE(random_state=RANDOM_STATE)),
    ("scaler", StandardScaler()),
    ("model",  xgb_base),
])

skf = StratifiedKFold(n_splits=5, shuffle=False)  # no shuffle — respects time order

cv_results = cross_validate(
    cv_pipeline, X_train, y_train_bin,
    cv=skf,
    scoring=["accuracy", "f1", "roc_auc"],
    return_train_score=True,
)

print(f"\nCV Results (5-fold, time-ordered):")
print(f"  Train Accuracy: {cv_results['train_accuracy'].mean():.3f} "
      f"(+/- {cv_results['train_accuracy'].std():.3f})")
print(f"  Val   Accuracy: {cv_results['test_accuracy'].mean():.3f} "
      f"(+/- {cv_results['test_accuracy'].std():.3f})")
print(f"  Val   F1:       {cv_results['test_f1'].mean():.3f} "
      f"(+/- {cv_results['test_f1'].std():.3f})")
print(f"  Val   ROC-AUC:  {cv_results['test_roc_auc'].mean():.3f} "
      f"(+/- {cv_results['test_roc_auc'].std():.3f})")

gap = cv_results['train_accuracy'].mean() - cv_results['test_accuracy'].mean()
if gap > 0.10:
    print(f"\nWARNING: Train-Val gap = {gap:.3f} — possible overfitting.")
elif cv_results['test_accuracy'].mean() > 0.99:
    print(f"\nWARNING: Val accuracy still >=99% — check dataset for remaining leakage.")
else:
    print(f"\nTrain-Val gap = {gap:.3f} — model looks healthy.")

# ============================================================
# STEP 6: FINAL MODEL TRAINING
# ============================================================

print("\n[6/6] Training final models on full training set...")
print("=" * 70)

# --- SMOTE on training set (for final model only, CV is done) ---
smote = SMOTE(random_state=RANDOM_STATE)
X_train_bal, y_train_bal = smote.fit_resample(X_train_scaled, y_train_bin)
print(f"After SMOTE: {len(X_train_bal)} train rows "
      f"(was {len(X_train_scaled)})")

# =============================
# MODEL 1: XGBoost (binary)
# =============================

print("\n[Model 1/3] XGBoost Binary Classifier")
print("-" * 70)

xgb_model = XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    min_child_weight=5,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=1.0,
    reg_lambda=2.0,
    random_state=RANDOM_STATE,
    eval_metric='logloss',
    use_label_encoder=False,
)
xgb_model.fit(X_train_bal, y_train_bal)

y_pred_xgb   = xgb_model.predict(X_test_scaled)
y_proba_xgb  = xgb_model.predict_proba(X_test_scaled)[:, 1]

xgb_acc  = accuracy_score(y_test_bin, y_pred_xgb)
xgb_prec = precision_score(y_test_bin, y_pred_xgb, zero_division=0)
xgb_rec  = recall_score(y_test_bin, y_pred_xgb)
xgb_f1   = f1_score(y_test_bin, y_pred_xgb)
xgb_auc  = roc_auc_score(y_test_bin, y_proba_xgb)

print(f"  Accuracy:  {xgb_acc:.4f}")
print(f"  Precision: {xgb_prec:.4f}")
print(f"  Recall:    {xgb_rec:.4f}")
print(f"  F1-Score:  {xgb_f1:.4f}")
print(f"  ROC-AUC:   {xgb_auc:.4f}")

if xgb_acc >= 0.99:
    print("\n  WARNING: Accuracy >=99%. Possible remaining data leakage!")
    print("  Check the feature correlation report from dataset_builder_v2.py.")
elif xgb_acc >= 0.88:
    print("\n  GOOD: Accuracy in healthy range (88-99%). Model is learning real patterns.")
else:
    print("\n  NOTE: Accuracy <88%. Model is challenged — verify data quality.")

joblib.dump(xgb_model, "models/xgboost_binary_v4.pkl")
print("  Saved: models/xgboost_binary_v4.pkl")

# =============================
# MODEL 2: Random Forest (multiclass)
# =============================

print("\n[Model 2/3] Random Forest Multiclass Classifier")
print("-" * 70)

rf_model = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=RANDOM_STATE,
    n_jobs=-1,
    class_weight="balanced",  # handles imbalance without SMOTE
)
rf_model.fit(X_train_scaled, y_train_mul)

y_pred_rf = rf_model.predict(X_test_scaled)
rf_acc    = accuracy_score(y_test_mul, y_pred_rf)
print(f"  Multiclass Accuracy: {rf_acc:.4f}")

joblib.dump(rf_model, "models/random_forest_multiclass_v4.pkl")
print("  Saved: models/random_forest_multiclass_v4.pkl")

# =============================
# MODEL 3: Isolation Forest (unsupervised anomaly)
# =============================

print("\n[Model 3/3] Isolation Forest (unsupervised)")
print("-" * 70)

# Train ONLY on normal traffic — the whole point of anomaly detection
X_normal = X_train_scaled[y_train_bin == 0]
print(f"  Training on {len(X_normal)} normal-only samples...")

iso_model = IsolationForest(
    n_estimators=200,
    contamination=0.05,  # expect ~5% anomalies (conservative)
    random_state=RANDOM_STATE,
    n_jobs=-1,
)
iso_model.fit(X_normal)

y_pred_iso = iso_model.predict(X_test_scaled)
y_pred_iso = np.where(y_pred_iso == -1, 1, 0)

iso_acc  = accuracy_score(y_test_bin, y_pred_iso)
iso_prec = precision_score(y_test_bin, y_pred_iso, zero_division=0)
iso_rec  = recall_score(y_test_bin, y_pred_iso)
iso_f1   = f1_score(y_test_bin, y_pred_iso)

print(f"  Accuracy:  {iso_acc:.4f}")
print(f"  Precision: {iso_prec:.4f}")
print(f"  Recall:    {iso_rec:.4f}")
print(f"  F1-Score:  {iso_f1:.4f}")

joblib.dump(iso_model, "models/isolation_forest_v4.pkl")
print("  Saved: models/isolation_forest_v4.pkl")

# ============================================================
# SAVE METADATA
# ============================================================

metadata = {
    "feature_names":   feature_cols,
    "feature_count":   len(feature_cols),
    "train_samples":   len(X_train),
    "test_samples":    len(X_test),
    "random_state":    RANDOM_STATE,
    "version":         "4.0_leakage_free",
    "split_strategy":  "time_based",
    "smote_strategy":  "inside_cv_and_final_train_only",
    "removed_features": ["uid_flag", "firmware_flag",
                         "temp_out_of_range", "humid_out_of_range"],
    "notes": (
        "Ghost ESP32 now uses legit UID for clone attacks. "
        "Detection relies purely on behavioral signals. "
        "Rolling windows computed per-device."
    )
}

joblib.dump(metadata, "models/metadata_v4.pkl")
print("\nSaved: models/metadata_v4.pkl")

# ============================================================
# VISUALIZATIONS
# ============================================================

print("\nGenerating visualizations...")

# Confusion Matrix
cm = confusion_matrix(y_test_bin, y_pred_xgb)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['Normal', 'Attack'],
            yticklabels=['Normal', 'Attack'])
plt.title(f'XGBoost Confusion Matrix — v4 (Acc={xgb_acc:.3f})')
plt.ylabel('True Label')
plt.xlabel('Predicted Label')
plt.tight_layout()
plt.savefig('confusion_matrix_v4.png', dpi=150)
plt.close()
print("Saved: confusion_matrix_v4.png")

# ROC Curve
fpr_vals, tpr_vals, _ = roc_curve(y_test_bin, y_proba_xgb)
plt.figure(figsize=(8, 6))
plt.plot(fpr_vals, tpr_vals,
         label=f'XGBoost (AUC={xgb_auc:.3f})', linewidth=2)
plt.plot([0, 1], [0, 1], 'k--', label='Random Guess')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curve — v4 Leakage-Free Model')
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('roc_curve_v4.png', dpi=150)
plt.close()
print("Saved: roc_curve_v4.png")

# Feature Importance
fi = pd.DataFrame({
    'feature':    feature_cols,
    'importance': xgb_model.feature_importances_,
}).sort_values('importance', ascending=False)

plt.figure(figsize=(10, 6))
plt.barh(fi['feature'][::-1], fi['importance'][::-1])
plt.xlabel('Importance Score')
plt.title('XGBoost Feature Importance — v4')
plt.tight_layout()
plt.savefig('feature_importance_v4.png', dpi=150)
plt.close()
print("Saved: feature_importance_v4.png")

# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("TRAINING COMPLETE — v4 Summary")
print("=" * 70)

print(f"\n{'Model':<35} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10}")
print("-" * 70)
print(f"{'XGBoost (binary)':<35} {xgb_acc:>10.3f} {xgb_prec:>10.3f} {xgb_rec:>10.3f} {xgb_f1:>10.3f}")
print(f"{'Random Forest (multiclass)':<35} {rf_acc:>10.3f} {'-':>10} {'-':>10} {'-':>10}")
print(f"{'Isolation Forest (unsupervised)':<35} {iso_acc:>10.3f} {iso_prec:>10.3f} {iso_rec:>10.3f} {iso_f1:>10.3f}")
print("-" * 70)

print(f"\nCV Val Accuracy: {cv_results['test_accuracy'].mean():.3f} "
      f"(+/- {cv_results['test_accuracy'].std():.3f})")
print(f"CV Val ROC-AUC:  {cv_results['test_roc_auc'].mean():.3f}")

print("\nNext: Run evaluate_results.py to generate SHAP plots and full report.")
print("=" * 70)
