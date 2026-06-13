import pandas as pd
import numpy as np
import time
import json
import os
import lightgbm as lgb
from sklearn.inspection import permutation_importance
from lime import lime_tabular
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split

# Config
SEED = 42
SAMPLE_SIZE = 5000
RESULTS_DIR = "reports/research/benchmarks"
os.makedirs(RESULTS_DIR, exist_ok=True)

def run_explainability_research():
    tasks = [
        ("transaction", "data/processed/transaction_data.parquet", "is_fraud"),
        ("network", "data/processed/network_data.parquet", "Label_Encoded")
    ]
    
    for task_name, path, target in tasks:
        print(f"[PHASE H] Explainability Research for {task_name}...")
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
        
        X_train, X_test, y_train, y_test = train_test_split(X_proc, y, test_size=0.2, random_state=SEED)
        
        # Best Model (LGBM as proxy)
        model = lgb.LGBMClassifier(n_estimators=100, n_jobs=-1, verbose=-1, random_state=SEED)
        model.fit(X_train, y_train)
        
        explanations = {}
        
        # 1. Gain Importance
        print("  [EXP] Gain Importance")
        explanations["gain"] = dict(zip(X_proc.columns, [float(x) for x in model.feature_importances_]))
        
        # 2. Permutation Importance
        print("  [EXP] Permutation Importance")
        perm = permutation_importance(model, X_test, y_test, n_repeats=5, random_state=SEED, n_jobs=-1)
        explanations["permutation"] = dict(zip(X_proc.columns, [float(x) for x in perm.importances_mean]))
        
        # 3. LIME
        print("  [EXP] LIME")
        explainer = lime_tabular.LimeTabularExplainer(X_train.values, feature_names=X_proc.columns, class_names=['Benign', 'Fraud'], mode='classification')
        exp = explainer.explain_instance(X_test.iloc[0].values, model.predict_proba, num_features=5)
        explanations["lime_sample"] = exp.as_list()

        # 4. SHAP (Try-Except due to DLL issues)
        try:
            import shap
            print("  [EXP] SHAP")
            shap_explainer = shap.TreeExplainer(model)
            shap_values = shap_explainer.shap_values(X_test)
            # Take mean absolute shap values
            if isinstance(shap_values, list):
                # multi-class or binary with list
                importance = np.abs(shap_values[1]).mean(axis=0)
            else:
                importance = np.abs(shap_values).mean(axis=0)
            explanations["shap"] = dict(zip(X_proc.columns, [float(x) for x in importance]))
        except Exception as e:
            print(f"  [SKIP] SHAP: {e}")

        output_path = os.path.join(RESULTS_DIR, f"{task_name}_explainability.json")
        with open(output_path, "w") as f:
            json.dump(explanations, f, indent=4)

    print(f"[SUCCESS] Phase H completed.")

if __name__ == "__main__":
    run_explainability_research()
