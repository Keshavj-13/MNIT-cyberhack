import pandas as pd
import numpy as np
import time
import os
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import roc_auc_score
from imblearn.combine import SMOTEENN
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer
import xgboost as xgb
import lightgbm as lgb

SEED = 42
SAMPLE_SIZE = 5000
RESULTS_DIR = "reports/research/benchmarks"

# Focal loss objective for XGBoost
def focal_loss_obj(y_true, y_pred):
    gamma = 2.0
    # y_pred is margin, we need to apply sigmoid
    p = 1.0 / (1.0 + np.exp(-y_pred))
    grad = p * (1.0 - p) * (gamma * y_true * (1.0 - p)**(gamma-1) * np.log(p + 1e-9) - y_true * (1.0 - p)**gamma / (p + 1e-9) - gamma * (1.0 - y_true) * p**(gamma-1) * np.log(1.0 - p + 1e-9) + (1.0 - y_true) * p**gamma / (1.0 - p + 1e-9))
    hess = p * (1.0 - p) # Simplified hessian for stability
    return grad, hess

def run_missing_imb():
    print("[PHASE 4] Executing Missing Imbalance...")
    df = pd.read_parquet("data/processed/transaction_data.parquet").sample(SAMPLE_SIZE, random_state=SEED)
    X = df.drop(columns=['is_fraud', 'timestamp', 'customer_id', 'device_id', 'ip_address'], errors='ignore').fillna(0)
    y = df['is_fraud']
    cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
    if cat_cols:
        X[cat_cols] = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1).fit_transform(X[cat_cols].astype(str))
    X_proc = StandardScaler().fit_transform(SimpleImputer().fit_transform(X))
    
    results = []
    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED)
    
    # Focal Loss (XGBoost)
    print("  [EXP] Focal Loss")
    start = time.time()
    try:
        model = xgb.XGBClassifier(random_state=SEED, n_jobs=-1, objective=focal_loss_obj)
        auc = cross_validate(model, X_proc, y, cv=skf, scoring='roc_auc')['test_score'].mean()
        results.append({"method": "Focal Loss", "roc_auc": float(auc), "executed": True})
    except Exception as e: print(f"    [ERR] Focal Loss: {e}")
    
    # SMOTE ENN
    print("  [EXP] SMOTE ENN")
    try:
        from imblearn.pipeline import Pipeline
        from sklearn.ensemble import RandomForestClassifier
        pipeline = Pipeline([
            ('smoteenn', SMOTEENN(random_state=SEED)),
            ('clf', RandomForestClassifier(n_estimators=50, n_jobs=-1, random_state=SEED))
        ])
        auc = cross_validate(pipeline, X_proc, y, cv=skf, scoring='roc_auc')['test_score'].mean()
        results.append({"method": "SMOTE ENN", "roc_auc": float(auc), "executed": True})
    except Exception as e: print(f"    [ERR] SMOTE ENN: {e}")

    df_res = pd.DataFrame(results)
    df_res.to_csv(f"{RESULTS_DIR}/missing_imb_leaderboard.csv", index=False)
    print("[SUCCESS] Phase 4 completed.")

if __name__ == "__main__":
    run_missing_imb()
