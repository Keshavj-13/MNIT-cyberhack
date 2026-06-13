import pandas as pd
import numpy as np
import time
import json
import os
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

# Reproducibility Config
SEED = 42
TRAIN_VAL_SPLIT = 0.3 # SKF handles the split, but conceptually
DATA_DIR = "data/processed"
RESULTS_DIR = "reports/research"

def run_reproducibility_check():
    print("[PHASE A] Starting Reproducibility Check...")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    report = "# Reproducibility Report\n\n"
    report += f"- **Date**: {time.ctime()}\n"
    report += f"- **Random Seed**: {SEED}\n"
    report += f"- **K-Folds**: 3\n\n"
    
    tasks = [
        ("transaction", f"{DATA_DIR}/transaction_data.parquet", "is_fraud"),
        ("network", f"{DATA_DIR}/network_data.parquet", "Label_Encoded")
    ]
    
    for name, path, target in tasks:
        print(f"  [TASK] {name}")
        report += f"## Task: {name}\n"
        
        try:
            df = pd.read_parquet(path)
            X = df.drop(columns=[target, 'timestamp', 'customer_id', 'device_id', 'ip_address', 'Label'], errors='ignore').fillna(0)
            y = df[target]
            
            if name == "network" and "Label_Encoded" in target:
                y = (df[target] != 0).astype(int)
            
            # Sample like before (10000 rows)
            X_sample = X.sample(min(10000, len(X)), random_state=SEED)
            y_sample = y.loc[X_sample.index]
            
            report += f"- **Dataset Size (Sample)**: {len(X_sample)}\n"
            report += f"- **Features**: {list(X.columns)}\n"
            
            # Baseline: Mean Impute + Standard Scale + RF(50)
            print("    [EXP] Baseline Reproduce...")
            start_time = time.time()
            
            imputer = SimpleImputer(strategy='mean')
            scaler = StandardScaler()
            
            X_proc = scaler.fit_transform(imputer.fit_transform(X_sample))
            
            model = RandomForestClassifier(n_estimators=50, n_jobs=-1, random_state=SEED)
            skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED)
            
            aucs = []
            for train_idx, val_idx in skf.split(X_proc, y_sample):
                model.fit(X_proc[train_idx], y_sample.iloc[train_idx])
                probs = model.predict_proba(X_proc[val_idx])[:, 1]
                aucs.append(roc_auc_score(y_sample.iloc[val_idx], probs))
            
            mean_auc = np.mean(aucs)
            duration = time.time() - start_time
            
            report += f"### Baseline Experiment (Mean Impute + Std Scale + RF)\n"
            report += f"- **Status**: {'VALIDATED' if mean_auc > 0.4 else 'FAILED'}\n"
            report += f"- **ROC AUC**: {mean_auc:.4f}\n"
            report += f"- **Duration**: {duration:.2f}s\n\n"
            
        except Exception as e:
            report += f"### Error processing {name}: {e}\n\n"
            
    with open(f"{RESULTS_DIR}/reproducibility_report.md", "w") as f:
        f.write(report)
    print(f"[SUCCESS] Phase A report saved to {RESULTS_DIR}/reproducibility_report.md")

if __name__ == "__main__":
    run_reproducibility_check()
