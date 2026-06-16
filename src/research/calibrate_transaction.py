"""Recalibrate the v2 Transaction Risk model's probability outputs.

The tuned XGBoost (scale_pos_weight=89.67) gives strong ranking (ROC-AUC
0.903) but badly miscalibrated probabilities (Brier=0.117, R^2=-9.77) because
scale_pos_weight inflates predicted probabilities for the positive class.
Sigmoid (Platt) calibration on the held-out validation set fixes calibration
-- and therefore R^2/Brier -- without changing the ranking-based ROC-AUC/PR-AUC
(a monotonic transform preserves rank order).
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score


def fit_platt(logit_x, y, n_iter=500, lr=0.1):
    """2-parameter Platt scaling p = sigmoid(a*x + b), fit via plain-numpy
    gradient descent. Avoids sklearn.linear_model, which crashes the
    process (silent exit 127) when called in the same process as a
    loaded XGBoost model on this machine (OpenMP runtime conflict)."""
    x = logit_x.ravel()
    y = y.astype(float)
    a, b = 1.0, 0.0
    n = len(x)
    for _ in range(n_iter):
        z = a * x + b
        p = 1.0 / (1.0 + np.exp(-z))
        grad_a = np.mean((p - y) * x)
        grad_b = np.mean(p - y)
        a -= lr * grad_a
        b -= lr * grad_b
    return a, b


def apply_platt(raw_probs, a, b, eps=1e-6):
    raw_probs = np.clip(raw_probs, eps, 1 - eps)
    logit = np.log(raw_probs / (1 - raw_probs))
    z = a * logit + b
    return 1.0 / (1.0 + np.exp(-z))

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.ml_metrics import extended_metrics

ARTIFACT_DIR = "models/artifacts"
REPORT_DIR = "reports/models"


def main():
    print("[INFO] Loading full Feedzai BAF Base.csv...")
    df = pd.read_csv("datasets/raw/feedzai_baf/Base.csv")
    target = "fraud_bool"
    y = df[target].astype(int)
    X = df.drop(columns=[target])

    preproc = joblib.load(os.path.join(ARTIFACT_DIR, "transaction_preprocessor.joblib"))
    encoder, cat_cols = preproc["encoder"], preproc["cat_cols"]
    X[cat_cols] = encoder.transform(X[cat_cols].astype(str))

    feature_cols = joblib.load(os.path.join(ARTIFACT_DIR, "transaction_features.joblib"))
    X = X[feature_cols]

    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.30, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp)

    model = joblib.load(os.path.join(ARTIFACT_DIR, "transaction_risk.joblib"))

    print("[INFO] Fitting Platt (sigmoid) calibrator on validation set...")
    val_raw = model.predict_proba(X_val)[:, 1]
    eps = 1e-6
    val_logit = np.log(np.clip(val_raw, eps, 1 - eps) / (1 - np.clip(val_raw, eps, 1 - eps)))
    a, b = fit_platt(val_logit, y_val.to_numpy())
    print(f"[INFO] Platt params: a={a:.4f} b={b:.4f}")

    def calibrate(raw_probs):
        return apply_platt(raw_probs, a, b, eps)

    # Re-calibrate decision threshold for F1 on val set with calibrated probs
    val_probs = calibrate(val_raw)
    thresholds = np.linspace(0.05, 0.95, 19)
    best_thresh, best_f1 = 0.5, -1
    for th in thresholds:
        f1 = f1_score(y_val, (val_probs >= th).astype(int))
        if f1 > best_f1:
            best_f1, best_thresh = f1, th
    print(f"[INFO] Re-calibrated F1-max threshold: {best_thresh:.2f} (F1={best_f1:.4f})")

    test_raw = model.predict_proba(X_test)[:, 1]
    test_probs = calibrate(test_raw)
    metrics = extended_metrics(
        y_test, test_probs, threshold=best_thresh,
        n_train=len(X_train), n_test=len(X_test),
        extra={"decision_threshold": float(best_thresh), "calibration": "Platt (logistic on logit)"},
    )
    print(f"[RESULT] Transaction Risk v2 (calibrated): {json.dumps(metrics, indent=2)}")

    calibrated = {"model": model, "platt_a": a, "platt_b": b}
    joblib.dump(calibrated, os.path.join(ARTIFACT_DIR, "transaction_risk.joblib"))
    preproc["decision_threshold"] = best_thresh
    joblib.dump(preproc, os.path.join(ARTIFACT_DIR, "transaction_preprocessor.joblib"))

    with open(os.path.join(REPORT_DIR, "Transaction_CatBoost_metrics.json"), "w") as f:
        json.dump({**metrics, "provider": "Transaction", "dataset": "Feedzai BAF (Base, full 1M rows)",
                   "model": "XGBoost (tuned) + Platt calibration"}, f, indent=4)


if __name__ == "__main__":
    main()
