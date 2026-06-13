import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from sklearn.model_selection import train_test_split, cross_validate, StratifiedKFold
from sklearn.metrics import (
    roc_auc_score, average_precision_score, accuracy_score, 
    precision_score, recall_score, f1_score, confusion_matrix,
    classification_report
)
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import lightgbm as lgb
import xgboost as xgb
import joblib

class ModelValidator:
    def __init__(self, task_name, data_path, features, target):
        self.task_name = task_name
        self.data_path = data_path
        self.features = features
        self.target = target
        self.results_dir = "reports/validation"
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Load Data
        self.df = pd.read_parquet(data_path)
        self.X = self.df[features]
        self.y = self.df[target]
        
        # Handle binary target for network if needed
        if task_name == "network" and self.y.dtype == object:
             self.y = (self.y != "BENIGN").astype(int)
        elif task_name == "network" and "Label_Encoded" in target:
             self.y = (self.df[target] != 0).astype(int)

    def get_models(self):
        models = {
            "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
            "XGBoost": xgb.XGBClassifier(random_state=42, n_jobs=-1)
        }
        
        # Try to add models that might fail due to DLL issues
        try:
            models["RandomForest"] = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        except Exception as e:
            print(f"[WARN] Could not initialize RandomForest: {e}")
            
        try:
            models["LightGBM"] = lgb.LGBMClassifier(random_state=42, n_jobs=-1, verbose=-1)
        except Exception as e:
            print(f"[WARN] Could not initialize LightGBM: {e}")
            
        return models

    def validate(self):
        print(f"\n[INFO] Validating models for {self.task_name}...")
        models = self.get_models()
        leaderboard = []
        
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        
        for name, model in models.items():
            print(f"[INFO] Evaluating {name}...")
            try:
                # 5-Fold Cross Validation
                cv_results = cross_validate(
                    model, self.X, self.y, 
                    cv=skf, 
                    scoring=['roc_auc', 'f1', 'precision', 'recall'],
                    n_jobs=-1
                )
                
                # Train-Test Split for detailed report
                X_train, X_test, y_train, y_test = train_test_split(
                    self.X, self.y, test_size=0.2, random_state=42, stratify=self.y
                )
                model.fit(X_train, y_train)
                y_prob = model.predict_proba(X_test)[:, 1]
                y_pred = model.predict(X_test)
                
                metrics = {
                    "model": name,
                    "roc_auc_cv": float(np.mean(cv_results['test_roc_auc'])),
                    "roc_auc_std": float(np.std(cv_results['test_roc_auc'])),
                    "f1_cv": float(np.mean(cv_results['test_f1'])),
                    "pr_auc": float(average_precision_score(y_test, y_prob)),
                    "accuracy": float(accuracy_score(y_test, y_pred)),
                    "precision": float(precision_score(y_test, y_pred, zero_division=0)),
                    "recall": float(recall_score(y_test, y_pred, zero_division=0)),
                    "status": "UNUSABLE" if np.mean(cv_results['test_roc_auc']) < 0.60 else "PASS"
                }
                leaderboard.append(metrics)
                
                # Save individual report
                self.save_individual_report(name, y_test, y_pred, y_prob, metrics, model.feature_importances_ if hasattr(model, 'feature_importances_') else None)
                
            except Exception as e:
                print(f"[ERROR] Failed to evaluate {name}: {e}")

        self.save_leaderboard(leaderboard)
        return leaderboard

    def save_individual_report(self, name, y_true, y_pred, y_prob, metrics, importance):
        report_data = {
            "metrics": metrics,
            "classification_report": classification_report(y_true, y_pred, output_dict=True),
            "confusion_matrix": confusion_matrix(y_true, y_pred).tolist()
        }
        
        if importance is not None:
            report_data["feature_importance"] = dict(zip(self.features, [float(x) for x in importance]))

        report_path = os.path.join(self.results_dir, f"{self.task_name}_{name}_report.json")
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=4)

    def save_leaderboard(self, leaderboard):
        df_lb = pd.DataFrame(leaderboard).sort_values("roc_auc_cv", ascending=False)
        lb_path = os.path.join(self.results_dir, f"{self.task_name}_leaderboard.md")
        
        with open(lb_path, "w") as f:
            f.write(f"# {self.task_name.capitalize()} Model Leaderboard\n\n")
            f.write(df_lb.to_markdown(index=False))
            f.write("\n\n## Recommendations\n")
            
            best = df_lb.iloc[0]
            if best['roc_auc_cv'] < 0.60:
                f.write(f"**WARNING:** All models for {self.task_name} are currently flagged as **UNUSABLE** (AUC < 0.60).\n")
                f.write("This is expected for synthetic development data. Real data is required for meaningful training.\n")
            else:
                f.write(f"The best model is **{best['model']}** with an AUC of {best['roc_auc_cv']:.4f}.\n")
                
            # Issue Detection
            if best['roc_auc_cv'] > 0.99:
                f.write("- **Potential Data Leakage Detected:** AUC is suspiciously high (>0.99).\n")
            if best['roc_auc_cv'] - best['roc_auc_std'] < 0.5:
                 f.write("- **High Variance:** Model performance is inconsistent across folds.\n")

if __name__ == "__main__":
    # Validate Transaction Models
    tx_features = ['amount', 'currency', 'transaction_type', 'merchant_category', 'account_age_days', 'tx_velocity_24h', 'amount_deviation', 'is_new_beneficiary', 'time_risk', 'country']
    tx_validator = ModelValidator("transaction", "data/processed/transaction_data.parquet", tx_features, "is_fraud")
    tx_validator.validate()
    
    # Validate Network Models
    net_features = ['Destination Port', 'Flow Duration', 'Total Fwd Packets', 'Total Backward Packets', 'Fwd Packet Length Max', 'Bwd Packet Length Max', 'Flow Bytes/s', 'Flow Packets/s']
    net_validator = ModelValidator("network", "data/processed/network_data.parquet", net_features, "Label_Encoded")
    net_validator.validate()
