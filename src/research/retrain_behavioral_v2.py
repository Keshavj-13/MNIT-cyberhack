import os
import sys
import json
import time
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, RandomizedSearchCV, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.ml_metrics import extended_metrics

ARTIFACT_DIR = "models/artifacts"
REPORT_DIR = "reports/models"
os.makedirs(ARTIFACT_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

def fit_platt(logit_x, y, n_iter=500, lr=0.1):
    x = logit_x.ravel()
    y = y.astype(float)
    a, b = 1.0, 0.0
    for _ in range(n_iter):
        z = a * x + b
        p = 1.0 / (1.0 + np.exp(-z))
        a -= lr * np.mean((p - y) * x)
        b -= lr * np.mean(p - y)
    return a, b

def apply_platt(raw_probs, a, b, eps=1e-6):
    raw_probs = np.clip(raw_probs, eps, 1 - eps)
    logit = np.log(raw_probs / (1 - raw_probs))
    z = a * logit + b
    return 1.0 / (1.0 + np.exp(-z))

def main():
    t0 = time.time()
    print("[INFO] Loading CMU Keystroke DSL-StrongPasswordData.csv...")
    df = pd.read_csv("datasets/raw/cmu_keystroke/DSL-StrongPasswordData.csv")
    
    df['is_authorized'] = (df['subject'] == 's002').astype(int)
    features = [c for c in df.columns if c not in ['subject', 'sessionIndex', 'rep', 'is_authorized']]
    X = df[features]
    y = df['is_authorized']
    
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )
    
    print(f"[INFO] Split sizes -> train={len(X_train)} val={len(X_val)} test={len(X_test)}")
    neg_pos_ratio = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    
    # 1. RandomizedSearchCV for XGBoost
    xgb_param_dist = {
        "n_estimators": [100, 200, 300],
        "max_depth": [3, 4, 5, 6],
        "learning_rate": [0.01, 0.05, 0.1],
        "subsample": [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0]
    }
    xgb_model = xgb.XGBClassifier(
        random_state=42, tree_method="hist", scale_pos_weight=neg_pos_ratio, eval_metric="aucpr", n_jobs=-1
    )
    
    print("[INFO] Tuning XGBoost...")
    xgb_search = RandomizedSearchCV(
        xgb_model, xgb_param_dist, n_iter=10, scoring="average_precision", 
        cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42), n_jobs=-1, random_state=42
    )
    xgb_search.fit(X_train, y_train)
    
    # 2. RandomizedSearchCV for RandomForest
    rf_param_dist = {
        "n_estimators": [100, 200, 300],
        "max_depth": [10, 20, None],
        "min_samples_split": [2, 5],
        "min_samples_leaf": [1, 2]
    }
    rf_model = RandomForestClassifier(random_state=42, class_weight="balanced", n_jobs=-1)
    
    print("[INFO] Tuning RandomForest...")
    rf_search = RandomizedSearchCV(
        rf_model, rf_param_dist, n_iter=10, scoring="average_precision",
        cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42), n_jobs=-1, random_state=42
    )
    rf_search.fit(X_train, y_train)
    
    # Compare best scores
    if xgb_search.best_score_ >= rf_search.best_score_:
        print(f"[INFO] XGBoost selected (PR-AUC: {xgb_search.best_score_:.4f})")
        best_model = xgb_search.best_estimator_
        model_name = "XGBoost"
        best_params = xgb_search.best_params_
    else:
        print(f"[INFO] RandomForest selected (PR-AUC: {rf_search.best_score_:.4f})")
        best_model = rf_search.best_estimator_
        model_name = "RandomForest"
        best_params = rf_search.best_params_

    # Fit Platt Calibration on val set
    val_probs_raw = best_model.predict_proba(X_val)[:, 1]
    eps = 1e-6
    val_probs_raw_clipped = np.clip(val_probs_raw, eps, 1 - eps)
    val_logits = np.log(val_probs_raw_clipped / (1 - val_probs_raw_clipped))
    
    a, b = fit_platt(val_logits, y_val.values)
    print(f"[INFO] Platt Calibration fit: a={a:.4f}, b={b:.4f}")
    
    calibrated_val_probs = apply_platt(val_probs_raw, a, b)
    
    # Pick F1-maximizing threshold on val
    thresholds = np.linspace(0.05, 0.95, 19)
    best_thresh, best_f1 = 0.5, -1
    for th in thresholds:
        f1 = f1_score(y_val, (calibrated_val_probs >= th).astype(int))
        if f1 > best_f1:
            best_f1, best_thresh = f1, th
    print(f"[INFO] Best F1 threshold on val: {best_thresh:.2f} (F1={best_f1:.4f})")
    
    # Test set evaluation
    test_probs_raw = best_model.predict_proba(X_test)[:, 1]
    test_probs_calibrated = apply_platt(test_probs_raw, a, b)
    
    metrics = extended_metrics(
        y_test, test_probs_calibrated, threshold=best_thresh,
        n_train=len(X_train), n_test=len(X_test),
        extra={
            "decision_threshold": float(best_thresh),
            "best_params": best_params,
            "calibration": "Platt (logistic on logit)",
            "model_type": model_name
        }
    )
    
    print(f"[RESULT] {model_name} metrics: {json.dumps(metrics, indent=2)}")
    
    # Save artifacts
    joblib.dump({"model": best_model, "platt_a": a, "platt_b": b, "threshold": best_thresh}, 
                os.path.join(ARTIFACT_DIR, "behavioral_risk.joblib"))
    
    # Report
    report_path = os.path.join(REPORT_DIR, f"AccountTakeover_{model_name}_metrics.json")
    with open(report_path, "w") as f:
        json.dump({
            **metrics,
            "provider": "AccountTakeover",
            "dataset": "CMU CMU Keystroke Dynamics (DSL-StrongPasswordData, full 20400 rows)",
            "model": f"{model_name} (tuned) + Platt calibration"
        }, f, indent=4)
        
    print(f"[DONE] Behavioral retraining complete in {time.time()-t0:.1f}s")
    print(json.dumps(metrics))

if __name__ == "__main__":
    main()
