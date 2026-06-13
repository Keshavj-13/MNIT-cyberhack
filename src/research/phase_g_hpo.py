import optuna
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer
import os

# Config
SEED = 42
SAMPLE_SIZE = 5000
TRIALS = 100 # User requested 100
RESULTS_DIR = "reports/research/benchmarks"
os.makedirs(RESULTS_DIR, exist_ok=True)

def objective_xgb(trial, X, y):
    params = {
        'verbosity': 0,
        'objective': 'binary:logistic',
        'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
    }
    model = xgb.XGBClassifier(**params, random_state=SEED, n_jobs=-1)
    score = cross_val_score(model, X, y, cv=3, scoring='roc_auc', n_jobs=-1).mean()
    return score

def objective_lgbm(trial, X, y):
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'verbosity': -1,
        'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
        'num_leaves': trial.suggest_int('num_leaves', 20, 300),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'feature_fraction': trial.suggest_float('feature_fraction', 0.5, 1.0),
    }
    model = lgb.LGBMClassifier(**params, random_state=SEED, n_jobs=-1)
    score = cross_val_score(model, X, y, cv=3, scoring='roc_auc', n_jobs=-1).mean()
    return score

def run_hpo():
    tasks = [
        ("transaction", "data/processed/transaction_data.parquet", "is_fraud"),
        ("network", "data/processed/network_data.parquet", "Label_Encoded")
    ]
    
    all_trials = []
    
    for task_name, path, target in tasks:
        print(f"[PHASE G] HPO for {task_name}...")
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
        
        # XGBoost Study
        print("  Tuning XGBoost...")
        study_xgb = optuna.create_study(direction='maximize')
        study_xgb.optimize(lambda t: objective_xgb(t, X_proc, y), n_trials=TRIALS)
        
        # LightGBM Study
        print("  Tuning LightGBM...")
        study_lgbm = optuna.create_study(direction='maximize')
        study_lgbm.optimize(lambda t: objective_lgbm(t, X_proc, y), n_trials=TRIALS)
        
        # Export trials
        df_xgb = study_xgb.trials_dataframe()
        df_xgb['model'] = 'XGBoost'
        df_xgb['task'] = task_name
        
        df_lgbm = study_lgbm.trials_dataframe()
        df_lgbm['model'] = 'LightGBM'
        df_lgbm['task'] = task_name
        
        all_trials.extend([df_xgb, df_lgbm])

    final_df = pd.concat(all_trials)
    final_df.to_csv(f"{RESULTS_DIR}/optuna_trials.csv", index=False)
    print(f"[SUCCESS] HPO completed. Trials saved to {RESULTS_DIR}/optuna_trials.csv")

if __name__ == "__main__":
    run_hpo()
