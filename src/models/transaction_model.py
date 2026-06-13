import os
import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
import lightgbm as lgb
import xgboost as xgb

def train_transaction_model():
    print("[INFO] Starting Transaction Model Training...")
    
    # Load data
    df = pd.read_parquet("data/processed/transaction_data.parquet")
    
    # Sampling for dev mode
    MAX_SAMPLES = 500000
    if len(df) > MAX_SAMPLES:
        print(f"[INFO] Sampling {MAX_SAMPLES} rows for training.")
        df = df.sample(MAX_SAMPLES, random_state=42)
    
    # Define features
    features = [
        'amount', 'currency', 'transaction_type', 'merchant_category', 
        'account_age_days', 'tx_velocity_24h', 'amount_deviation', 
        'is_new_beneficiary', 'time_risk', 'country'
    ]
    target = 'is_fraud'
    
    X = df[features]
    y = df[target]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    models = {}
    metrics = {}
    
    # 1. LightGBM
    print("[INFO] Training LightGBM...")
    lgbm = lgb.LGBMClassifier(random_state=42, n_jobs=-1, verbose=-1)
    lgbm.fit(X_train, y_train)
    y_pred_proba = lgbm.predict_proba(X_test)[:, 1]
    
    models['lightgbm'] = lgbm
    metrics['lightgbm'] = {
        'roc_auc': float(roc_auc_score(y_test, y_pred_proba)),
        'f1': float(f1_score(y_test, lgbm.predict(X_test))),
        'precision': float(precision_score(y_test, lgbm.predict(X_test))),
        'recall': float(recall_score(y_test, lgbm.predict(X_test)))
    }
    
    # 2. XGBoost
    print("[INFO] Training XGBoost...")
    xgb_model = xgb.XGBClassifier(random_state=42, n_jobs=-1)
    xgb_model.fit(X_train, y_train)
    y_pred_proba_xgb = xgb_model.predict_proba(X_test)[:, 1]
    
    models['xgboost'] = xgb_model
    metrics['xgboost'] = {
        'roc_auc': float(roc_auc_score(y_test, y_pred_proba_xgb)),
        'f1': float(f1_score(y_test, xgb_model.predict(X_test))),
        'precision': float(precision_score(y_test, xgb_model.predict(X_test))),
        'recall': float(recall_score(y_test, xgb_model.predict(X_test)))
    }
    
    # Select Best
    best_model_name = max(metrics, key=lambda k: metrics[k]['roc_auc'])
    best_model = models[best_model_name]
    print(f"[SUCCESS] Best Transaction Model: {best_model_name} (AUC: {metrics[best_model_name]['roc_auc']:.4f})")
    
    # Save Model
    os.makedirs("models", exist_ok=True)
    joblib.dump(best_model, "models/transaction_model.joblib")
    
    # Explainability (Simple Feature Importance as SHAP replacement due to DLL issue)
    print("[INFO] Saving feature importance as explainer proxy...")
    importance = best_model.feature_importances_
    feat_imp = dict(zip(features, [float(x) for x in importance]))
    joblib.dump(feat_imp, "models/transaction_importance.joblib")
    
    # Experiment Tracking
    report = {
        "timestamp": datetime.now().isoformat(),
        "dataset_size": len(df),
        "model_type": best_model_name,
        "metrics": metrics[best_model_name],
        "all_metrics": metrics
    }
    os.makedirs("reports/experiments", exist_ok=True)
    with open(f"reports/experiments/transaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(report, f, indent=4)
        
    return best_model

if __name__ == "__main__":
    train_transaction_model()
