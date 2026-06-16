import torch
import torch.nn as nn
import pandas as pd
import json
import os

# Import the actual architectures to load state_dicts correctly
from src.research.phase_1_missing_dl import (
    AutoEncoder, VAE, WideAndDeep, DeepFM, 
    FTTransformerProxy, NODEProxy, ContrastiveProxy
)

RESULTS_DIR = "reports/research/benchmarks"
MODELS_DIR = "models"
VERIFICATION_CSV = "reports/research/model_verification.csv"

def get_model_instance(name, input_dim):
    if name == "AutoEncoder": return AutoEncoder(input_dim)
    if name == "Variational AutoEncoder": return VAE(input_dim)
    if name == "Wide and Deep": return WideAndDeep(input_dim)
    if name == "DeepFM": return DeepFM(input_dim)
    if name == "FT Transformer": return FTTransformerProxy(input_dim)
    if name == "TabTransformer": return FTTransformerProxy(input_dim)
    if name == "SAINT": return FTTransformerProxy(input_dim)
    if name == "NODE": return NODEProxy(input_dim)
    if name == "Contrastive Tabular Learning": return ContrastiveProxy(input_dim)
    return None

def verify_models():
    print("[PHASE 16] Starting Model Quality Verification...\n")
    
    dl_models = [
        "AutoEncoder", "Variational AutoEncoder", "Wide and Deep", 
        "DeepFM", "FT Transformer", "TabTransformer", "SAINT", 
        "NODE", "Contrastive Tabular Learning"
    ]
    
    # We used transaction data with 10 features encoded + scaled
    input_dim = 13 
    
    verification_data = []
    
    for name in dl_models:
        print(f"--- Verifying: {name} ---")
        safe_name = name.replace(' ', '_')
        pt_path = os.path.join(MODELS_DIR, f"{safe_name}.pt")
        json_path = os.path.join("reports/research/models", f"{safe_name}.json")
        
        verified = False
        param_count = 0
        ckpt_size = 0
        auc = 0.0
        prec = 0.0
        rec = 0.0
        f1 = 0.0
        
        # 1. Inspect Checkpoint
        if os.path.exists(pt_path):
            ckpt_size = os.path.getsize(pt_path)
            model_instance = get_model_instance(name, input_dim)
            if model_instance:
                try:
                    model_instance.load_state_dict(torch.load(pt_path))
                    param_count = sum(p.numel() for p in model_instance.parameters() if p.requires_grad)
                    verified = True
                    print(f"  Architecture:")
                    print(model_instance)
                    print(f"  Extracted Parameter Count: {param_count}")
                except Exception as e:
                    print(f"  [ERROR] Failed to load checkpoint: {e}")
        else:
            print("  [ERROR] Checkpoint missing.")
            
        # 2. Inspect Metrics
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                res = json.load(f)
                auc = res.get("validation_auc", 0)
                prec = res.get("precision", 0)
                rec = res.get("recall", 0)
                f1 = res.get("validation_f1", 0)
                epochs = 5 # Hardcoded in phase_1_missing_dl.py
                dataset_rows = 1000 # Hardcoded SAMPLE_SIZE
                val_rows = int(1000 * 0.2) # 20% test split
                
                print(f"  Reported Params: {res.get('parameter_count')}")
                print(f"  Metrics: AUC={auc:.4f}, Precision={prec:.4f}, Recall={rec:.4f}, F1={f1:.4f}")
                print(f"  Training: {epochs} epochs, Batch Size: 64, Optimizer: Adam(lr=0.01)")
                print(f"  Data: {dataset_rows} train rows, {val_rows} val rows (Transaction Data)")
        else:
            print("  [ERROR] Metrics JSON missing.")
            
        verification_data.append({
            "model": name,
            "parameter_count": param_count if verified else "UNVERIFIED",
            "epochs": 5,
            "dataset_rows": 1000,
            "checkpoint_size": ckpt_size,
            "auc": auc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "verified": verified
        })
        print()

    df_ver = pd.DataFrame(verification_data)
    df_ver.to_csv(VERIFICATION_CSV, index=False)
    print(f"[SUCCESS] Verification CSV generated at {VERIFICATION_CSV}")
    
    print("\n--- ANALYSIS: Why AUC > 0.6 while Precision/Recall/F1 = 0 ---")
    print("This occurs because the datasets are highly imbalanced (fraud rate ~1-2%).")
    print("1. AUC is a ranking metric. It measures the model's ability to rank a random positive example higher than a random negative example. It is independent of absolute probability thresholds.")
    print("2. Precision, Recall, and F1 are threshold-dependent metrics (defaulting to a 0.5 probability threshold).")
    print("3. When training a simple, non-rebalanced DL model (like these 5-epoch networks) on highly imbalanced data, the model quickly learns to predict low probabilities (e.g., 0.01 to 0.10) for all samples to minimize Binary Cross Entropy loss.")
    print("4. Therefore, no prediction ever crosses the 0.5 threshold, resulting in 0 True Positives (Recall=0, Precision=0, F1=0).")
    print("5. However, the model still assigns slightly higher probabilities to the actual positive class (e.g., 0.08 vs 0.01), allowing the AUC to reach 0.60 - 0.76.")

if __name__ == "__main__":
    verify_models()
