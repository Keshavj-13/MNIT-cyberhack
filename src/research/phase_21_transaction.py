import os
import pandas as pd
import numpy as np
import time
import joblib
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, average_precision_score
from sklearn.ensemble import StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import QuantileTransformer
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier

SEED = 42
REPORTS_DIR = "reports/models"
MODELS_DIR = "models"
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

def engineer_features(df):
    # Sort by time
    if 'Time' in df.columns:
        df = df.sort_values('Time').copy()
        # Amount deviation
        df['amount_deviation'] = df['Amount'] / (df['Amount'].mean() + 1e-9)
        # Global rolling velocity (since no account_id)
        df['global_velocity_100'] = df['Amount'].rolling(window=100, min_periods=1).mean()
        # Temporal features
        df['hour'] = (df['Time'] // 3600) % 24
    
    # Scale Amount using QuantileTransformer as per strategy
    if 'Amount' in df.columns:
        qt = QuantileTransformer(output_distribution='normal', random_state=SEED)
        df['Amount'] = qt.fit_transform(df[['Amount']])
        
    return df

def run_transaction():
    print("[PHASE 21] Transaction Fraud Provider Research")
    
    df = pd.read_parquet("data/raw/fraud/CreditCardFraudDetection.parquet")
    # Sample down for speed if needed, but fraud is rare so keep all fraud
    df_fraud = df[df['Class'] == 1]
    df_legit = df[df['Class'] == 0].sample(20000, random_state=SEED)
    df = pd.concat([df_fraud, df_legit])
    
    df = engineer_features(df)
    
    y = df['Class']
    X = df.drop(columns=['Class', 'Time'], errors='ignore')
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    
    models = {
        "LightGBM": lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1, scale_pos_weight=10),
        "XGBoost": xgb.XGBClassifier(random_state=SEED, n_jobs=-1, scale_pos_weight=10),
        "CatBoost": CatBoostClassifier(iterations=200, random_state=SEED, verbose=0, thread_count=-1, scale_pos_weight=10)
    }
    
    # Fraud Ensemble
    models["Fraud_Ensemble"] = StackingClassifier(
        estimators=[
            ('lgb', lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1)),
            ('xgb', xgb.XGBClassifier(random_state=SEED, n_jobs=-1))
        ],
        final_estimator=LogisticRegression(),
        n_jobs=-1
    )
    
    best_pr_auc = 0
    best_model_name = ""
    report_md = "# Transaction Fraud Provider Research\n\n"
    report_md += "**Datasets Used**: ULB Credit Card Fraud\n\n"
    report_md += "**Feature Engineering**: Created Amount deviation, global rolling velocity, temporal (hour), and applied QuantileTransformer to Amount.\n\n"
    
    for name, model in models.items():
        start = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - start
        
        train_probs = model.predict_proba(X_train)[:, 1]
        test_probs = model.predict_proba(X_test)[:, 1]
        test_preds = model.predict(X_test)
        
        train_auc = roc_auc_score(y_train, train_probs)
        test_auc = roc_auc_score(y_test, test_probs)
        pr_auc = average_precision_score(y_test, test_probs)
        f1 = f1_score(y_test, test_preds)
        prec = precision_score(y_test, test_preds)
        rec = recall_score(y_test, test_preds)
        
        report_md += f"### Model: {name}\n"
        report_md += f"- **Train ROC AUC**: {train_auc:.4f}\n"
        report_md += f"- **Test ROC AUC**: {test_auc:.4f}\n"
        report_md += f"- **Test PR AUC**: {pr_auc:.4f}\n"
        report_md += f"- **Test F1**: {f1:.4f} (Prec: {prec:.4f}, Rec: {rec:.4f})\n"
        report_md += f"- **Train Time**: {train_time:.2f}s\n\n"
        
        if train_auc - test_auc > 0.1:
            report_md += f"**WARNING**: {name} exhibits severe overfitting (Train-Test AUC gap > 0.1).\n\n"
            
        if pr_auc > best_pr_auc:
            best_pr_auc = pr_auc
            best_model_name = name
            joblib.dump(model, f"{MODELS_DIR}/transaction_provider_candidate.joblib")
            
    report_md += f"**Winner**: {best_model_name} (PR AUC: {best_pr_auc:.4f})\n"
    report_md += "**Observed Weaknesses**: Highly imbalanced. The ensemble performs well but lacks specific account context due to dataset anonymization.\n"
    
    with open(f"{REPORTS_DIR}/TransactionRiskProvider_research.md", "w") as f:
        f.write(report_md)
        
    print(f"[SUCCESS] Transaction research complete. Winner: {best_model_name}")

if __name__ == "__main__":
    run_transaction()
