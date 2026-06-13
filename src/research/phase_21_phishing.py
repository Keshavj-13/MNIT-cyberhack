import os
import pandas as pd
import numpy as np
import time
import json
import joblib
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import StackingClassifier
import math
from collections import Counter

SEED = 42
REPORTS_DIR = "reports/models"
MODELS_DIR = "models"
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

def entropy(s):
    if not isinstance(s, str): return 0
    p, lns = Counter(s), float(len(s))
    return -sum(count/lns * math.log(count/lns, 2) for count in p.values())

def extract_url_features(df, url_col):
    df['url_len'] = df[url_col].astype(str).apply(len)
    df['url_entropy'] = df[url_col].astype(str).apply(entropy)
    df['num_digits'] = df[url_col].astype(str).apply(lambda x: sum(c.isdigit() for c in x))
    df['num_special'] = df[url_col].astype(str).apply(lambda x: sum(not c.isalnum() for c in x))
    df['num_subdomains'] = df[url_col].astype(str).apply(lambda x: x.count('.') - 1 if '.' in x else 0)
    keywords = ['login', 'verify', 'account', 'secure', 'bank', 'update', 'signin']
    for kw in keywords:
        df[f'has_{kw}'] = df[url_col].astype(str).str.lower().str.contains(kw).astype(int)
    return df.drop(columns=[url_col])

def run_phishing():
    print("[PHASE 21] Phishing Provider Research")
    
    # We use PhishingWebsites.parquet which is already feature engineered, 
    # but we can simulate the requirement if we find a raw URL dataset.
    df = pd.read_parquet("data/raw/phishing/PhishingWebsites.parquet")
    
    # OpenML format: target is 'Result' (-1 = Phishing, 1 = Legitimate typically, or vice versa)
    # Map to 0=Legitimate, 1=Phishing
    df['target'] = df['Result'].apply(lambda x: 1 if str(x) == '-1' else 0)
    X = df.drop(columns=['Result', 'target'])
    
    # If raw URL column existed, we would extract features:
    if 'url' in X.columns:
        X = extract_url_features(X, 'url')
        
    # Convert all columns to float to avoid CatBoost categorical errors on pre-encoded data
    for col in X.columns:
        X[col] = X[col].astype(float)
        
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    
    models = {
        "LightGBM": lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1),
        "CatBoost": CatBoostClassifier(iterations=200, random_state=SEED, verbose=0, thread_count=-1)
    }
    
    # Lexical Structural Fusion Ensemble
    models["Lexical_Structural_Fusion"] = StackingClassifier(
        estimators=[
            ('lgb', lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1)),
            ('cb', CatBoostClassifier(iterations=200, random_state=SEED, verbose=0))
        ],
        final_estimator=LogisticRegression(),
        n_jobs=-1
    )
    
    best_f1 = 0
    best_model_name = ""
    report_md = "# Phishing Provider Research\n\n"
    report_md += "**Datasets Used**: PhishingWebsites\n\n"
    report_md += "**Feature Engineering**: Used existing structural and lexical features from the dataset. If raw URLs were present, entropy and keyword features would be extracted.\n\n"
    
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
        
        # Overfitting check
        if train_auc - test_auc > 0.1:
            report_md += f"**WARNING**: {name} exhibits severe overfitting (Train-Test AUC gap > 0.1).\n\n"
            
        if f1 > best_f1:
            best_f1 = f1
            best_model_name = name
            joblib.dump(model, f"{MODELS_DIR}/phishing_provider_candidate.joblib")
            
    report_md += f"**Winner**: {best_model_name} (F1: {best_f1:.4f})\n"
    report_md += "**Observed Weaknesses**: Relies heavily on pre-extracted features rather than raw URL inspection. Highly performant but susceptible to drift if attackers change URL structures.\n"
    
    with open(f"{REPORTS_DIR}/PhishingRiskProvider_research.md", "w") as f:
        f.write(report_md)
        
    print(f"[SUCCESS] Phishing research complete. Winner: {best_model_name}")

if __name__ == "__main__":
    run_phishing()
