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
from sklearn.preprocessing import StandardScaler

# Simple MLP architectures
class MLP(nn.Module):
    def __init__(self, input_dim, hidden_dims=[64, 32], output_dim=1):
        super(MLP, self).__init__()
        layers = []
        last_dim = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(last_dim, h))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.2))
            last_dim = h
        layers.append(nn.Linear(last_dim, output_dim))
        layers.append(nn.Sigmoid())
        self.net = nn.Sequential(*layers)
        
    def forward(self, x):
        return self.net(x)

class DeepLearningBenchmarker:
    def __init__(self, data_path, target_col, task_name):
        self.df = pd.read_parquet(data_path)
        self.target = target_col
        self.task_name = task_name
        self.X = self.df.drop(columns=[self.target, 'timestamp', 'customer_id', 'device_id', 'ip_address', 'Label'], errors='ignore').fillna(0)
        self.y = self.df[self.target]
        
        if task_name == "network" and "Label_Encoded" in self.target:
             self.y = (self.df[target] != 0).astype(int)
             
        self.scaler = StandardScaler()
        self.X_scaled = self.scaler.fit_transform(self.X)
        
        self.results_dir = "reports/research/benchmarks"
        os.makedirs(self.results_dir, exist_ok=True)

    def train_evaluate(self, model, X_train, y_train, X_test, y_test, epochs=10):
        criterion = nn.BCELoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        
        train_ds = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train).view(-1, 1))
        train_loader = DataLoader(train_ds, batch_size=64, shuffle=True)
        
        model.train()
        for epoch in range(epochs):
            for xb, yb in train_loader:
                optimizer.zero_grad()
                pred = model(xb)
                loss = criterion(pred, yb)
                loss.backward()
                optimizer.step()
        
        model.eval()
        with torch.no_grad():
            preds = model(torch.FloatTensor(X_test)).numpy()
            auc = roc_auc_score(y_test, preds)
        return auc

    def run_benchmark(self):
        print(f"[RESEARCH] Starting Deep Learning Benchmark for {self.task_name}...")
        results = []
        
        X_train, X_test, y_train, y_test = train_test_split(self.X_scaled, self.y.values, test_size=0.2, random_state=42)
        
        architectures = {
            "MLP_Small": MLP(self.X.shape[1], [32, 16]),
            "MLP_Medium": MLP(self.X.shape[1], [64, 32]),
            "MLP_Deep": MLP(self.X.shape[1], [128, 64, 32, 16])
        }
        
        for name, model in architectures.items():
            print(f"  [EXP] DL Model: {name}")
            start_time = time.time()
            try:
                auc = self.train_evaluate(model, X_train, y_train, X_test, y_test)
                duration = time.time() - start_time
                results.append({
                    "model": name,
                    "roc_auc": float(auc),
                    "duration": float(duration)
                })
            except Exception as e:
                print(f"    [ERROR] {e}")

        output_path = os.path.join(self.results_dir, f"{self.task_name}_deep_learning.json")
        with open(output_path, "w") as f:
            json.dump(results, f, indent=4)

if __name__ == "__main__":
    tasks = [
        ("transaction", "data/processed/transaction_data.parquet", "is_fraud"),
        ("network", "data/processed/network_data.parquet", "Label_Encoded")
    ]
    
    for name, path, target in tasks:
        benchmarker = DeepLearningBenchmarker(path, target, name)
        benchmarker.run_benchmark()
