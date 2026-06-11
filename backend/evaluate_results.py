import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from sklearn.metrics import (
    classification_report, confusion_matrix,
    precision_recall_curve, roc_curve, roc_auc_score,
    accuracy_score, precision_score, recall_score, f1_score,
)
import shap
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# MODEL EVALUATION & EXPLAINABILITY — v4
#
# Fix: Now loads v4 models (scaler_v4, xgboost_binary_v4,
#      metadata_v4) and uses the time-based split marker from
#      clean_dataset_v3.csv instead of re-running random split.
# ============================================================

print("=" * 70)
print("MODEL EVALUATION & EXPLAINABILITY — v4")
print("=" * 70)

# ============================================================
# LOAD MODELS & DATA
# ============================================================

print("\n[1/5] Loading v4 models and dataset...")

try:
    scaler    = joblib.load("models/scaler_v4.pkl")
    xgb_model = joblib.load("models/xgboost_binary_v4.pkl")
    metadata  = joblib.load("models/metadata_v4.pkl")
except FileNotFoundError as e:
    raise FileNotFoundError(
        f"{e}\nRun train_models_v3_FIXED.py first to generate v4 models."
    )

feature_cols = metadata["feature_names"]

try:
    df = pd.read_csv("clean_dataset_v3.csv")
except FileNotFoundError:
    raise FileNotFoundError(
        "clean_dataset_v3.csv not found.\n"
        "Run dataset_builder_v2.py first."
    )

# Use the time-based split marker — same split as training
label_cols = ["is_clone", "is_tamper", "is_anomaly", "is_trusted",
              "attack_flag", "attack_class", "split"]

X         = df[feature_cols].values
y_binary  = df["attack_flag"].values
splits    = df["split"].values

X_train = X[splits == "train"]
X_test  = X[splits == "test"]
y_train = y_binary[splits == "train"]
y_test  = y_binary[splits == "test"]

X_train_scaled = scaler.transform(X_train)
X_test_scaled  = scaler.transform(X_test)

print(f"Model version: {metadata.get('version', 'unknown')}")
print(f"Features ({len(feature_cols)}): {feature_cols}")
print(f"Test set: {len(X_test)} rows")
print(f"Split strategy: {metadata.get('split_strategy', 'unknown')}")

# ============================================================
# PREDICTIONS
# ============================================================

print("\n[2/5] Generating predictions...")

y_pred       = xgb_model.predict(X_test_scaled)
y_pred_proba = xgb_model.predict_proba(X_test_scaled)[:, 1]

# ============================================================
# METRICS
# ============================================================

print("\n[3/5] Computing metrics...")

acc       = accuracy_score(y_test, y_pred)
prec      = precision_score(y_test, y_pred, zero_division=0)
rec       = recall_score(y_test, y_pred)
f1        = f1_score(y_test, y_pred)
auc_score = roc_auc_score(y_test, y_pred_proba)

cm            = confusion_matrix(y_test, y_pred)
tn, fp, fn, tp = cm.ravel()

fpr_rate = fp / (fp + tn) if (fp + tn) > 0 else 0
fnr_rate = fn / (fn + tp) if (fn + tp) > 0 else 0
tpr_rate = tp / (tp + fn) if (tp + fn) > 0 else 0
tnr_rate = tn / (tn + fp) if (tn + fp) > 0 else 0

print("\n" + "=" * 70)
print("PERFORMANCE METRICS (Time-Based Test Split)")
print("=" * 70)

print(f"\nClassification:")
print(f"  Accuracy:  {acc:.4f} ({acc*100:.2f}%)")
print(f"  Precision: {prec:.4f}")
print(f"  Recall:    {rec:.4f}")
print(f"  F1-Score:  {f1:.4f}")
print(f"  ROC-AUC:   {auc_score:.4f}")

print(f"\nConfusion Matrix:")
print(f"  TN={tn}  FP={fp}")
print(f"  FN={fn}  TP={tp}")

print(f"\nError Rates:")
print(f"  False Positive Rate: {fpr_rate:.4f} ({fpr_rate*100:.2f}%)")
print(f"  False Negative Rate: {fnr_rate:.4f} ({fnr_rate*100:.2f}%)")
print(f"  True Positive Rate:  {tpr_rate:.4f}")
print(f"  True Negative Rate:  {tnr_rate:.4f}")

# Overfitting warning
if acc >= 0.99:
    print("\nWARNING: Accuracy >=99% on hold-out set.")
    print("Re-check features in clean_dataset_v3.csv for remaining leakage.")
elif acc >= 0.88:
    print("\nHEALTHY RANGE: Accuracy 88-99%. Model is learning real patterns.")
else:
    print("\nNOTE: Accuracy <88%. May need more data or feature tuning.")

print("\nClassification Report:")
print(classification_report(y_test, y_pred,
                            target_names=["Normal", "Attack"]))

# ============================================================
# SHAP EXPLAINABILITY
# ============================================================

print("\n[4/5] Computing SHAP values...")

n_shap   = min(200, len(X_test_scaled))
X_sample = X_test_scaled[:n_shap]

# Use training data as background for SHAP
background = X_train_scaled[:min(500, len(X_train_scaled))]
explainer  = shap.Explainer(xgb_model, background)
shap_values = explainer(X_sample)

# SHAP summary plot
plt.figure(figsize=(10, 7))
shap.summary_plot(shap_values, X_sample,
                  feature_names=feature_cols, show=False)
plt.title("SHAP Feature Impact — v4")
plt.tight_layout()
plt.savefig("shap_summary_v4.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved: shap_summary_v4.png")

# SHAP bar plot
plt.figure(figsize=(10, 6))
shap.plots.bar(shap_values, show=False)
plt.title("SHAP Mean |Feature Impact| — v4")
plt.tight_layout()
plt.savefig("shap_importance_bar_v4.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved: shap_importance_bar_v4.png")

# ============================================================
# PRECISION-RECALL & ROC CURVES
# ============================================================

print("\n[5/5] Threshold analysis...")

precision_vals, recall_vals, pr_thresholds = precision_recall_curve(
    y_test, y_pred_proba)

plt.figure(figsize=(10, 6))
plt.plot(recall_vals, precision_vals, linewidth=2)
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Precision-Recall Curve — v4')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('precision_recall_curve_v4.png', dpi=150)
plt.close()
print("Saved: precision_recall_curve_v4.png")

# ROC
fpr_vals, tpr_vals, _ = roc_curve(y_test, y_pred_proba)
plt.figure(figsize=(8, 6))
plt.plot(fpr_vals, tpr_vals,
         label=f'XGBoost v4 (AUC={auc_score:.3f})', linewidth=2)
plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curve — v4')
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('roc_curve_v4.png', dpi=150)
plt.close()
print("Saved: roc_curve_v4.png")

# Optimal F1 threshold
f1_scores = (2 * precision_vals * recall_vals
             / (precision_vals + recall_vals + 1e-10))
best_idx       = np.argmax(f1_scores)
best_threshold = (pr_thresholds[best_idx]
                  if best_idx < len(pr_thresholds) else 0.5)

print(f"\nOptimal Threshold: {best_threshold:.3f}")
print(f"  At threshold — Precision: {precision_vals[best_idx]:.3f}, "
      f"Recall: {recall_vals[best_idx]:.3f}, "
      f"F1: {f1_scores[best_idx]:.3f}")

# ============================================================
# SAMPLE PREDICTIONS
# ============================================================

n_show = min(10, len(X_test))
sample = pd.DataFrame({
    'True':       ['Normal' if y == 0 else 'Attack' for y in y_test[:n_show]],
    'Predicted':  ['Normal' if y == 0 else 'Attack' for y in y_pred[:n_show]],
    'Confidence': [f"{p:.3f}" for p in y_pred_proba[:n_show]],
    'Correct':    ['Y' if y_test[i] == y_pred[i] else 'N' for i in range(n_show)]
})
print(f"\nSample predictions (first {n_show}):")
print(sample.to_string(index=False))

# ============================================================
# SAVE REPORT
# ============================================================

if acc >= 0.95 and fpr_rate <= 0.05:
    grade = "EXCELLENT"
elif acc >= 0.88 and fpr_rate <= 0.12:
    grade = "GOOD"
elif acc >= 0.80:
    grade = "ACCEPTABLE"
else:
    grade = "NEEDS IMPROVEMENT"

report = (
    "=" * 70 + "\n"
    "IoT IDS — MODEL EVALUATION REPORT v4\n"
    "=" * 70 + "\n\n"
    f"Model version:   {metadata.get('version', 'v4')}\n"
    f"Split strategy:  {metadata.get('split_strategy', 'time_based')}\n"
    f"Features used:   {len(feature_cols)}\n"
    f"Test set size:   {len(X_test)}\n\n"
    f"Accuracy:   {acc:.4f}\n"
    f"Precision:  {prec:.4f}\n"
    f"Recall:     {rec:.4f}\n"
    f"F1-Score:   {f1:.4f}\n"
    f"ROC-AUC:    {auc_score:.4f}\n\n"
    f"False Positive Rate: {fpr_rate:.4f}\n"
    f"False Negative Rate: {fnr_rate:.4f}\n\n"
    f"Confusion Matrix:\n"
    f"  TN={tn}  FP={fp}\n"
    f"  FN={fn}  TP={tp}\n\n"
    f"Grade: {grade}\n\n"
    "Removed features (data leakage):\n"
    + "\n".join(f"  - {f}" for f in metadata.get('removed_features', []))
    + "\n"
)

with open("evaluation_report_v4.txt", "w", encoding="utf-8") as fh:
    fh.write(report)

print("\n" + "=" * 70)
print(f"Grade: {grade}")
print(f"Saved: evaluation_report_v4.txt")
print("=" * 70)
