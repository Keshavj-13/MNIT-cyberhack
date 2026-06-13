import pandas as pd
import numpy as np
import time
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from sklearn.ensemble import VotingClassifier, StackingClassifier, RandomForestClassifier
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer

# Config
SEED = 42
SAMPLE_SIZE = 10000
RESULTS_DIR = "reports/research/benchmarks"
os.makedirs(RESULTS_DIR, exist_ok=True)

def run_ensemble_research():
    tasks = [
        ("transaction", "data/processed/transaction_data.parquet", "is_fraud"),
        ("network", "data/processed/network_data.parquet", "Label_Encoded")
    ]
    
    for task_name, path, target in tasks:
        print(f"[PHASE D] Ensemble Research for {task_name}...")
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
            
        imp = SimpleImputer(strategy='mean')
        scaler = StandardScaler()
        X_proc = pd.DataFrame(scaler.fit_transform(imp.fit_transform(X)), columns=X.columns)
        
        X_train, X_test, y_train, y_test = train_test_split(X_proc, y, test_size=0.3, random_state=SEED, stratify=y)
        
        # Base Models
        lgbm = lgb.LGBMClassifier(n_jobs=-1, verbose=-1, random_state=SEED)
        xgb_m = xgb.XGBClassifier(n_jobs=-1, random_state=SEED)
        rf = RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=SEED)
        cat = CatBoostClassifier(verbose=0, thread_count=-1, random_state=SEED)
        
        estimators = [('lgbm', lgbm), ('xgb', xgb_m), ('rf', rf), ('cat', cat)]
        
        results = []
        
        # 1. Voting (Soft)
        print("  [EXP] Voting Classifier")
        start = time.time()
        voting = VotingClassifier(estimators=estimators, voting='soft', n_jobs=-1)
        voting.fit(X_train, y_train)
        probs = voting.predict_proba(X_test)[:, 1]
        results.append({"ensemble": "Voting (Soft)", "roc_auc": float(roc_auc_score(y_test, probs)), "duration": float(time.time()-start)})
        
        # 2. Stacking
        print("  [EXP] Stacking Classifier")
        start = time.time()
        stacking = StackingClassifier(estimators=estimators, final_estimator=LogisticRegression(), n_jobs=-1)
        stacking.fit(X_train, y_train)
        probs = stacking.predict_proba(X_test)[:, 1]
        results.append({"ensemble": "Stacking", "roc_auc": float(roc_auc_score(y_test, probs)), "duration": float(time.time()-start)})
        
        # 3. Blending (Manual)
        print("  [EXP] Blending")
        start = time.time()
        # Split train into train_base and val_meta
        X_base, X_meta, y_base, y_meta = train_test_split(X_train, y_train, test_size=0.3, random_state=SEED)
        meta_features = []
        for name, model in estimators:
            model.fit(X_base, y_base)
            meta_features.append(model.predict_proba(X_meta)[:, 1])
        
        X_meta_input = np.column_stack(meta_features)
        meta_model = LogisticRegression().fit(X_meta_input, y_meta)
        
        # Evaluate on test
        test_meta_features = []
        for name, model in estimators:
            test_meta_features.append(model.predict_proba(X_test)[:, 1])
        X_test_meta = np.column_stack(test_meta_features)
        probs = meta_model.predict_proba(X_test_meta)[:, 1]
        results.append({"ensemble": "Blending", "roc_auc": float(roc_auc_score(y_test, probs)), "duration": float(time.time()-start)})
        
        # 4. Weighted Average (Simple)
        print("  [EXP] Weighted Average")
        # Weights proportional to individual performance (conceptually)
        # For now equal weights
        probs = np.mean(X_test_meta, axis=1)
        results.append({"ensemble": "Weighted Average (Equal)", "roc_auc": float(roc_auc_score(y_test, probs)), "duration": 0.0})
        
        # 5. Confidence Weighted
        print("  [EXP] Confidence Weighted")
        # Weighted by certainty |p-0.5|
        certainties = np.abs(X_test_meta - 0.5)
        # Normalize weights per sample
        weights = certainties / (np.sum(certainties, axis=1, keepdims=True) + 1e-9)
        conf_weighted_probs = np.sum(X_test_meta * weights, axis=1)
        results.append({"ensemble": "Confidence Weighted", "roc_auc": float(roc_auc_score(y_test, conf_weighted_probs)), "duration": 0.0})

        res_df = pd.DataFrame(results)
        res_df.to_csv(f"{RESULTS_DIR}/{task_name}_ensemble_leaderboard.csv", index=False)
        with open(f"{RESULTS_DIR}/{task_name}_ensemble_leaderboard.md", "w") as f:
            f.write(f"# Ensemble Leaderboard: {task_name}\n\n")
            f.write(res_df.sort_values("roc_auc", ascending=False).to_markdown(index=False))

    print(f"[SUCCESS] Phase D completed. Results in {RESULTS_DIR}")

if __name__ == "__main__":
    run_ensemble_research()
