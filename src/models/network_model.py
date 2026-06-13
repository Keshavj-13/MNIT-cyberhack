import os
import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
import xgboost as xgb

def train_network_model():
    print("[INFO] Starting Network Model Training (XGBoost Only due to DLL restriction)...")
    
    # Load data
    df = pd.read_parquet("data/processed/network_data.parquet")
    
    # Sampling
    MAX_SAMPLES = 500000
    if len(df) > MAX_SAMPLES:
        df = df.sample(MAX_SAMPLES, random_state=42)
    
    # Define features
    features = [
        'Destination Port', 'Flow Duration', 'Total Fwd Packets', 
        'Total Backward Packets', 'Fwd Packet Length Max', 
        'Bwd Packet Length Max', 'Flow Bytes/s', 'Flow Packets/s'
    ]
    target = 'Label_Encoded'
    y_binary = (df[target] != 0).astype(int)
    
    X = df[features]
    y = y_binary
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # XGBoost
    print("[INFO] Training XGBoost...")
    xgb_model = xgb.XGBClassifier(random_state=42, n_jobs=-1)
    xgb_model.fit(X_train, y_train)
    y_pred_proba_xgb = xgb_model.predict_proba(X_test)[:, 1]
    
    metrics = {
        'roc_auc': float(roc_auc_score(y_test, y_pred_proba_xgb)),
        'f1': float(f1_score(y_test, xgb_model.predict(X_test))),
        'precision': float(precision_score(y_test, xgb_model.predict(X_test))),
        'recall': float(recall_score(y_test, xgb_model.predict(X_test)))
    }
    
    print(f"[SUCCESS] Network Model Trained (AUC: {metrics['roc_auc']:.4f})")
    
    # Save Model
    os.makedirs("models", exist_ok=True)
    joblib.dump(xgb_model, "models/network_model.joblib")
    
    # Explainability
    importance = xgb_model.feature_importances_
    feat_imp = dict(zip(features, [float(x) for x in importance]))
    joblib.dump(feat_imp, "models/network_importance.joblib")
    
    # Tracking
    report = {
        "timestamp": datetime.now().isoformat(),
        "dataset_size": len(df),
        "model_type": "xgboost",
        "metrics": metrics
    }
    os.makedirs("reports/experiments", exist_ok=True)
    with open(f"reports/experiments/network_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(report, f, indent=4)
        
    return xgb_model

if __name__ == "__main__":
    train_network_model()
