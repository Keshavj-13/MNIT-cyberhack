import pandas as pd
import numpy as np
import time
import json
import os
import itertools
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import (
    StandardScaler, MinMaxScaler, RobustScaler, 
    QuantileTransformer, PowerTransformer, OrdinalEncoder
)
from category_encoders import OneHotEncoder, TargetEncoder, CatBoostEncoder
from sklearn.feature_selection import SelectKBest, mutual_info_classif, RFE
from sklearn.ensemble import RandomForestClassifier
import lightgbm as lgb

# Config
SEED = 42
SAMPLE_SIZE = 3000 # Reduced for speed in such a large grid
RESULTS_DIR = "reports/research/benchmarks"
os.makedirs(RESULTS_DIR, exist_ok=True)

def run_preprocessing_grid():
    tasks = [
        ("transaction", "data/processed/transaction_data.parquet", "is_fraud"),
        ("network", "data/processed/network_data.parquet", "Label_Encoded")
    ]
    
    # Grid Dimensions
    imputers = ["mean", "median", "most_frequent", "knn", "iterative", "native"]
    scalers = ["none", "standard", "minmax", "robust", "quantile", "power"]
    encoders = ["onehot", "ordinal", "target", "catboost"]
    selectors = ["none", "mutual_info", "kbest", "rfe"]
    
    for task_name, path, target in tasks:
        print(f"[PHASE B] Grid Search for {task_name}...")
        df_full = pd.read_parquet(path)
        
        # Binary target for network
        if task_name == "network" and "Label_Encoded" in target:
             df_full[target] = (df_full[target] != 0).astype(int)
             
        df = df_full.sample(min(SAMPLE_SIZE, len(df_full)), random_state=SEED)
        
        X = df.drop(columns=[target, 'timestamp', 'customer_id', 'device_id', 'ip_address', 'Label'], errors='ignore')
        y = df[target]
        
        # Identify categorical vs numerical
        cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
        num_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        
        results = []
        
        combinations = list(itertools.product(imputers, scalers, encoders, selectors))
        total = len(combinations)
        print(f"  Total combinations: {total}")
        
        for i, (imp_name, sc_name, enc_name, sel_name) in enumerate(combinations):
            if i % 50 == 0:
                print(f"    Progress: {i}/{total}")
                
            start_time = time.time()
            try:
                X_curr = X.copy()
                
                # 1. Encoding
                if enc_name == "onehot":
                    enc = OneHotEncoder(cols=cat_cols)
                elif enc_name == "ordinal":
                    enc = OrdinalEncoder() # Simplified for speed
                elif enc_name == "target":
                    enc = TargetEncoder(cols=cat_cols)
                elif enc_name == "catboost":
                    enc = CatBoostEncoder(cols=cat_cols)
                
                if cat_cols:
                    X_curr = enc.fit_transform(X_curr, y)
                
                # 2. Imputation
                if imp_name != "native":
                    if imp_name == "mean":
                        imp = SimpleImputer(strategy='mean')
                    elif imp_name == "median":
                        imp = SimpleImputer(strategy='median')
                    elif imp_name == "most_frequent":
                        imp = SimpleImputer(strategy='most_frequent')
                    elif imp_name == "knn":
                        imp = KNNImputer(n_neighbors=5)
                    elif imp_name == "iterative":
                        imp = IterativeImputer(max_iter=5, random_state=SEED)
                    
                    X_curr = pd.DataFrame(imp.fit_transform(X_curr), columns=X_curr.columns)
                
                # 3. Scaling
                if sc_name != "none":
                    if sc_name == "standard":
                        sc = StandardScaler()
                    elif sc_name == "minmax":
                        sc = MinMaxScaler()
                    elif sc_name == "robust":
                        sc = RobustScaler()
                    elif sc_name == "quantile":
                        sc = QuantileTransformer(output_distribution='normal', random_state=SEED)
                    elif sc_name == "power":
                        sc = PowerTransformer()
                    
                    X_curr = pd.DataFrame(sc.fit_transform(X_curr), columns=X_curr.columns)
                
                # 4. Selection
                if sel_name != "none":
                    if sel_name == "mutual_info":
                        sel = SelectKBest(mutual_info_classif, k=min(10, X_curr.shape[1]))
                    elif sel_name == "kbest":
                        sel = SelectKBest(k=min(10, X_curr.shape[1]))
                    elif sel_name == "rfe":
                        # RFE is slow, use a small n_features
                        sel = RFE(lgb.LGBMRegressor(n_jobs=1, verbose=-1), n_features_to_select=min(10, X_curr.shape[1]))
                    
                    X_curr = pd.DataFrame(sel.fit_transform(X_curr, y), columns=X_curr.columns[:10] if X_curr.shape[1]>10 else X_curr.columns)

                # 5. Evaluate
                # Use LightGBM as it handles NaNs natively if imp_name == 'native'
                model = lgb.LGBMClassifier(n_jobs=-1, verbose=-1, random_state=SEED)
                skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED)
                
                scores = []
                for train_idx, val_idx in skf.split(X_curr, y):
                    model.fit(X_curr.iloc[train_idx], y.iloc[train_idx])
                    probs = model.predict_proba(X_curr.iloc[val_idx])[:, 1]
                    scores.append(roc_auc_score(y.iloc[val_idx], probs))
                
                mean_auc = np.mean(scores)
                duration = time.time() - start_time
                
                results.append({
                    "imputer": imp_name,
                    "scaler": sc_name,
                    "encoder": enc_name,
                    "selector": sel_name,
                    "roc_auc": float(mean_auc),
                    "duration": float(duration)
                })
                
            except Exception as e:
                # print(f"      [ERR] {imp_name}-{sc_name}-{enc_name}-{sel_name}: {e}")
                pass

        # Save results
        res_df = pd.DataFrame(results)
        res_df.to_csv(f"{RESULTS_DIR}/{task_name}_preprocessing_leaderboard.csv", index=False)
        
        # Markdown summary (Top 10)
        with open(f"{RESULTS_DIR}/{task_name}_preprocessing_leaderboard.md", "w") as f:
            f.write(f"# Preprocessing Leaderboard: {task_name}\n\n")
            f.write(res_df.sort_values("roc_auc", ascending=False).head(20).to_markdown(index=False))

    print(f"[SUCCESS] Phase B completed. Results in {RESULTS_DIR}")

if __name__ == "__main__":
    run_preprocessing_grid()
