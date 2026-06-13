import pandas as pd
import numpy as np
import time
import json
import os
import joblib
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import roc_auc_score, f1_score
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier, ExtraTreesClassifier, 
    AdaBoostClassifier, GradientBoostingClassifier, 
    HistGradientBoostingClassifier, StackingClassifier
)
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

class TraditionalModelBenchmarker:
    def __init__(self, data_path, target_col, task_name):
        self.df = pd.read_parquet(data_path)
        self.target = target_col
        self.task_name = task_name
        self.X = self.df.drop(columns=[self.target, 'timestamp', 'customer_id', 'device_id', 'ip_address', 'Label'], errors='ignore').fillna(0)
        self.y = self.df[self.target]
        
        if task_name == "network" and self.y.dtype == object:
            self.y = (self.y != "BENIGN").astype(int)
        elif task_name == "network" and "Label_Encoded" in self.target:
             self.y = (self.df[target] != 0).astype(int)
             
        self.results_dir = "reports/research/benchmarks"
        os.makedirs(self.results_dir, exist_ok=True)

    def get_models(self):
        models = {
            "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
            "Ridge": RidgeClassifier(random_state=42),
            "GaussianNB": GaussianNB(),
            "KNN": KNeighborsClassifier(),
            "DecisionTree": DecisionTreeClassifier(random_state=42),
            "RandomForest": RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42),
            "ExtraTrees": ExtraTreesClassifier(n_estimators=100, n_jobs=-1, random_state=42),
            "AdaBoost": AdaBoostClassifier(random_state=42),
            "GradientBoosting": GradientBoostingClassifier(random_state=42),
            "HistGradientBoosting": HistGradientBoostingClassifier(random_state=42),
            "XGBoost": xgb.XGBClassifier(random_state=42, n_jobs=-1),
            "LightGBM": lgb.LGBMClassifier(random_state=42, n_jobs=-1, verbose=-1),
            "CatBoost": CatBoostClassifier(random_state=42, verbose=0, thread_count=-1)
        }
        return models

    def run_benchmark(self):
        print(f"[RESEARCH] Starting Traditional Model Benchmark for {self.task_name}...")
        models = self.get_models()
        results = []
        
        X_sample = self.X.sample(min(10000, len(self.X)), random_state=42)
        y_sample = self.y.loc[X_sample.index]
        
        skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        
        for name, model in models.items():
            print(f"  [EXP] Model: {name}")
            start_time = time.time()
            try:
                # Use cross_val_score for stability
                scores = cross_val_score(model, X_sample, y_sample, cv=skf, scoring='roc_auc', n_jobs=-1)
                duration = time.time() - start_time
                
                results.append({
                    "model": name,
                    "roc_auc_mean": float(np.mean(scores)),
                    "roc_auc_std": float(np.std(scores)),
                    "duration": float(duration)
                })
            except Exception as e:
                print(f"    [ERROR] {e}")

        output_path = os.path.join(self.results_dir, f"{self.task_name}_traditional_models.json")
        with open(output_path, "w") as f:
            json.dump(results, f, indent=4)
        print(f"[SUCCESS] Traditional model benchmark saved to {output_path}")

if __name__ == "__main__":
    tasks = [
        ("transaction", "data/processed/transaction_data.parquet", "is_fraud"),
        ("network", "data/processed/network_data.parquet", "Label_Encoded")
    ]
    
    for name, path, target in tasks:
        benchmarker = TraditionalModelBenchmarker(path, target, name)
        benchmarker.run_benchmark()
