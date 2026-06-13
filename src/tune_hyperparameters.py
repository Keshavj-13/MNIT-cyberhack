import optuna
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from sklearn.model_selection import cross_val_score, StratifiedKFold
import joblib
import os

class HyperparameterTuner:
    def __init__(self, task_name, data_path, features, target):
        self.task_name = task_name
        self.df = pd.read_parquet(data_path)
        self.X = self.df[features]
        self.y = self.df[target]
        
        if task_name == "network" and "Label_Encoded" in target:
             self.y = (self.df[target] != 0).astype(int)

    def tune_xgboost(self, n_trials=10):
        print(f"[INFO] Tuning XGBoost for {self.task_name}...")
        
        def objective(trial):
            param = {
                'verbosity': 0,
                'objective': 'binary:logistic',
                'lambda': trial.suggest_float('lambda', 1e-8, 1.0, log=True),
                'alpha': trial.suggest_float('alpha', 1e-8, 1.0, log=True),
                'max_depth': trial.suggest_int('max_depth', 3, 9),
                'eta': trial.suggest_float('eta', 1e-8, 1.0, log=True),
                'gamma': trial.suggest_float('gamma', 1e-8, 1.0, log=True),
                'grow_policy': trial.suggest_categorical('grow_policy', ['depthwise', 'lossguide'])
            }
            
            model = xgb.XGBClassifier(**param)
            score = cross_val_score(model, self.X, self.y, cv=StratifiedKFold(n_splits=3), scoring='roc_auc').mean()
            return score

        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)
        
        print(f"[SUCCESS] Best trial for XGBoost: {study.best_trial.params}")
        return study.best_trial.params

    def tune_lightgbm(self, n_trials=10):
        print(f"[INFO] Tuning LightGBM for {self.task_name}...")
        
        def objective(trial):
            param = {
                'objective': 'binary',
                'metric': 'auc',
                'verbosity': -1,
                'boosting_type': 'gbdt',
                'lambda_l1': trial.suggest_float('lambda_l1', 1e-8, 10.0, log=True),
                'lambda_l2': trial.suggest_float('lambda_l2', 1e-8, 10.0, log=True),
                'num_leaves': trial.suggest_int('num_leaves', 2, 256),
                'feature_fraction': trial.suggest_float('feature_fraction', 0.4, 1.0),
                'bagging_fraction': trial.suggest_float('bagging_fraction', 0.4, 1.0),
                'bagging_freq': trial.suggest_int('bagging_freq', 1, 7),
                'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
            }
            
            try:
                model = lgb.LGBMClassifier(**param)
                score = cross_val_score(model, self.X, self.y, cv=StratifiedKFold(n_splits=3), scoring='roc_auc').mean()
                return score
            except:
                return 0.0

        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)
        
        print(f"[SUCCESS] Best trial for LightGBM: {study.best_trial.params}")
        return study.best_trial.params

if __name__ == "__main__":
    # Example usage for Transaction
    tx_features = ['amount', 'currency', 'transaction_type', 'merchant_category', 'account_age_days', 'tx_velocity_24h', 'amount_deviation', 'is_new_beneficiary', 'time_risk', 'country']
    tuner = HyperparameterTuner("transaction", "data/processed/transaction_data.parquet", tx_features, "is_fraud")
    
    # We only run 2 trials in dev mode to verify the machinery
    tuner.tune_xgboost(n_trials=2)
    tuner.tune_lightgbm(n_trials=2)
