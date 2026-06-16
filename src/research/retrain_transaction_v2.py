"""Retrain the Transaction Risk model on the FULL Feedzai BAF 'Base' dataset
(1,000,000 rows) with proper categorical encoding and tuned XGBoost
hyperparameters, replacing the previous 100k-row / pd.factorize baseline.
"""
import os
import sys
import json
import time
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, RandomizedSearchCV, StratifiedKFold
from sklearn.preprocessing import OrdinalEncoder

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.ml_metrics import extended_metrics

ARTIFACT_DIR = "models/artifacts"
REPORT_DIR = "reports/models"
os.makedirs(ARTIFACT_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

CAT_COLS = ["payment_type", "employment_status", "housing_status", "source", "device_os"]


def main():
    t0 = time.time()
    print("[INFO] Loading full Feedzai BAF Base.csv (1,000,000 rows)...")
    df = pd.read_csv("datasets/raw/feedzai_baf/Base.csv")
    print(f"[INFO] Loaded {len(df):,} rows in {time.time()-t0:.1f}s")

    target = "fraud_bool"
    y = df[target].astype(int)
    X = df.drop(columns=[target])

    # Proper, savable categorical encoding (replaces the old pd.factorize
    # hack that couldn't be replicated at inference time).
    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    X[CAT_COLS] = encoder.fit_transform(X[CAT_COLS].astype(str))

    feature_cols = X.columns.tolist()

    # 70 / 15 / 15 stratified split
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )
    print(f"[INFO] Split sizes -> train={len(X_train):,} val={len(X_val):,} test={len(X_test):,}")

    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    print(f"[INFO] Fraud rate train={y_train.mean():.4%}, scale_pos_weight={scale_pos_weight:.2f}")

    # Hyperparameter search on a stratified subsample for speed, scored on PR-AUC
    # (more informative than ROC-AUC for a ~1% positive class).
    search_idx, _ = train_test_split(
        np.arange(len(X_train)), train_size=min(200_000, len(X_train)),
        random_state=42, stratify=y_train
    )
    X_search, y_search = X_train.iloc[search_idx], y_train.iloc[search_idx]

    param_dist = {
        "n_estimators": [200, 300, 400, 600],
        "max_depth": [4, 5, 6, 8],
        "learning_rate": [0.01, 0.03, 0.05, 0.1],
        "subsample": [0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.6, 0.7, 0.8, 1.0],
        "min_child_weight": [1, 3, 5, 10],
        "gamma": [0, 0.1, 0.5],
    }

    base_model = xgb.XGBClassifier(
        random_state=42, eval_metric="aucpr", tree_method="hist",
        scale_pos_weight=scale_pos_weight, n_jobs=-1,
    )

    print("[INFO] Running RandomizedSearchCV (8 iters x 3-fold) on 200k-row subsample...")
    t1 = time.time()
    search = RandomizedSearchCV(
        base_model, param_distributions=param_dist, n_iter=8,
        scoring="average_precision", cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42),
        random_state=42, n_jobs=-1, verbose=1,
    )
    search.fit(X_search, y_search)
    print(f"[INFO] Search done in {time.time()-t1:.1f}s. Best params: {search.best_params_}")

    # Final fit on the full training set with the best hyperparameters.
    best_params = search.best_params_
    model = xgb.XGBClassifier(
        random_state=42, eval_metric="aucpr", tree_method="hist",
        scale_pos_weight=scale_pos_weight, n_jobs=-1, **best_params,
    )
    print("[INFO] Final fit on full training set (700k rows)...")
    t2 = time.time()
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    print(f"[INFO] Final fit done in {time.time()-t2:.1f}s")

    # Calibrate decision threshold on validation set to maximize F1
    val_probs = model.predict_proba(X_val)[:, 1]
    thresholds = np.linspace(0.05, 0.95, 19)
    best_thresh, best_f1 = 0.5, -1
    for th in thresholds:
        from sklearn.metrics import f1_score
        f1 = f1_score(y_val, (val_probs >= th).astype(int))
        if f1 > best_f1:
            best_f1, best_thresh = f1, th
    print(f"[INFO] Best F1-maximizing threshold on val set: {best_thresh:.2f} (F1={best_f1:.4f})")

    test_probs = model.predict_proba(X_test)[:, 1]
    metrics = extended_metrics(
        y_test, test_probs, threshold=best_thresh,
        n_train=len(X_train), n_test=len(X_test),
        extra={"decision_threshold": float(best_thresh), "best_params": best_params,
               "scale_pos_weight": float(scale_pos_weight)},
    )
    print(f"[RESULT] Transaction Risk v2: {json.dumps({k: v for k, v in metrics.items() if not isinstance(v, dict)}, indent=2)}")

    # Persist artifacts
    joblib.dump(model, os.path.join(ARTIFACT_DIR, "transaction_risk.joblib"))
    joblib.dump(feature_cols, os.path.join(ARTIFACT_DIR, "transaction_features.joblib"))
    joblib.dump({"encoder": encoder, "cat_cols": CAT_COLS, "decision_threshold": best_thresh},
                 os.path.join(ARTIFACT_DIR, "transaction_preprocessor.joblib"))

    with open(os.path.join(REPORT_DIR, "Transaction_CatBoost_metrics.json"), "w") as f:
        json.dump({**metrics, "provider": "Transaction", "dataset": "Feedzai BAF (Base, full 1M rows)",
                   "model": "XGBoost (tuned)"}, f, indent=4)

    print(f"[DONE] Total time {time.time()-t0:.1f}s")
    return metrics


if __name__ == "__main__":
    main()
