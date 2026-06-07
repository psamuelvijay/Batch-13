import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from sklearn.metrics import (
    classification_report, confusion_matrix,
    precision_recall_curve, roc_curve, auc
)
import shap
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# MODEL EVALUATION & EXPLAINABILITY
# SHAP values + Per-class metrics + Adversarial analysis
# ============================================================

print("="*70)
print("📊 MODEL EVALUATION & EXPLAINABILITY ANALYSIS")
print("="*70)

# ---------------- LOAD MODELS & DATA ----------------

print("\n[1/5] Loading models and test data...")

scaler = joblib.load("models/scaler.pkl")
xgb_model = joblib.load("models/xgboost_binary.pkl")
metadata = joblib.load("models/metadata.pkl")

df = pd.read_csv("clean_dataset_v2.csv")

# Prepare test set (same split as training)
from sklearn.model_selection import train_test_split

label_cols = ["is_clone", "is_tamper", "is_anomaly", "is_trusted", "attack_flag", "attack_class"]
feature_cols = metadata["feature_names"]

X = df[feature_cols].values
y_binary = df["attack_flag"].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y_binary, test_size=0.25, random_state=42, stratify=y_binary
)

X_test_scaled = scaler.transform(X_test)

print(f"✅ Loaded XGBoost model")
print(f"✅ Test set: {len(X_test)} samples")

# ---------------- PREDICTIONS ----------------

print("\n[2/5] Generating predictions...")

y_pred = xgb_model.predict(X_test_scaled)
y_pred_proba = xgb_model.predict_proba(X_test_scaled)[:, 1]

# ---------------- DETAILED METRICS ----------------

print("\n[3/5] Computing detailed metrics...")

from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score
)

acc = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred)
rec = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
auc_score = roc_auc_score(y_test, y_pred_proba)

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
tn, fp, fn, tp = cm.ravel()

# Calculate rates
fpr = fp / (fp + tn)  # False Positive Rate
fnr = fn / (fn + tp)  # False Negative Rate
tpr = tp / (tp + fn)  # True Positive Rate (Recall)
tnr = tn / (tn + fp)  # True Negative Rate (Specificity)

print("\n" + "="*70)
print("🎯 PERFORMANCE METRICS")
print("="*70)

print(f"\n📊 Classification Metrics:")
print(f"   Accuracy:  {acc:.4f} ({acc*100:.2f}%)")
print(f"   Precision: {prec:.4f} ({prec*100:.2f}%)")
print(f"   Recall:    {rec:.4f} ({rec*100:.2f}%)")
print(f"   F1-Score:  {f1:.4f}")
print(f"   ROC-AUC:   {auc_score:.4f}")

print(f"\n🎭 Confusion Matrix Breakdown:")
print(f"   True Negatives (TN):  {tn:>4} (Correctly identified normal)")
print(f"   False Positives (FP): {fp:>4} (Normal flagged as attack)")
print(f"   False Negatives (FN): {fn:>4} (Attack missed)")
print(f"   True Positives (TP):  {tp:>4} (Correctly detected attack)")

print(f"\n📈 Error Rates:")
print(f"   False Positive Rate (FPR): {fpr:.4f} ({fpr*100:.2f}%)")
print(f"   False Negative Rate (FNR): {fnr:.4f} ({fnr*100:.2f}%)")
print(f"   True Positive Rate (TPR):  {tpr:.4f} ({tpr*100:.2f}%)")
print(f"   True Negative Rate (TNR):  {tnr:.4f} ({tnr*100:.2f}%)")

# ---------------- SHAP EXPLAINABILITY ----------------

print("\n[4/5] Computing SHAP values (this may take 1-2 minutes)...")

# Sample 100 test points for SHAP (faster computation)
n_samples = min(100, len(X_test_scaled))
X_sample = X_test_scaled[:n_samples]

explainer = shap.Explainer(xgb_model, X_train[:500])  # Use 500 training samples as background
shap_values = explainer(X_sample)

print("✅ SHAP values computed")

# SHAP Summary Plot
plt.figure(figsize=(10, 8))
shap.summary_plot(shap_values, X_sample, feature_names=feature_cols, show=False)
plt.title('SHAP Feature Importance Summary')
plt.tight_layout()
plt.savefig('shap_summary.png', dpi=150, bbox_inches='tight')
print("✅ Saved 'shap_summary.png'")
plt.close()

# SHAP Bar Plot (Mean absolute impact)
plt.figure(figsize=(10, 8))
shap.plots.bar(shap_values, show=False)
plt.title('SHAP Mean Absolute Feature Impact')
plt.tight_layout()
plt.savefig('shap_importance_bar.png', dpi=150, bbox_inches='tight')
print("✅ Saved 'shap_importance_bar.png'")
plt.close()

# ---------------- THRESHOLD ANALYSIS ----------------

print("\n[5/5] Analyzing decision thresholds...")

# Precision-Recall curve
precision_vals, recall_vals, pr_thresholds = precision_recall_curve(y_test, y_pred_proba)

plt.figure(figsize=(10, 6))
plt.plot(recall_vals, precision_vals, linewidth=2, label='PR Curve')
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Precision-Recall Curve')
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig('precision_recall_curve.png', dpi=150)
print("✅ Saved 'precision_recall_curve.png'")
plt.close()

# Find optimal threshold (maximize F1)
f1_scores = 2 * (precision_vals * recall_vals) / (precision_vals + recall_vals + 1e-10)
best_threshold_idx = np.argmax(f1_scores)
best_threshold = pr_thresholds[best_threshold_idx] if best_threshold_idx < len(pr_thresholds) else 0.5

print(f"\n🎯 Optimal Decision Threshold:")
print(f"   Threshold: {best_threshold:.3f}")
print(f"   Precision: {precision_vals[best_threshold_idx]:.3f}")
print(f"   Recall:    {recall_vals[best_threshold_idx]:.3f}")
print(f"   F1-Score:  {f1_scores[best_threshold_idx]:.3f}")

# ---------------- SAMPLE PREDICTIONS ----------------

print("\n" + "="*70)
print("🔍 SAMPLE PREDICTIONS (First 10 Test Cases)")
print("="*70)

sample_df = pd.DataFrame({
    'True_Label': ['Normal' if y == 0 else 'Attack' for y in y_test[:10]],
    'Predicted': ['Normal' if y == 0 else 'Attack' for y in y_pred[:10]],
    'Confidence': y_pred_proba[:10],
    'Correct': ['✅' if y_test[i] == y_pred[i] else '❌' for i in range(10)]
})

print(sample_df.to_string(index=False))

# ---------------- FINAL REPORT ----------------

print("\n" + "="*70)
print("📝 FINAL EVALUATION REPORT")
print("="*70)

print(f"\n🏆 MODEL QUALITY ASSESSMENT:")

# Grading criteria
if acc >= 0.95 and fpr <= 0.05:
    grade = "EXCEPTIONAL ⭐⭐⭐"
elif acc >= 0.92 and fpr <= 0.10:
    grade = "EXCELLENT ⭐⭐"
elif acc >= 0.85 and fpr <= 0.15:
    grade = "GOOD ⭐"
else:
    grade = "NEEDS IMPROVEMENT ⚠️"

print(f"   Overall Grade: {grade}")
print(f"   Accuracy: {acc:.1%}")
print(f"   False Positive Rate: {fpr:.1%}")
print(f"   Detection Rate (Recall): {rec:.1%}")

print(f"\n💡 KEY INSIGHTS:")
print(f"   ✅ Model correctly identifies {acc*100:.1f}% of all cases")
print(f"   ✅ When model predicts 'Attack', it's correct {prec*100:.1f}% of the time")
print(f"   ✅ Model catches {rec*100:.1f}% of all real attacks")
print(f"   ⚠️ {fpr*100:.1f}% of normal traffic is incorrectly flagged as attack")

print(f"\n📊 Saved Artifacts:")
print(f"   ├── shap_summary.png (Feature importance visualization)")
print(f"   ├── shap_importance_bar.png (Mean absolute SHAP values)")
print(f"   ├── precision_recall_curve.png (Threshold tuning guide)")
print(f"   └── This evaluation report")

print("\n" + "="*70)
print("✅ Evaluation complete!")
print("="*70)

# Save results to text file
with open("evaluation_report.txt", "w", encoding="utf-8") as f:
    f.write("="*70 + "\n")
    f.write("IoT INTRUSION DETECTION - MODEL EVALUATION REPORT\n")
    f.write("="*70 + "\n\n")
    f.write(f"Accuracy:  {acc:.4f}\n")
    f.write(f"Precision: {prec:.4f}\n")
    f.write(f"Recall:    {rec:.4f}\n")
    f.write(f"F1-Score:  {f1:.4f}\n")
    f.write(f"ROC-AUC:   {auc_score:.4f}\n\n")
    f.write(f"False Positive Rate: {fpr:.4f}\n")
    f.write(f"False Negative Rate: {fnr:.4f}\n\n")
    f.write(f"Confusion Matrix:\n")
    f.write(f"TN: {tn}, FP: {fp}\n")
    f.write(f"FN: {fn}, TP: {tp}\n\n")
    f.write(f"Overall Grade: {grade}\n")

print("✅ Saved 'evaluation_report.txt'")