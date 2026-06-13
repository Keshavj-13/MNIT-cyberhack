import pandas as pd
import numpy as np
import time
import os
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from boruta import BorutaPy
import lightgbm as lgb
import category_encoders as ce
try:
    from missingpy import MissForest
except:
    MissForest = None

SEED = 42
SAMPLE_SIZE = 3000
RESULTS_DIR = "reports/research/benchmarks"

def run_missing_prep():
    print("[PHASE 3] Executing Missing Preprocessing...")
    df = pd.read_parquet("data/processed/transaction_data.parquet").sample(SAMPLE_SIZE, random_state=SEED)
    X = df.drop(columns=['is_fraud', 'timestamp', 'customer_id', 'device_id', 'ip_address'], errors='ignore')
    y = df['is_fraud']
    cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
    
    results = []
    
    # Frequency Encoding
    print("  [EXP] Frequency Encoding")
    start = time.time()
    try:
        enc = ce.CountEncoder(cols=cat_cols)
        X_enc = enc.fit_transform(X)
        model = lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1)
        auc = cross_val_score(model, X_enc, y, cv=3, scoring='roc_auc').mean()
        results.append({"prep": "Frequency Encoding", "roc_auc": float(auc), "executed": True})
    except Exception as e: print(f"    [ERR] {e}")

    # MissForest
    print("  [EXP] MissForest")
    if MissForest:
        try:
            X_mf = X.copy()
            for c in cat_cols: X_mf[c] = X_mf[c].astype('category').cat.codes
            mf = MissForest(random_state=SEED)
            X_imp = mf.fit_transform(X_mf)
            auc = cross_val_score(model, X_imp, y, cv=3, scoring='roc_auc').mean()
            results.append({"prep": "MissForest", "roc_auc": float(auc), "executed": True})
        except Exception as e: print(f"    [ERR] {e}")

    # Fill for selections
    X_num = X.copy()
    for c in cat_cols: X_num[c] = X_num[c].astype('category').cat.codes
    X_num = X_num.fillna(0)
    
    # Boruta
    print("  [EXP] Boruta")
    try:
        rf = RandomForestClassifier(n_jobs=-1, max_depth=5, random_state=SEED)
        boruta = BorutaPy(rf, n_estimators='auto', random_state=SEED, max_iter=20)
        boruta.fit(X_num.values, y.values)
        X_bor = X_num.iloc[:, boruta.support_]
        if X_bor.shape[1] > 0:
            auc = cross_val_score(model, X_bor, y, cv=3, scoring='roc_auc').mean()
        else: auc = 0.5
        results.append({"prep": "Boruta", "roc_auc": float(auc), "executed": True})
    except Exception as e: print(f"    [ERR] {e}")

    # Permutation Selection
    print("  [EXP] Permutation Selection")
    try:
        model.fit(X_num, y)
        perm = permutation_importance(model, X_num, y, n_repeats=3, random_state=SEED)
        sel_cols = X_num.columns[perm.importances_mean > 0]
        if len(sel_cols) > 0:
            auc = cross_val_score(model, X_num[sel_cols], y, cv=3, scoring='roc_auc').mean()
        else: auc = 0.5
        results.append({"prep": "Permutation Selection", "roc_auc": float(auc), "executed": True})
    except Exception as e: print(f"    [ERR] {e}")

    # SHAP Selection
    print("  [EXP] SHAP Selection")
    try:
        import shap
        model.fit(X_num, y)
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_num)
        if isinstance(shap_vals, list): imp = np.abs(shap_vals[1]).mean(0)
        else: imp = np.abs(shap_vals).mean(0)
        sel_cols = X_num.columns[imp > np.median(imp)]
        if len(sel_cols) > 0:
            auc = cross_val_score(model, X_num[sel_cols], y, cv=3, scoring='roc_auc').mean()
        else: auc = 0.5
        results.append({"prep": "SHAP Selection", "roc_auc": float(auc), "executed": True})
    except Exception as e: print(f"    [ERR] {e}")

    df_res = pd.DataFrame(results)
    df_res.to_csv(f"{RESULTS_DIR}/missing_prep_leaderboard.csv", index=False)
    print("[SUCCESS] Phase 3 completed.")

if __name__ == "__main__":
    run_missing_prep()
