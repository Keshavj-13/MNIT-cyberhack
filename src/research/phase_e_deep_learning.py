import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np
import time
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer
from pytorch_tabnet.tab_model import TabNetClassifier

# Config
SEED = 42
SAMPLE_SIZE = 5000
RESULTS_DIR = "reports/research/benchmarks"
os.makedirs(RESULTS_DIR, exist_ok=True)

# MLP variants
class MLP(nn.Module):
    def __init__(self, input_dim, hidden_dims=[64, 32], dropout=0.2):
        super(MLP, self).__init__()
        layers = []
        last_dim = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(last_dim, h))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            last_dim = h
        layers.append(nn.Linear(last_dim, 1))
        layers.append(nn.Sigmoid())
        self.net = nn.Sequential(*layers)
    def forward(self, x): return self.net(x)

class ResidualMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim=64):
        super(ResidualMLP, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.res_block = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )
        self.fc2 = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = x + self.res_block(x)
        return self.sigmoid(self.fc2(x))

def run_dl_research():
    tasks = [
        ("transaction", "data/processed/transaction_data.parquet", "is_fraud"),
        ("network", "data/processed/network_data.parquet", "Label_Encoded")
    ]
    
    for task_name, path, target in tasks:
        print(f"[PHASE E] Deep Learning Research for {task_name}...")
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
        X_proc = StandardScaler().fit_transform(SimpleImputer().fit_transform(X))
        
        X_train, X_test, y_train, y_test = train_test_split(X_proc, y.values, test_size=0.2, random_state=SEED)
        
        results = []
        
        # Architectures
        models = {
            "MLP_Small": MLP(X_proc.shape[1], [32, 16]),
            "MLP_Medium": MLP(X_proc.shape[1], [64, 32]),
            "MLP_Deep": MLP(X_proc.shape[1], [128, 64, 32, 16]),
            "ResidualMLP": ResidualMLP(X_proc.shape[1]),
        }
        
        for name, model in models.items():
            print(f"  [EXP] {name}")
            start = time.time()
            criterion = nn.BCELoss()
            optimizer = optim.Adam(model.parameters(), lr=0.001)
            train_ds = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train).view(-1, 1))
            loader = DataLoader(train_ds, batch_size=32, shuffle=True)
            
            model.train()
            for epoch in range(10):
                for xb, yb in loader:
                    optimizer.zero_grad()
                    loss = criterion(model(xb), yb)
                    loss.backward()
                    optimizer.step()
            
            model.eval()
            with torch.no_grad():
                probs = model(torch.FloatTensor(X_test)).numpy()
                auc = roc_auc_score(y_test, probs)
            
            results.append({
                "model": name, "roc_auc": float(auc), 
                "train_time": float(time.time()-start),
                "params": sum(p.numel() for p in model.parameters())
            })
            
        # TabNet
        print("  [EXP] TabNet")
        start = time.time()
        tabnet = TabNetClassifier(verbose=0)
        tabnet.fit(X_train, y_train, max_epochs=10)
        probs = tabnet.predict_proba(X_test)[:, 1]
        results.append({
            "model": "TabNet", "roc_auc": float(roc_auc_score(y_test, probs)),
            "train_time": float(time.time()-start),
            "params": 0 # complex to extract
        })

        res_df = pd.DataFrame(results)
        res_df.to_csv(f"{RESULTS_DIR}/{task_name}_dl_leaderboard.csv", index=False)
        with open(f"{RESULTS_DIR}/{task_name}_dl_leaderboard.md", "w") as f:
            f.write(f"# Deep Learning Leaderboard: {task_name}\n\n")
            f.write(res_df.sort_values("roc_auc", ascending=False).to_markdown(index=False))

    print(f"[SUCCESS] Phase E completed.")

if __name__ == "__main__":
    run_dl_research()
