"""Retrain the Environment/Network Risk model on a much larger, more diverse
sample of the SIMARGL2021 NetFlow dataset.

The previous model used only 100,000 rows from dataset-part1.csv (2.8% of
the 3.57M rows available there) and saw only 2 traffic classes (Normal flow,
SYN Scan - aggressive). dataset-part2.csv.zip (8.6M rows) adds two more
attack classes (DoS R-U-Dead-Yet, DoS Slowloris) and a much larger pool of
Normal flow traffic. This script stratified-samples ~12% of part1 and ~6%
of part2 (via chunked reads, so the full 12.2M-row corpus never needs to
fit in memory at once) for a combined ~900k-1M row training set spanning
all 4 traffic classes, then trains a tuned XGBoost classifier with extended
metrics (incl. pseudo-R^2).
"""
import os
import sys
import json
import time
import zipfile
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, RandomizedSearchCV, StratifiedKFold
from sklearn.metrics import f1_score

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.ml_metrics import extended_metrics

ARTIFACT_DIR = "models/artifacts"
REPORT_DIR = "reports/models"
os.makedirs(ARTIFACT_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

DROP_COLS = ["LABEL", "FLOW_ID", "IPV4_SRC_ADDR", "IPV4_DST_ADDR", "PROTOCOL_MAP", "L7_PROTO_NAME"]


def sample_csv(path_or_buf, frac, chunksize=500_000, label="dataset"):
    parts = []
    total = 0
    t0 = time.time()
    for i, chunk in enumerate(pd.read_csv(path_or_buf, chunksize=chunksize)):
        sampled = chunk.sample(frac=frac, random_state=42)
        parts.append(sampled)
        total += len(sampled)
        print(f"[INFO] {label} chunk {i+1}: read {len(chunk):,}, sampled {len(sampled):,} (running total {total:,})")
    df = pd.concat(parts, ignore_index=True)
    print(f"[INFO] {label} sampled {len(df):,} rows in {time.time()-t0:.1f}s")
    return df


def main():
    t0 = time.time()
    print("[INFO] Sampling dataset-part1.csv (~12%)...")
    df1 = sample_csv("datasets/raw/simargl2021/dataset-part1.csv", frac=0.12, label="part1")

    print("[INFO] Sampling dataset-part2.csv.zip (~6%)...")
    with zipfile.ZipFile("datasets/raw/simargl2021/dataset-part2.csv.zip") as z:
        with z.open("dataset-part2.csv") as f:
            df2 = sample_csv(f, frac=0.06, label="part2")

    df = pd.concat([df1, df2], ignore_index=True)
    del df1, df2
    print(f"[INFO] Combined sample: {len(df):,} rows")
    print(f"[INFO] Label distribution:\n{df['LABEL'].value_counts()}")

    y = (df["LABEL"] != "Normal flow").astype(int)
    X = df.drop(columns=[c for c in DROP_COLS if c in df.columns])

    for col in X.select_dtypes(include=["object"]).columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0)

    feature_cols = X.columns.tolist()
    print(f"[INFO] {len(feature_cols)} features, anomaly rate = {y.mean():.4%}")

    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.30, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp)
    print(f"[INFO] Split sizes -> train={len(X_train):,} val={len(X_val):,} test={len(X_test):,}")

    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)

    search_idx, _ = train_test_split(
        np.arange(len(X_train)), train_size=min(150_000, len(X_train)),
        random_state=42, stratify=y_train
    )
    X_search, y_search = X_train.iloc[search_idx], y_train.iloc[search_idx]

    param_dist = {
        "n_estimators": [200, 300, 400, 600],
        "max_depth": [4, 6, 8, 10],
        "learning_rate": [0.03, 0.05, 0.1, 0.2],
        "subsample": [0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.6, 0.7, 0.8, 1.0],
        "min_child_weight": [1, 3, 5],
    }

    base_model = xgb.XGBClassifier(
        random_state=42, eval_metric="aucpr", tree_method="hist",
        scale_pos_weight=scale_pos_weight, n_jobs=-1,
    )

    print("[INFO] Running RandomizedSearchCV (8 iters x 3-fold) on 150k-row subsample...")
    t1 = time.time()
    search = RandomizedSearchCV(
        base_model, param_distributions=param_dist, n_iter=8,
        scoring="average_precision", cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42),
        random_state=42, n_jobs=-1, verbose=1,
    )
    search.fit(X_search, y_search)
    print(f"[INFO] Search done in {time.time()-t1:.1f}s. Best params: {search.best_params_}")

    best_params = search.best_params_
    model = xgb.XGBClassifier(
        random_state=42, eval_metric="aucpr", tree_method="hist",
        scale_pos_weight=scale_pos_weight, n_jobs=-1, **best_params,
    )
    print("[INFO] Final fit on full training set...")
    t2 = time.time()
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    print(f"[INFO] Final fit done in {time.time()-t2:.1f}s")

    val_raw = model.predict_proba(X_val)[:, 1]
    eps = 1e-6
    val_logit = np.log(np.clip(val_raw, eps, 1 - eps) / (1 - np.clip(val_raw, eps, 1 - eps)))

    def fit_platt(logit_x, yy, n_iter=500, lr=0.1):
        x = logit_x.ravel()
        yy = yy.astype(float)
        a, b = 1.0, 0.0
        for _ in range(n_iter):
            z = a * x + b
            p = 1.0 / (1.0 + np.exp(-z))
            a -= lr * np.mean((p - yy) * x)
            b -= lr * np.mean(p - yy)
        return a, b

    def apply_platt(raw_probs, a, b):
        raw_probs = np.clip(raw_probs, eps, 1 - eps)
        logit = np.log(raw_probs / (1 - raw_probs))
        return 1.0 / (1.0 + np.exp(-(a * logit + b)))

    a, b = fit_platt(val_logit, y_val.to_numpy())
    print(f"[INFO] Platt params: a={a:.4f} b={b:.4f}")

    val_probs = apply_platt(val_raw, a, b)
    thresholds = np.linspace(0.05, 0.95, 19)
    best_thresh, best_f1 = 0.5, -1
    for th in thresholds:
        f1 = f1_score(y_val, (val_probs >= th).astype(int))
        if f1 > best_f1:
            best_f1, best_thresh = f1, th
    print(f"[INFO] Best F1-maximizing threshold on val set: {best_thresh:.2f} (F1={best_f1:.4f})")

    test_raw = model.predict_proba(X_test)[:, 1]
    test_probs = apply_platt(test_raw, a, b)
    metrics = extended_metrics(
        y_test, test_probs, threshold=best_thresh,
        n_train=len(X_train), n_test=len(X_test),
        extra={"decision_threshold": float(best_thresh), "best_params": best_params,
               "scale_pos_weight": float(scale_pos_weight), "calibration": "Platt (logistic on logit)"},
    )
    print(f"[RESULT] Environment Risk v2: {json.dumps({k: v for k, v in metrics.items() if not isinstance(v, dict)}, indent=2)}")

    joblib.dump({"model": model, "platt_a": a, "platt_b": b}, os.path.join(ARTIFACT_DIR, "environment_risk.joblib"))
    joblib.dump(feature_cols, os.path.join(ARTIFACT_DIR, "environment_features.joblib"))

    with open(os.path.join(REPORT_DIR, "NetworkRisk_LightGBM_metrics.json"), "w") as f:
        json.dump({**metrics, "provider": "NetworkRisk", "dataset": "SIMARGL2021 (part1+part2 stratified sample, ~1M rows, 4 classes)",
                   "model": "XGBoost (tuned) + Platt calibration"}, f, indent=4)

    print(f"[DONE] Total time {time.time()-t0:.1f}s")
    return metrics


if __name__ == "__main__":
    main()
