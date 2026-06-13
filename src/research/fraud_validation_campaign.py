import os
import time
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_score, 
    recall_score, f1_score, brier_score_loss
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import ExtraTreesClassifier, VotingClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier
import shap

SEED = 42
DATA_PATH = "data/raw/real_fraud/ulb_creditcard.parquet"
RESULTS_DIR = "reports/research"
os.makedirs(RESULTS_DIR, exist_ok=True)

# Helper: Expected Calibration Error
def expected_calibration_error(y_true, y_prob, n_bins=10):
    bins = np.linspace(0., 1., n_bins + 1)
    binned = np.digitize(y_prob, bins) - 1
    
    bin_accs = np.zeros(n_bins)
    bin_confs = np.zeros(n_bins)
    bin_sizes = np.zeros(n_bins)
    
    for b in range(n_bins):
        bin_sizes[b] = len(y_prob[binned == b])
        if bin_sizes[b] > 0:
            bin_accs[b] = (y_true[binned == b]).sum() / bin_sizes[b]
            bin_confs[b] = (y_prob[binned == b]).mean()
            
    ece = np.sum(np.abs(bin_accs - bin_confs) * (bin_sizes / len(y_prob)))
    return ece

def get_models():
    # ExtraTrees needs an imputer for missing values robustness tests later
    et = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('clf', ExtraTreesClassifier(n_estimators=100, n_jobs=-1, class_weight='balanced', random_state=SEED))
    ])
    
    lgbm = lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1, scale_pos_weight=10)
    xgb_m = xgb.XGBClassifier(random_state=SEED, n_jobs=-1, scale_pos_weight=10)
    cat = CatBoostClassifier(random_state=SEED, verbose=0, thread_count=-1, scale_pos_weight=10)
    
    voting = VotingClassifier(
        estimators=[('lgbm', lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1)), 
                    ('xgb', xgb.XGBClassifier(random_state=SEED, n_jobs=-1))],
        voting='soft', n_jobs=-1
    )
    
    return {
        "LightGBM": lgbm,
        "XGBoost": xgb_m,
        "CatBoost": cat,
        "ExtraTrees": et,
        "VotingEnsemble": voting
    }

def run_campaign():
    print("[INFO] Loading ULB Dataset...")
    df = pd.read_parquet(DATA_PATH)
    target_col = 'Class'
    X = df.drop(columns=[target_col])
    y = df[target_col]
    
    # --- PHASE 1: LEAKAGE AUDIT ---
    print("[PHASE 1] Leakage Audit...")
    # 60/20/20 split
    X_train_val, X_test, y_train_val, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    X_train, X_val, y_train, y_val = train_test_split(X_train_val, y_train_val, test_size=0.25, stratify=y_train_val, random_state=SEED) # 0.25 * 0.8 = 0.2
    
    models = get_models()
    leakage_records = []
    
    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED)
    
    trained_models = {} # Store for later phases
    
    for name, model in models.items():
        print(f"  Evaluating {name}")
        # Cross Validation on train_val strictly (no test leakage)
        cv_aucs, cv_pr_aucs = [], []
        for tr_idx, va_idx in skf.split(X_train_val, y_train_val):
            X_tr, y_tr = X_train_val.iloc[tr_idx], y_train_val.iloc[tr_idx]
            X_va, y_va = X_train_val.iloc[va_idx], y_train_val.iloc[va_idx]
            model.fit(X_tr, y_tr)
            probs = model.predict_proba(X_va)[:, 1]
            cv_aucs.append(roc_auc_score(y_va, probs))
            cv_pr_aucs.append(average_precision_score(y_va, probs))
            
        # Final train for subsequent phases
        model.fit(X_train, y_train)
        probs_val = model.predict_proba(X_val)[:, 1]
        
        # Optimize threshold on Validation set ONLY (No Test Leakage)
        best_f1, best_t = 0, 0.5
        for t in np.arange(0.05, 0.95, 0.05):
            preds = (probs_val >= t).astype(int)
            f = f1_score(y_val, preds, zero_division=0)
            if f > best_f1:
                best_f1 = f
                best_t = t
                
        # OOF / Test evaluation
        probs_test = model.predict_proba(X_test)[:, 1]
        preds_test = (probs_test >= best_t).astype(int)
        
        trained_models[name] = {"model": model, "best_t": best_t, "probs_test": probs_test, "preds_test": preds_test}
        
        leakage_records.append({
            "model": name,
            "train_rows": len(X_train),
            "val_rows": len(X_val),
            "test_rows": len(X_test),
            "fraud_train": y_train.sum(),
            "fraud_val": y_val.sum(),
            "fraud_test": y_test.sum(),
            "smote_applied": "No (Using sample weights)",
            "threshold_opt_touched_test": "No (Optimized on Val)",
            "cv_roc_auc": float(np.mean(cv_aucs)),
            "cv_pr_auc": float(np.mean(cv_pr_aucs)),
            "oof_test_roc_auc": float(roc_auc_score(y_test, probs_test)),
            "oof_test_pr_auc": float(average_precision_score(y_test, probs_test)),
            "oof_test_f1": float(f1_score(y_test, preds_test, zero_division=0))
        })
        
    pd.DataFrame(leakage_records).to_csv(os.path.join(RESULTS_DIR, "leakage_audit.csv"), index=False)

    # --- PHASE 2: CALIBRATION AUDIT ---
    print("[PHASE 2] Calibration Audit...")
    cal_records = []
    
    for name, data in trained_models.items():
        model = data["model"]
        probs_test = data["probs_test"]
        
        brier_raw = brier_score_loss(y_test, probs_test)
        ece_raw = expected_calibration_error(y_test.values, probs_test)
        
        # Isotonic Regression on Val
        cal_iso = CalibratedClassifierCV(estimator=model, cv=2, method='isotonic')
        cal_iso.fit(X_val, y_val)
        probs_iso = cal_iso.predict_proba(X_test)[:, 1]
        brier_iso = brier_score_loss(y_test, probs_iso)
        
        # Platt Scaling on Val
        cal_platt = CalibratedClassifierCV(estimator=model, cv=2, method='sigmoid')
        cal_platt.fit(X_val, y_val)
        probs_platt = cal_platt.predict_proba(X_test)[:, 1]
        brier_platt = brier_score_loss(y_test, probs_platt)
        
        cal_records.append({
            "model": name,
            "brier_raw": float(brier_raw),
            "ece_raw": float(ece_raw),
            "brier_isotonic": float(brier_iso),
            "brier_platt": float(brier_platt)
        })
    pd.DataFrame(cal_records).to_csv(os.path.join(RESULTS_DIR, "calibration_report.csv"), index=False)

    # --- PHASE 3: ROBUSTNESS AUDIT ---
    print("[PHASE 3] Robustness Audit...")
    rob_records = []
    
    # Dist Shift: Train first 50% time, Test last 50%
    # OpenML ULB dataset drops 'Time', so we split sequentially as original data is chronologically ordered
    split_idx = int(len(df) * 0.5)
    X_ds_train = df.iloc[:split_idx].drop(columns=[target_col])
    y_ds_train = df.iloc[:split_idx][target_col]
    X_ds_test = df.iloc[split_idx:].drop(columns=[target_col])
    y_ds_test = df.iloc[split_idx:][target_col]
    
    for name, data in trained_models.items():
        model = data["model"]
        base_pr = leakage_records[[r['model'] for r in leakage_records].index(name)]['oof_test_pr_auc']
        
        def eval_corrupted(X_corr):
            p = model.predict_proba(X_corr)[:, 1]
            return average_precision_score(y_test, p)

        res = {"model": name, "baseline_pr": base_pr}
        
        # Noise
        for pct in [0.01, 0.05, 0.10]:
            X_noise = X_test + np.random.normal(0, X_test.std() * pct, X_test.shape)
            res[f"noise_{int(pct*100)}"] = eval_corrupted(X_noise)
            
        # Dropout (zeros)
        for pct in [0.01, 0.05, 0.10, 0.20]:
            X_drop = X_test.copy()
            mask = np.random.rand(*X_drop.shape) < pct
            X_drop[mask] = 0
            res[f"dropout_{int(pct*100)}"] = eval_corrupted(X_drop)
            
        # Missing (NaNs)
        for pct in [0.01, 0.05, 0.10]:
            X_miss = X_test.copy()
            mask = np.random.rand(*X_miss.shape) < pct
            X_miss[mask] = np.nan
            try:
                res[f"missing_{int(pct*100)}"] = eval_corrupted(X_miss)
            except:
                res[f"missing_{int(pct*100)}"] = 0.0 # Failed to handle missing
                
        # Dist Shift (Time)
        try:
            m_shift = get_models()[name]
            m_shift.fit(X_ds_train, y_ds_train)
            p_shift = m_shift.predict_proba(X_ds_test)[:, 1]
            res["dist_shift_pr"] = average_precision_score(y_ds_test, p_shift)
        except Exception as e:
            res["dist_shift_pr"] = 0.0
            
        rob_records.append(res)
    pd.DataFrame(rob_records).to_csv(os.path.join(RESULTS_DIR, "robustness_report.csv"), index=False)

    # --- PHASE 4: FRAUD OPERATIONS SIMULATION ---
    print("[PHASE 4] Fraud Operations Simulation...")
    # Because ULB is PCA (V1-V28), we approximate scenarios using distribution percentiles
    best_model_name = max(leakage_records, key=lambda x: x['oof_test_pr_auc'])['model']
    best_model = trained_models[best_model_name]['model']
    best_t = trained_models[best_model_name]['best_t']
    
    fraud_df = df[df[target_col] == 1]
    legit_df = df[df[target_col] == 0]
    
    scenarios = {
        "Legitimate Customer": legit_df.drop(columns=[target_col]).median().to_dict(),
        "Stolen Card (High V4, V11)": fraud_df.drop(columns=[target_col]).quantile(0.75).to_dict(),
        "Mule Account (Low V12, V14)": fraud_df.drop(columns=[target_col]).quantile(0.25).to_dict(),
        "Rapid Transaction Burst": fraud_df.drop(columns=[target_col]).mean().to_dict(),
    }
    
    sim_df = pd.DataFrame(scenarios).T
    sim_df['Amount'] = [50.0, 999.0, 10.0, 2500.0]
    
    # We will compute SHAP
    explainer = None
    if best_model_name in ["LightGBM", "XGBoost", "CatBoost"]:
        explainer = shap.TreeExplainer(best_model)
    elif best_model_name == "ExtraTrees":
        explainer = shap.TreeExplainer(best_model.named_steps['clf'])
        
    probs = best_model.predict_proba(sim_df)[:, 1]
    
    md_out = f"# Fraud Operations Simulation Report\n\n"
    md_out += f"**Model Selected**: {best_model_name} (Threshold: {best_t:.4f})\n\n"
    
    for i, (name, row) in enumerate(sim_df.iterrows()):
        prob = probs[i]
        decision = "BLOCK" if prob >= best_t else "ALLOW"
        
        md_out += f"### Scenario: {name}\n"
        md_out += f"- **Risk Score**: {prob:.4f}\n"
        md_out += f"- **Decision**: **{decision}**\n"
        
        if explainer:
            if best_model_name == "ExtraTrees":
                shap_vals = explainer.shap_values(best_model.named_steps['imputer'].transform(sim_df.iloc[[i]]))
            else:
                shap_vals = explainer.shap_values(sim_df.iloc[[i]])
            
            # extract top 3 features
            if isinstance(shap_vals, list): s_val = shap_vals[1][0]
            else: s_val = shap_vals[0]
            
            top_idx = np.argsort(np.abs(s_val))[-3:][::-1]
            md_out += "- **Top Risk Factors (SHAP)**:\n"
            for idx in top_idx:
                md_out += f"  - `{sim_df.columns[idx]}`: {s_val[idx]:.4f}\n"
        md_out += "\n"
        
    with open(os.path.join(RESULTS_DIR, "fraud_operations_report.md"), "w") as f:
        f.write(md_out)

    # --- PHASE 5: FINAL RANKING ---
    print("[PHASE 5] Final Ranking...")
    final_ranking = []
    
    for lr in leakage_records:
        name = lr['model']
        rr = next(r for r in rob_records if r['model'] == name)
        cr = next(c for c in cal_records if c['model'] == name)
        
        pr_auc = lr['oof_test_pr_auc']
        recall = recall_score(y_test, trained_models[name]['preds_test'], zero_division=0)
        cal = max(0, 1.0 - (cr['brier_raw'] * 10)) # Invert Brier so higher is better
        
        # Average robustness across all corrupted tests
        rob_keys = [k for k in rr.keys() if k not in ['model', 'baseline_pr', 'dist_shift_pr']]
        rob_avg = np.mean([rr[k] for k in rob_keys])
        
        # 40% PR AUC, 30% Recall, 20% Calibration, 10% Robustness
        score = (0.4 * pr_auc) + (0.3 * recall) + (0.2 * cal) + (0.1 * rob_avg)
        
        final_ranking.append({
            "model": name,
            "final_score": float(score),
            "pr_auc_weight_40": float(pr_auc),
            "recall_weight_30": float(recall),
            "calibration_weight_20": float(cal),
            "robustness_weight_10": float(rob_avg)
        })
        
    df_rank = pd.DataFrame(final_ranking).sort_values(by="final_score", ascending=False)
    df_rank.to_csv(os.path.join(RESULTS_DIR, "production_model_ranking.csv"), index=False)
    print(f"[SUCCESS] All phases complete. Artifacts saved in {RESULTS_DIR}")

if __name__ == "__main__":
    run_campaign()
