import pandas as pd
import numpy as np
import time
import json
import os
import joblib
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import Lasso, ElasticNet, LogisticRegression
from sklearn.neighbors import LocalOutlierFactor
from imblearn.ensemble import RUSBoostClassifier
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer

SEED = 42
SAMPLE_SIZE = 5000
RESULTS_DIR = "reports/research/benchmarks"

def run_missing_trad():
    print("[PHASE 2] Executing Missing Traditional Models...")
    df = pd.read_parquet("data/processed/transaction_data.parquet").sample(SAMPLE_SIZE, random_state=SEED)
    X = df.drop(columns=['is_fraud', 'timestamp', 'customer_id', 'device_id', 'ip_address'], errors='ignore').fillna(0)
    y = df['is_fraud']
    
    cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
    if cat_cols:
        X[cat_cols] = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1).fit_transform(X[cat_cols].astype(str))
    X_proc = StandardScaler().fit_transform(SimpleImputer().fit_transform(X))
    
    models = {
        "RUSBoost": RUSBoostClassifier(random_state=SEED),
        # Lasso and ElasticNet in scikit-learn are Regressors. We use LogisticRegression with penalty l1/elasticnet
        "Lasso": LogisticRegression(penalty='l1', solver='liblinear', random_state=SEED),
        "ElasticNet": LogisticRegression(penalty='elasticnet', solver='saga', l1_ratio=0.5, random_state=SEED),
        "Local Outlier Factor": LocalOutlierFactor(novelty=True)
    }
    
    results = []
    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED)
    
    for name, model in models.items():
        print(f"  [EXP] {name}")
        start = time.time()
        try:
            if name == "Local Outlier Factor":
                model.fit(X_proc)
                scores = -model.decision_function(X_proc)
                auc = roc_auc_score(y, scores)
                duration = time.time() - start
                joblib.dump(model, f"models/{name.replace(' ', '_')}.joblib")
                results.append({"model": name, "roc_auc": float(auc), "duration": float(duration), "executed": True})
            else:
                cv_results = cross_validate(model, X_proc, y, cv=skf, scoring='roc_auc', n_jobs=-1)
                model.fit(X_proc, y)
                duration = time.time() - start
                joblib.dump(model, f"models/{name.replace(' ', '_')}.joblib")
                results.append({"model": name, "roc_auc": float(np.mean(cv_results['test_roc_auc'])), "duration": float(duration), "executed": True})
        except Exception as e:
            print(f"    [ERR] {name}: {e}")
            
    df_res = pd.DataFrame(results)
    df_res.to_csv(f"{RESULTS_DIR}/missing_trad_leaderboard.csv", index=False)
    print("[SUCCESS] Phase 2 completed.")

if __name__ == "__main__":
    run_missing_trad()
