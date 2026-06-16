import os
import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
import xgboost as xgb

# Ensure artifact directory exists
ARTIFACT_DIR = "models/artifacts"
os.makedirs(ARTIFACT_DIR, exist_ok=True)
os.makedirs("reports/models", exist_ok=True)

SUMMARY = {}

def train_behavioral_model():
    print("[INFO] Training Behavioral Risk Model (CMU Keystroke)...")
    df = pd.read_csv("datasets/raw/cmu_keystroke/DSL-StrongPasswordData.csv")
    
    # We'll treat this as a binary classification: is it subject 's002' or not?
    # This simulates "Is this the authorized user?"
    df['is_authorized'] = (df['subject'] == 's002').astype(int)
    
    features = [c for c in df.columns if c not in ['subject', 'sessionIndex', 'rep', 'is_authorized']]
    X = df[features]
    y = df['is_authorized']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)
    
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_pred_proba))
    }
    
    joblib.dump(model, os.path.join(ARTIFACT_DIR, "behavioral_risk.joblib"))
    SUMMARY["behavioral_risk"] = metrics
    print(f"[SUCCESS] Behavioral Risk Model trained. AUC: {metrics['roc_auc']:.4f}")

def train_transaction_model():
    print("[INFO] Training Transaction Risk Model (Feedzai BAF)...")
    # Using a subset for speed in this environment
    df = pd.read_csv("datasets/raw/feedzai_baf/Base.csv", nrows=100000)
    
    target = 'fraud_bool'
    # Identify categorical columns
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    # Simple encoding for demo
    for col in cat_cols:
        df[col] = pd.factorize(df[col])[0]
        
    X = df.drop(columns=[target])
    y = df[target]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    model = xgb.XGBClassifier(n_estimators=100, random_state=42, use_label_encoder=False, eval_metric='logloss')
    model.fit(X_train, y_train)
    
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)
    
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_pred_proba))
    }
    
    joblib.dump(model, os.path.join(ARTIFACT_DIR, "transaction_risk.joblib"))
    # Save feature names for inference alignment
    joblib.dump(X.columns.tolist(), os.path.join(ARTIFACT_DIR, "transaction_features.joblib"))
    
    SUMMARY["transaction_risk"] = metrics
    print(f"[SUCCESS] Transaction Risk Model trained. AUC: {metrics['roc_auc']:.4f}")

def train_intent_model():
    print("[INFO] Training Intent Risk Model (SMS Spam)...")
    # SMSSpamCollection is tab-separated, no header
    df = pd.read_csv("datasets/raw/sms_spam_collection/SMSSpamCollection", sep='\t', names=['label', 'text'])
    df['target'] = (df['label'] == 'spam').astype(int)
    
    X_train, X_test, y_train, y_test = train_test_split(df['text'], df['target'], test_size=0.2, random_state=42, stratify=df['target'])
    
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=5000)),
        ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    
    pipeline.fit(X_train, y_train)
    
    y_pred_proba = pipeline.predict_proba(X_test)[:, 1]
    y_pred = pipeline.predict(X_test)
    
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_pred_proba))
    }
    
    joblib.dump(pipeline, os.path.join(ARTIFACT_DIR, "intent_risk.joblib"))
    SUMMARY["intent_risk"] = metrics
    print(f"[SUCCESS] Intent Risk Model trained. AUC: {metrics['roc_auc']:.4f}")

def train_environment_model():
    print("[INFO] Training Environment Risk Model (Simargl 2021)...")
    # This dataset is huge, using a small subset for feasibility
    df = pd.read_csv("datasets/raw/simargl2021/dataset-part1.csv", nrows=100000)
    
    # target is 'LABEL'
    df['is_anomaly'] = (df['LABEL'] != 'Normal flow').astype(int)
    
    # Drop non-numeric or non-useful columns
    drop_cols = ['LABEL', 'is_anomaly', 'FLOW_ID', 'IPV4_SRC_ADDR', 'IPV4_DST_ADDR', 'PROTOCOL_MAP', 'L7_PROTO_NAME']
    X = df.drop(columns=[c for c in drop_cols if c in df.columns])
    
    # Convert remaining objects to numeric if any
    for col in X.select_dtypes(include=['object']).columns:
        X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)
        
    y = df['is_anomaly']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)
    
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_pred_proba))
    }
    
    joblib.dump(model, os.path.join(ARTIFACT_DIR, "environment_risk.joblib"))
    joblib.dump(X.columns.tolist(), os.path.join(ARTIFACT_DIR, "environment_features.joblib"))
    
    SUMMARY["environment_risk"] = metrics
    print(f"[SUCCESS] Environment Risk Model trained. AUC: {metrics['roc_auc']:.4f}")

def main():
    train_behavioral_model()
    train_transaction_model()
    train_intent_model()
    train_environment_model()
    
    with open("reports/models/training_summary.json", "w") as f:
        json.dump(SUMMARY, f, indent=4)
    print("\n[FINISH] All models trained and artifacts saved.")

if __name__ == "__main__":
    main()
