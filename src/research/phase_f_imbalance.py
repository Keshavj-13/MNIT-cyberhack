import pandas as pd
import numpy as np
import time
import json
import os
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, average_precision_score, recall_score
from imblearn.over_sampling import SMOTE, ADASYN, BorderlineSMOTE, RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler
from imblearn.combine import SMOTETomek
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer

# Config
SEED = 42
SAMPLE_SIZE = 10000
RESULTS_DIR = "reports/research/benchmarks"
os.makedirs(RESULTS_DIR, exist_ok=True)

def run_imbalance_research():
    tasks = [
        ("transaction", "data/processed/transaction_data.parquet", "is_fraud"),
        ("network", "data/processed/network_data.parquet", "Label_Encoded")
    ]
    
    for task_name, path, target in tasks:
        print(f"[PHASE F] Class Imbalance Research for {task_name}...")
        df_full = pd.read_parquet(path)
        if task_name == "network" and "Label_Encoded" in target:
             df_full[target] = (df_full[target] != 0).astype(int)
             
        df = df_full.sample(min(SAMPLE_SIZE, len(df_full)), random_state=SEED)
        X = df.drop(columns=[target, 'timestamp', 'customer_id', 'device_id', 'ip_address', 'Label'], errors='ignore')
        y = df[target]
        
        # Preprocessing
        cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
        if cat_cols:
            enc = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
            X[cat_cols] = enc.fit_transform(X[cat_cols].astype(str))
        X_proc = pd.DataFrame(StandardScaler().fit_transform(SimpleImputer().fit_transform(X)), columns=X.columns)
        
        samplers = {
            "None": None,
            "ClassWeights": "weights",
            "ROS": RandomOverSampler(random_state=SEED),
            "RUS": RandomUnderSampler(random_state=SEED),
            "SMOTE": SMOTE(random_state=SEED),
            "BorderlineSMOTE": BorderlineSMOTE(random_state=SEED),
            "ADASYN": ADASYN(random_state=SEED),
            "SMOTETomek": SMOTETomek(random_state=SEED)
        }
        
        results = []
        skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED)
        
        for name, sampler in samplers.items():
            print(f"  [EXP] {name}")
            start = time.time()
            try:
                aucs, pr_aucs, recalls = [], [], []
                
                for train_idx, val_idx in skf.split(X_proc, y):
                    X_tr, y_tr = X_proc.iloc[train_idx], y.iloc[train_idx]
                    X_va, y_va = X_proc.iloc[val_idx], y.iloc[val_idx]
                    
                    if name == "ClassWeights":
                        model = RandomForestClassifier(n_estimators=50, class_weight='balanced', n_jobs=-1, random_state=SEED)
                        model.fit(X_tr, y_tr)
                    elif sampler is not None:
                        X_res, y_res = sampler.fit_resample(X_tr, y_tr)
                        model = RandomForestClassifier(n_estimators=50, n_jobs=-1, random_state=SEED)
                        model.fit(X_res, y_res)
                    else:
                        model = RandomForestClassifier(n_estimators=50, n_jobs=-1, random_state=SEED)
                        model.fit(X_tr, y_tr)
                    
                    probs = model.predict_proba(X_va)[:, 1]
                    preds = model.predict(X_va)
                    aucs.append(roc_auc_score(y_va, probs))
                    pr_aucs.append(average_precision_score(y_va, probs))
                    recalls.append(recall_score(y_va, preds))
                
                results.append({
                    "method": name,
                    "roc_auc": float(np.mean(aucs)),
                    "pr_auc": float(np.mean(pr_aucs)),
                    "recall": float(np.mean(recalls)),
                    "duration": float(time.time() - start)
                })
            except Exception as e:
                print(f"    [ERR] {name}: {e}")

        res_df = pd.DataFrame(results)
        res_df.to_csv(f"{RESULTS_DIR}/{task_name}_imbalance_leaderboard.csv", index=False)
        with open(f"{RESULTS_DIR}/{task_name}_imbalance_leaderboard.md", "w") as f:
            f.write(f"# Class Imbalance Leaderboard: {task_name}\n\n")
            f.write(res_df.sort_values("roc_auc", ascending=False).to_markdown(index=False))

    print(f"[SUCCESS] Phase F completed.")

if __name__ == "__main__":
    run_imbalance_research()
