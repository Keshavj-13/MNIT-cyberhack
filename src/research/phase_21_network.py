import os
import pandas as pd
import numpy as np
import time
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
from sklearn.ensemble import ExtraTreesClassifier, VotingClassifier
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier
from sklearn.preprocessing import RobustScaler

SEED = 42
REPORTS_DIR = "reports/models"
MODELS_DIR = "models"
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

def engineer_features(df):
    # Flow statistics (already present mostly, but we can scale/normalize)
    # We drop IP/Ports to prevent extreme identity leakage
    cols_to_drop = ['IPV4_SRC_ADDR', 'IPV4_DST_ADDR', 'L4_SRC_PORT', 'L4_DST_PORT', 'L7_PROTO_NAME', 'PROTOCOL_MAP', 'DST_TO_SRC_SECOND_BYTES', 'SRC_TO_DST_SECOND_BYTES']
    X = df.drop(columns=cols_to_drop, errors='ignore').copy()
    
    num_cols = X.select_dtypes(include=[np.number]).columns
    scaler = RobustScaler()
    X[num_cols] = scaler.fit_transform(X[num_cols].fillna(0))
    return X

def run_network():
    print("[PHASE 21] Network Risk Provider Research")
    
    # Load and sample from large SIMARGL dataset
    df_raw = pd.read_parquet("data/raw/INTRUSION/shivamjaisingh_SIMARGL2021-Intrusion-Detection-Systems/data.parquet")
    
    # Stratified sampling
    normal_df = df_raw[df_raw['LABEL'] == 'Normal flow'].sample(30000, random_state=SEED)
    attack_df = df_raw[df_raw['LABEL'] != 'Normal flow'].sample(min(20000, len(df_raw[df_raw['LABEL'] != 'Normal flow'])), random_state=SEED)
    df = pd.concat([normal_df, attack_df])
    
    df['target'] = (df['LABEL'] != 'Normal flow').astype(int)
    y = df['target']
    
    X = engineer_features(df.drop(columns=['target', 'LABEL']))
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    
    models = {
        "LightGBM": lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1),
        "XGBoost": xgb.XGBClassifier(random_state=SEED, n_jobs=-1),
        "CatBoost": CatBoostClassifier(iterations=200, random_state=SEED, verbose=0, thread_count=-1),
        "ExtraTrees": ExtraTreesClassifier(n_estimators=100, random_state=SEED, n_jobs=-1)
    }
    
    # Hybrid Intrusion Ensemble
    models["Hybrid_Intrusion_Ensemble"] = VotingClassifier(
        estimators=[
            ('lgb', lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1)),
            ('et', ExtraTreesClassifier(n_estimators=100, random_state=SEED, n_jobs=-1))
        ],
        voting='soft', n_jobs=-1
    )
    
    best_f1 = 0
    best_model_name = ""
    report_md = "# Network Risk Provider Research\n\n"
    report_md += "**Datasets Used**: SIMARGL2021\n\n"
    report_md += "**Feature Engineering**: Removed IPs and Ports to prevent identity leakage. Applied RobustScaler for flow statistics normalization.\n\n"
    
    for name, model in models.items():
        start = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - start
        
        train_probs = model.predict_proba(X_train)[:, 1]
        test_probs = model.predict_proba(X_test)[:, 1]
        test_preds = model.predict(X_test)
        
        train_auc = roc_auc_score(y_train, train_probs)
        test_auc = roc_auc_score(y_test, test_probs)
        f1 = f1_score(y_test, test_preds)
        prec = precision_score(y_test, test_preds)
        rec = recall_score(y_test, test_preds)
        
        report_md += f"### Model: {name}\n"
        report_md += f"- **Train AUC**: {train_auc:.4f}\n"
        report_md += f"- **Test AUC**: {test_auc:.4f}\n"
        report_md += f"- **Test F1**: {f1:.4f} (Prec: {prec:.4f}, Rec: {rec:.4f})\n"
        report_md += f"- **Train Time**: {train_time:.2f}s\n\n"
        
        if train_auc - test_auc > 0.1:
            report_md += f"**WARNING**: {name} exhibits severe overfitting (Train-Test AUC gap > 0.1).\n\n"
            
        if f1 > best_f1:
            best_f1 = f1
            best_model_name = name
            joblib.dump(model, f"{MODELS_DIR}/network_provider_candidate.joblib")
            
    report_md += f"**Winner**: {best_model_name} (F1: {best_f1:.4f})\n"
    report_md += "**Observed Weaknesses**: High dimensionality. The removal of ports prevents detection of known bad-port scans, but ensures generalization over memorization.\n"
    
    with open(f"{REPORTS_DIR}/NetworkRiskProvider_research.md", "w") as f:
        f.write(report_md)
        
    print(f"[SUCCESS] Network Risk research complete. Winner: {best_model_name}")

if __name__ == "__main__":
    run_network()
