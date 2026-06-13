import pandas as pd
import numpy as np
import time
import json
import os
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, recall_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import (
    StandardScaler, MinMaxScaler, RobustScaler, 
    QuantileTransformer, PowerTransformer
)

from sklearn.linear_model import LogisticRegression

class ResearchEngine:
    def __init__(self, data_path, target_col, task_name):
        self.df = pd.read_parquet(data_path)
        self.target = target_col
        self.task_name = task_name
        self.X = self.df.drop(columns=[self.target, 'timestamp', 'customer_id', 'device_id', 'ip_address', 'Label'], errors='ignore')
        self.y = self.df[self.target]
        
        # Ensure target is binary
        if task_name == "network" and self.y.dtype == object:
            self.y = (self.y != "BENIGN").astype(int)
        elif task_name == "network" and "Label_Encoded" in self.target:
             self.y = (self.df[self.target] != 0).astype(int)
             
        self.results_dir = "reports/research/benchmarks"
        os.makedirs(self.results_dir, exist_ok=True)

    def run_preprocessing_study(self):
        print(f"[RESEARCH] Starting Preprocessing Study for {self.task_name}...")
        
        imputers = {
            "mean": SimpleImputer(strategy='mean'),
            "median": SimpleImputer(strategy='median'),
            "most_frequent": SimpleImputer(strategy='most_frequent'),
            "constant": SimpleImputer(strategy='constant', fill_value=0),
            "iterative": IterativeImputer(random_state=42, max_iter=5),
            "knn": KNNImputer(n_neighbors=5)
        }
        
        scalers = {
            "none": None,
            "standard": StandardScaler(),
            "minmax": MinMaxScaler(),
            "robust": RobustScaler(),
            "quantile": QuantileTransformer(output_distribution='normal', random_state=42),
            "power": PowerTransformer(method='yeo-johnson')
        }
        
        results = []
        
        # We sample for research speed
        X_sample = self.X.sample(min(10000, len(self.X)), random_state=42)
        y_sample = self.y.loc[X_sample.index]
        
        # Introduce some artificial NaNs if none exist to test imputers
        if X_sample.isnull().sum().sum() == 0:
            for col in X_sample.select_dtypes(include=[np.number]).columns[:3]:
                X_sample.loc[X_sample.sample(frac=0.1).index, col] = np.nan

        for imp_name, imp in imputers.items():
            for sc_name, sc in scalers.items():
                print(f"  [EXP] Imputer: {imp_name}, Scaler: {sc_name}")
                start_time = time.time()
                
                try:
                    # Pipeline execution
                    X_imp = imp.fit_transform(X_sample)
                    if sc:
                        X_final = sc.fit_transform(X_imp)
                    else:
                        X_final = X_imp
                    
                    # Evaluation with Baseline RF
                    model = RandomForestClassifier(n_estimators=50, n_jobs=-1, random_state=42)
                    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
                    scores = []
                    for train_idx, val_idx in skf.split(X_final, y_sample):
                        model.fit(X_final[train_idx], y_sample.iloc[train_idx])
                        probs = model.predict_proba(X_final[val_idx])[:, 1]
                        scores.append(roc_auc_score(y_sample.iloc[val_idx], probs))
                    
                    auc = np.mean(scores)
                    duration = time.time() - start_time
                    
                    results.append({
                        "imputer": imp_name,
                        "scaler": sc_name,
                        "roc_auc": float(auc),
                        "duration": float(duration)
                    })
                except Exception as e:
                    print(f"    [ERROR] {e}")

        output_path = os.path.join(self.results_dir, f"{self.task_name}_preprocessing.json")
        with open(output_path, "w") as f:
            json.dump(results, f, indent=4)
        print(f"[SUCCESS] Preprocessing study saved to {output_path}")

    def run_imbalance_study(self):
        print(f"[RESEARCH] Starting Imbalance Study for {self.task_name}...")
        from imblearn.over_sampling import SMOTE, ADASYN, BorderlineSMOTE, RandomOverSampler
        from imblearn.under_sampling import RandomUnderSampler
        from imblearn.combine import SMOTEENN, SMOTETomek
        
        samplers = {
            "none": None,
            "ros": RandomOverSampler(random_state=42),
            "rus": RandomUnderSampler(random_state=42),
            "smote": SMOTE(random_state=42),
            "borderline_smote": BorderlineSMOTE(random_state=42),
            "adasyn": ADASYN(random_state=42),
            "smote_enn": SMOTEENN(random_state=42),
            "smote_tomek": SMOTETomek(random_state=42)
        }
        
        results = []
        X_sample = self.X.fillna(0).sample(min(10000, len(self.X)), random_state=42)
        y_sample = self.y.loc[X_sample.index]

        for name, sampler in samplers.items():
            print(f"  [EXP] Sampler: {name}")
            start_time = time.time()
            try:
                if sampler:
                    X_res, y_res = sampler.fit_resample(X_sample, y_sample)
                else:
                    X_res, y_res = X_sample, y_sample
                
                model = RandomForestClassifier(n_estimators=50, n_jobs=-1, random_state=42)
                skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
                scores = []
                for train_idx, val_idx in skf.split(X_res, y_res):
                    model.fit(X_res.iloc[train_idx], y_res.iloc[train_idx])
                    probs = model.predict_proba(X_res.iloc[val_idx])[:, 1]
                    scores.append(roc_auc_score(y_res.iloc[val_idx], probs))
                
                results.append({
                    "sampler": name,
                    "roc_auc": float(np.mean(scores)),
                    "duration": float(time.time() - start_time)
                })
            except Exception as e:
                print(f"    [ERROR] {e}")

        output_path = os.path.join(self.results_dir, f"{self.task_name}_imbalance.json")
        with open(output_path, "w") as f:
            json.dump(results, f, indent=4)

    def run_selection_study(self):
        print(f"[RESEARCH] Starting Feature Selection Study for {self.task_name}...")
        from sklearn.feature_selection import SelectFromModel, VarianceThreshold, SelectKBest, mutual_info_classif
        from boruta import BorutaPy
        
        # Fill NaNs for selection methods that don't handle them
        X_clean = self.X.fillna(0).sample(min(5000, len(self.X)), random_state=42)
        y_clean = self.y.loc[X_clean.index]
        
        selectors = {
            "variance": VarianceThreshold(threshold=0.01),
            "mutual_info": SelectKBest(mutual_info_classif, k=min(5, X_clean.shape[1])),
            "l1": SelectFromModel(LogisticRegression(penalty="l1", solver="liblinear", random_state=42)),
            "rf_importance": SelectFromModel(RandomForestClassifier(n_estimators=100, random_state=42)),
            "boruta": BorutaPy(RandomForestClassifier(n_estimators=50, n_jobs=-1, max_depth=5, random_state=42), n_estimators='auto', random_state=42)
        }
        
        results = []
        for name, selector in selectors.items():
            print(f"  [EXP] Selector: {name}")
            start_time = time.time()
            try:
                selector.fit(X_clean.values, y_clean.values)
                if hasattr(selector, 'get_support'):
                    mask = selector.get_support()
                else:
                    mask = selector.support_ # for Boruta
                
                feature_count = int(np.sum(mask))
                
                results.append({
                    "selector": name,
                    "feature_count": feature_count,
                    "duration": float(time.time() - start_time)
                })
            except Exception as e:
                print(f"    [ERROR] {e}")

        output_path = os.path.join(self.results_dir, f"{self.task_name}_selection.json")
        with open(output_path, "w") as f:
            json.dump(results, f, indent=4)

if __name__ == "__main__":
    tasks = [
        ("transaction", "data/processed/transaction_data.parquet", "is_fraud"),
        ("network", "data/processed/network_data.parquet", "Label_Encoded")
    ]
    
    for name, path, target in tasks:
        engine = ResearchEngine(path, target, name)
        engine.run_preprocessing_study()
        engine.run_imbalance_study()
        engine.run_selection_study()
