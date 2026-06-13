import pandas as pd
import numpy as np
import time
import os
import json
import joblib
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, precision_score, recall_score
import lightgbm as lgb
from sklearn.pipeline import Pipeline

SEED = 42
RESULTS_DIR = "reports/research/benchmarks"
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs("models", exist_ok=True)

def benchmark_sms():
    print("[INFO] Benchmarking SMS Scam Detection...")
    df = pd.read_csv("data/raw/se_datasets/sms_spam.csv")
    df['target'] = (df['label'] == 'spam').astype(int)
    
    X = df['message'].fillna('')
    y = df['target']
    
    models = {
        "TFIDF + LogisticRegression": Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, stop_words='english')),
            ('clf', LogisticRegression(random_state=SEED, max_iter=1000))
        ]),
        "TFIDF + RandomForest": Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, stop_words='english')),
            ('clf', RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=SEED))
        ]),
        "TFIDF + LightGBM": Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, stop_words='english')),
            ('clf', lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1))
        ])
    }
    
    results = []
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    
    best_model = None
    best_auc = 0
    
    for name, model in models.items():
        print(f"  [EXP] {name}")
        start = time.time()
        try:
            cv_results = cross_validate(
                model, X, y, cv=skf, 
                scoring=['roc_auc', 'average_precision', 'f1', 'precision', 'recall'],
                n_jobs=-1
            )
            
            model.fit(X, y)
            inf_start = time.time()
            model.predict_proba(X)
            inf_time = (time.time() - inf_start) / len(X)
            
            auc = float(np.mean(cv_results['test_roc_auc']))
            if auc > best_auc:
                best_auc = auc
                best_model = model
            
            results.append({
                "model": name,
                "dataset": "SMS Spam Collection",
                "roc_auc": auc,
                "pr_auc": float(np.mean(cv_results['test_average_precision'])),
                "f1": float(np.mean(cv_results['test_f1'])),
                "precision": float(np.mean(cv_results['test_precision'])),
                "recall": float(np.mean(cv_results['test_recall'])),
                "train_time": float(time.time() - start),
                "inf_time_per_sample": float(inf_time)
            })
        except Exception as e:
            print(f"    [ERR] {name}: {e}")
            
    if best_model:
        joblib.dump(best_model, "models/sms_scam_model.joblib")
        print(f"[SUCCESS] Saved best SMS model to models/sms_scam_model.joblib")
            
    return results

def benchmark_phishing():
    print("[INFO] Benchmarking Phishing URL Detection...")
    df = pd.read_csv("data/raw/se_datasets/phishing.csv")
    y = (df['Result'] == 1).astype(int)
    X = df.drop(columns=['Result'])
    
    models = {
        "LogisticRegression": LogisticRegression(random_state=SEED, max_iter=1000),
        "RandomForest": RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=SEED),
        "LightGBM": lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1)
    }
    
    results = []
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    
    best_model = None
    best_auc = 0
    
    for name, model in models.items():
        print(f"  [EXP] {name}")
        start = time.time()
        try:
            cv_results = cross_validate(
                model, X, y, cv=skf, 
                scoring=['roc_auc', 'average_precision', 'f1', 'precision', 'recall'],
                n_jobs=-1
            )
            
            model.fit(X, y)
            inf_start = time.time()
            model.predict_proba(X)
            inf_time = (time.time() - inf_start) / len(X)
            
            auc = float(np.mean(cv_results['test_roc_auc']))
            if auc > best_auc:
                best_auc = auc
                best_model = model
            
            results.append({
                "model": name,
                "dataset": "Phishing Websites",
                "roc_auc": auc,
                "pr_auc": float(np.mean(cv_results['test_average_precision'])),
                "f1": float(np.mean(cv_results['test_f1'])),
                "precision": float(np.mean(cv_results['test_precision'])),
                "recall": float(np.mean(cv_results['test_recall'])),
                "train_time": float(time.time() - start),
                "inf_time_per_sample": float(inf_time)
            })
        except Exception as e:
            print(f"    [ERR] {name}: {e}")
            
    if best_model:
        joblib.dump(best_model, "models/phishing_url_model.joblib")
        print(f"[SUCCESS] Saved best Phishing model to models/phishing_url_model.joblib")
            
    return results

if __name__ == "__main__":
    res_sms = benchmark_sms()
    res_phish = benchmark_phishing()
    
    df_all = pd.DataFrame(res_sms + res_phish)
    df_all.to_csv(f"{RESULTS_DIR}/social_engineering_leaderboard.csv", index=False)
    
    with open(f"{RESULTS_DIR}/social_engineering_leaderboard.md", "w") as f:
        f.write("# Social Engineering Models Leaderboard\n\n")
        f.write(df_all.sort_values(by="roc_auc", ascending=False).to_markdown(index=False))
        
    print(f"[SUCCESS] SE Benchmarking complete. Leaderboard saved to {RESULTS_DIR}/social_engineering_leaderboard.csv")

