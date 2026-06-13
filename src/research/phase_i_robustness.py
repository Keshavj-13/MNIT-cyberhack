import pandas as pd
import numpy as np
import time
import json
import os
import lightgbm as lgb
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split

# Config
SEED = 42
SAMPLE_SIZE = 5000
RESULTS_DIR = "reports/research/benchmarks"
os.makedirs(RESULTS_DIR, exist_ok=True)

def run_robustness_research():
    tasks = [
        ("transaction", "data/processed/transaction_data.parquet", "is_fraud"),
        ("network", "data/processed/network_data.parquet", "Label_Encoded")
    ]
    
    for task_name, path, target in tasks:
        print(f"[PHASE I] Robustness Research for {task_name}...")
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
        
        X_train, X_test, y_train, y_test = train_test_split(X_proc, y, test_size=0.2, random_state=SEED)
        
        model = lgb.LGBMClassifier(n_estimators=100, n_jobs=-1, verbose=-1, random_state=SEED)
        model.fit(X_train, y_train)
        
        baseline_auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
        
        robustness_results = {"baseline_auc": float(baseline_auc)}
        
        # 1. Missing Features (Dropout)
        print("  [EXP] Missing Features")
        for drop_rate in [0.1, 0.3, 0.5]:
            X_corrupted = X_test.copy()
            mask = np.random.rand(*X_corrupted.shape) < drop_rate
            X_corrupted[mask] = 0 # Assume zero-filling or imputer baseline
            auc = roc_auc_score(y_test, model.predict_proba(X_corrupted)[:, 1])
            robustness_results[f"missing_{int(drop_rate*100)}pct"] = float(auc)
            
        # 2. Noisy Features (Gaussian)
        print("  [EXP] Noisy Features")
        for noise_level in [0.1, 0.5, 1.0]:
            X_corrupted = X_test + np.random.normal(0, noise_level, X_test.shape)
            auc = roc_auc_score(y_test, model.predict_proba(X_corrupted)[:, 1])
            robustness_results[f"noise_{noise_level}"] = float(auc)
            
        # 3. Adversarial Corruption (Simple Flip)
        print("  [EXP] Adversarial Flip")
        # Flip top important feature to its opposite extreme
        top_feat = X_proc.columns[np.argmax(model.feature_importances_)]
        X_corrupted = X_test.copy()
        X_corrupted[top_feat] = -X_corrupted[top_feat] # Simplistic adversarial attack
        auc = roc_auc_score(y_test, model.predict_proba(X_corrupted)[:, 1])
        robustness_results["adversarial_flip_top_feat"] = float(auc)

        output_path = os.path.join(RESULTS_DIR, f"{task_name}_robustness.json")
        with open(output_path, "w") as f:
            json.dump(robustness_results, f, indent=4)

    print(f"[SUCCESS] Phase I completed.")

if __name__ == "__main__":
    run_robustness_research()
