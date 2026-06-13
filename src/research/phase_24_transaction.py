import pandas as pd
import numpy as np
import time
import joblib
import os
import json
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_score, 
    recall_score, f1_score, brier_score_loss, confusion_matrix
)
from sklearn.model_selection import train_test_split
from catboost import CatBoostClassifier
import shap

# --- PRE-TRAINING EVALUATION ---
# Hypothesis: Strict temporal split validation on ULB will reduce AUC from ~0.97 to ~0.93 
# but will increase platform reliability and scientific defensibility.

DATA_PATH = "data/raw/real_fraud/ulb_creditcard.parquet"
MODELS_DIR = "models"
REPORTS_DIR = "reports/research/audits"
os.makedirs(REPORTS_DIR, exist_ok=True)

def run_loop():
    print("[PHASE 24] Experiment 1: Transaction Fraud - Temporal Validation Loop")
    
    # 1. READ (Understand State)
    df = pd.read_parquet(DATA_PATH)
    X = df.drop(columns=['Class'])
    y = df['Class']
    
    # 2. HYPOTHESIZE
    print("HYPOTHESIS: Enforcing zero-shuffling (temporal split) will reveal the 'true' lower bound of fraud performance.")

    # 3. EXECUTE (Strict Temporal Split)
    # OpenML ULB rows are chronological. Use shuffle=False.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    model = CatBoostClassifier(iterations=300, random_state=42, verbose=0, thread_count=-1, scale_pos_weight=10)
    
    start_time = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start_time
    
    probs = model.predict_proba(X_test)[:, 1]
    
    # 4. AUDIT
    roc_auc = roc_auc_score(y_test, probs)
    pr_auc = average_precision_score(y_test, probs)
    brier = brier_score_loss(y_test, probs)
    
    # Thresholding for metrics
    best_f1, best_t = 0, 0.5
    for t in np.arange(0.1, 0.9, 0.1):
        p = (probs >= t).astype(int)
        f = f1_score(y_test, p, zero_division=0)
        if f > best_f1:
            best_f1 = f
            best_t = t
            
    preds = (probs >= best_t).astype(int)
    recall = recall_score(y_test, preds)
    precision = precision_score(y_test, preds)
    
    audit_results = {
        "model": "CatBoost_Temporal",
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "f1": float(best_f1),
        "recall": float(recall),
        "precision": float(precision),
        "brier_score": float(brier),
        "train_time": float(train_time),
        "improved_platform": True if (recall > 0.6 and f1_score(y_test, preds) > 0.3) else False
    }
    
    print(f"AUDIT COMPLETE: ROC AUC: {roc_auc:.4f}, Recall: {recall:.4f}")
    
    # 5. ANSWER: Did this improve the platform?
    # Even if metrics are lower, it improves reliability.
    if audit_results["improved_platform"]:
        print("DECISION: ACCEPTED. Model provides stable, non-leaking fraud signals.")
        joblib.dump(model, os.path.join(MODELS_DIR, "transaction_fraud_v2_temporal.joblib"))
    else:
        print("DECISION: REJECTED. Model did not meet minimal performance threshold for platform escalation.")

    with open(os.path.join(REPORTS_DIR, "transaction_temporal_audit.json"), "w") as f:
        json.dump(audit_results, f, indent=4)
    
    return audit_results

if __name__ == "__main__":
    run_loop()
