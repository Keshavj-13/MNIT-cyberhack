import pandas as pd
import numpy as np
import time
import json
import os
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    roc_auc_score, average_precision_score, f1_score, 
    precision_score, recall_score, confusion_matrix
)
from sklearn.linear_model import LogisticRegression, RidgeClassifier, SGDClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier, LocalOutlierFactor
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier, ExtraTreesClassifier, 
    AdaBoostClassifier, GradientBoostingClassifier, 
    HistGradientBoostingClassifier, IsolationForest
)
from sklearn.svm import OneClassSVM
from imblearn.ensemble import BalancedRandomForestClassifier, EasyEnsembleClassifier
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer

# Config
SEED = 42
SAMPLE_SIZE = 10000
RESULTS_DIR = "reports/research/benchmarks"
os.makedirs(RESULTS_DIR, exist_ok=True)

def run_traditional_benchmark():
    tasks = [
        ("transaction", "data/processed/transaction_data.parquet", "is_fraud"),
        ("network", "data/processed/network_data.parquet", "Label_Encoded")
    ]
    
    for task_name, path, target in tasks:
        print(f"[PHASE C] Traditional Benchmark for {task_name}...")
        df_full = pd.read_parquet(path)
        if task_name == "network" and "Label_Encoded" in target:
             df_full[target] = (df_full[target] != 0).astype(int)
             
        df = df_full.sample(min(SAMPLE_SIZE, len(df_full)), random_state=SEED)
        
        X = df.drop(columns=[target, 'timestamp', 'customer_id', 'device_id', 'ip_address', 'Label'], errors='ignore')
        y = df[target]
        
        # Preprocessing (Standard Baseline)
        cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
        if cat_cols:
            enc = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
            X[cat_cols] = enc.fit_transform(X[cat_cols].astype(str))
            
        imp = SimpleImputer(strategy='mean')
        scaler = StandardScaler()
        X_proc = pd.DataFrame(scaler.fit_transform(imp.fit_transform(X)), columns=X.columns)
        
        models = {
            "LogisticRegression": LogisticRegression(max_iter=1000, random_state=SEED),
            "Ridge": RidgeClassifier(random_state=SEED),
            "SGD": SGDClassifier(loss='log_loss', random_state=SEED),
            "GaussianNB": GaussianNB(),
            "KNN": KNeighborsClassifier(),
            "DecisionTree": DecisionTreeClassifier(random_state=SEED),
            "RandomForest": RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=SEED),
            "ExtraTrees": ExtraTreesClassifier(n_estimators=100, n_jobs=-1, random_state=SEED),
            "AdaBoost": AdaBoostClassifier(random_state=SEED),
            "GradientBoosting": GradientBoostingClassifier(random_state=SEED),
            "HistGradientBoosting": HistGradientBoostingClassifier(random_state=SEED),
            "XGBoost": xgb.XGBClassifier(random_state=SEED, n_jobs=-1),
            "LightGBM": lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1),
            "CatBoost": CatBoostClassifier(random_state=SEED, verbose=0, thread_count=-1),
            "BalancedRF": BalancedRandomForestClassifier(n_estimators=100, random_state=SEED, n_jobs=-1),
            "EasyEnsemble": EasyEnsembleClassifier(n_estimators=10, random_state=SEED, n_jobs=-1),
        }
        
        # Anomaly Detection models (require different handling for supervised benchmark)
        # We wrap them to return scores compatible with AUC
        
        results = []
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
        
        for name, model in models.items():
            print(f"  [EXP] Model: {name}")
            start_time = time.time()
            try:
                cv_results = cross_validate(
                    model, X_proc, y, 
                    cv=skf, 
                    scoring=['roc_auc', 'average_precision', 'f1', 'precision', 'recall'],
                    n_jobs=-1
                )
                
                # Inference time test
                model.fit(X_proc, y)
                inf_start = time.time()
                _ = model.predict_proba(X_proc) if hasattr(model, 'predict_proba') else model.predict(X_proc)
                inf_time = (time.time() - inf_start) / len(X_proc)
                
                results.append({
                    "model": name,
                    "roc_auc": float(np.mean(cv_results['test_roc_auc'])),
                    "pr_auc": float(np.mean(cv_results['test_average_precision'])),
                    "f1": float(np.mean(cv_results['test_f1'])),
                    "precision": float(np.mean(cv_results['test_precision'])),
                    "recall": float(np.mean(cv_results['test_recall'])),
                    "train_time": float(time.time() - start_time),
                    "inf_time_per_sample": float(inf_time)
                })
            except Exception as e:
                print(f"    [ERR] {name}: {e}")

        # Anomaly models
        anomaly_models = {
            "IsolationForest": IsolationForest(random_state=SEED, n_jobs=-1),
            "OneClassSVM": OneClassSVM()
        }
        
        for name, model in anomaly_models.items():
            print(f"  [EXP] Anomaly Model: {name}")
            start_time = time.time()
            try:
                # fit on benign only for anomaly? or just fit on sample?
                # User wants a comparison on same metrics
                model.fit(X_proc)
                # IF returns -1 for anomaly, 1 for normal. scores are path length.
                if name == "IsolationForest":
                    scores = -model.decision_function(X_proc) # higher is more anomalous
                else:
                    scores = -model.decision_function(X_proc)
                
                auc = roc_auc_score(y, scores)
                pr_auc = average_precision_score(y, scores)
                
                results.append({
                    "model": name,
                    "roc_auc": float(auc),
                    "pr_auc": float(pr_auc),
                    "f1": 0.0, # requires thresholding
                    "precision": 0.0,
                    "recall": 0.0,
                    "train_time": float(time.time() - start_time),
                    "inf_time_per_sample": 0.0
                })
            except Exception as e:
                print(f"    [ERR] {name}: {e}")

        res_df = pd.DataFrame(results)
        res_df.to_csv(f"{RESULTS_DIR}/{task_name}_traditional_leaderboard.csv", index=False)
        with open(f"{RESULTS_DIR}/{task_name}_traditional_leaderboard.md", "w") as f:
            f.write(f"# Traditional Model Leaderboard: {task_name}\n\n")
            f.write(res_df.sort_values("roc_auc", ascending=False).to_markdown(index=False))

    print(f"[SUCCESS] Phase C completed. Results in {RESULTS_DIR}")

if __name__ == "__main__":
    run_traditional_benchmark()
