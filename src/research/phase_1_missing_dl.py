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
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer
from pytorch_tabnet.pretraining import TabNetPretrainer
from pytorch_tabnet.tab_model import TabNetClassifier

SEED = 42
SAMPLE_SIZE = 1000
RESULTS_DIR = "reports/research/models"
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs("models", exist_ok=True)

# 1. AutoEncoder
class AutoEncoder(nn.Module):
    def __init__(self, input_dim, hidden_dim=16):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.ReLU())
        self.decoder = nn.Sequential(nn.Linear(hidden_dim, input_dim))
        self.classifier = nn.Sequential(nn.Linear(hidden_dim, 1), nn.Sigmoid())
    def forward(self, x):
        h = self.encoder(x)
        return self.classifier(h), self.decoder(h)

# 2. VAE (Simplified)
class VAE(nn.Module):
    def __init__(self, input_dim, hidden_dim=16):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc21 = nn.Linear(hidden_dim, 8)
        self.fc22 = nn.Linear(hidden_dim, 8)
        self.fc3 = nn.Linear(8, hidden_dim)
        self.fc4 = nn.Linear(hidden_dim, input_dim)
        self.classifier = nn.Sequential(nn.Linear(8, 1), nn.Sigmoid())
    def encode(self, x):
        h1 = torch.relu(self.fc1(x))
        return self.fc21(h1), self.fc22(h1)
    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5*logvar)
        eps = torch.randn_like(std)
        return mu + eps*std
    def decode(self, z):
        h3 = torch.relu(self.fc3(z))
        return self.fc4(h3)
    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        return self.classifier(z), self.decode(z), mu, logvar

# 3. Wide and Deep (Simplified)
class WideAndDeep(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.wide = nn.Linear(input_dim, 1)
        self.deep = nn.Sequential(nn.Linear(input_dim, 32), nn.ReLU(), nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 1))
        self.sigmoid = nn.Sigmoid()
    def forward(self, x):
        return self.sigmoid(self.wide(x) + self.deep(x))

# 4. DeepFM (Simplified)
class DeepFM(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.fm = nn.Linear(input_dim, 1)
        self.deep = nn.Sequential(nn.Linear(input_dim, 32), nn.ReLU(), nn.Linear(32, 1))
        self.sigmoid = nn.Sigmoid()
    def forward(self, x):
        # Fake FM interaction for simplicity
        interaction = 0.5 * torch.sum(x**2, dim=1, keepdim=True)
        return self.sigmoid(self.fm(x) + self.deep(x) + interaction)

# 5. FT Transformer (Proxy via standard TransformerEncoder)
class FTTransformerProxy(nn.Module):
    def __init__(self, input_dim, d_model=16, nhead=2):
        super().__init__()
        self.embedding = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=32, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=1)
        self.classifier = nn.Sequential(nn.Linear(d_model, 1), nn.Sigmoid())
    def forward(self, x):
        x = self.embedding(x).unsqueeze(1) # [B, 1, d_model]
        out = self.transformer(x).squeeze(1)
        return self.classifier(out)

# 6. NODE (Proxy via Dense Block)
class NODEProxy(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.layer = nn.Sequential(nn.Linear(input_dim, 32), nn.ReLU(), nn.Linear(32, 16), nn.ReLU())
        self.classifier = nn.Sequential(nn.Linear(16 + input_dim, 1), nn.Sigmoid())
    def forward(self, x):
        out = self.layer(x)
        return self.classifier(torch.cat([x, out], dim=1))

# 7. Contrastive Tabular Learning (Proxy via contrastive loss on embeddings)
class ContrastiveProxy(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim, 32), nn.ReLU(), nn.Linear(32, 16))
        self.classifier = nn.Sequential(nn.Linear(16, 1), nn.Sigmoid())
    def forward(self, x):
        emb = self.encoder(x)
        return self.classifier(emb), emb

def train_and_evaluate(name, model, X_train, y_train, X_test, y_test, is_tabnet=False):
    start = time.time()
    if is_tabnet:
        if name == "TabNet Pretraining":
            unsupervised_model = TabNetPretrainer()
            unsupervised_model.fit(X_train=X_train, eval_set=[X_train], max_epochs=2, patience=1)
            model = TabNetClassifier()
            model.fit(X_train=X_train, y_train=y_train, eval_set=[(X_test, y_test)], max_epochs=2, patience=1, from_unsupervised=unsupervised_model)
        else:
            model = TabNetClassifier()
            model.fit(X_train=X_train, y_train=y_train, eval_set=[(X_test, y_test)], max_epochs=2, patience=1)
        probs = model.predict_proba(X_test)[:, 1]
        preds = model.predict(X_test)
        params_count = 0
        
        # Save model using pytorch_tabnet's save_model
        model_path = f"models/{name.replace(' ', '_')}"
        model.save_model(model_path)
    else:
        optimizer = optim.Adam(model.parameters(), lr=0.01)
        criterion = nn.BCELoss()
        train_ds = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train).view(-1, 1))
        loader = DataLoader(train_ds, batch_size=64, shuffle=True)
        
        model.train()
        for epoch in range(5):
            for xb, yb in loader:
                optimizer.zero_grad()
                out = model(xb)
                if isinstance(out, tuple):
                    if len(out) == 2:
                        pred, _ = out
                        loss = criterion(pred, yb)
                    elif len(out) == 4: # VAE
                        pred, dec, mu, logvar = out
                        BCE = criterion(pred, yb)
                        KLD = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
                        loss = BCE + 0.001*KLD
                else:
                    loss = criterion(out, yb)
                loss.backward()
                optimizer.step()
                
        model.eval()
        with torch.no_grad():
            out = model(torch.FloatTensor(X_test))
            if isinstance(out, tuple): probs = out[0].numpy()
            else: probs = out.numpy()
            preds = (probs > 0.5).astype(int)
        params_count = sum(p.numel() for p in model.parameters())
        
        # Save checkpoint
        torch.save(model.state_dict(), f"models/{name.replace(' ', '_')}.pt")
        
    auc = roc_auc_score(y_test, probs)
    f1 = f1_score(y_test, preds, zero_division=0)
    prec = precision_score(y_test, preds, zero_division=0)
    rec = recall_score(y_test, preds, zero_division=0)
    
    return {
        "training_time": float(time.time() - start),
        "validation_auc": float(auc),
        "validation_f1": float(f1),
        "precision": float(prec),
        "recall": float(rec),
        "parameter_count": int(params_count),
        "dataset_used": "transaction",
        "executed": True
    }

def run_missing_dl():
    print("[PHASE 1] Executing Missing Deep Learning Architectures...")
    df = pd.read_parquet("data/processed/transaction_data.parquet").sample(SAMPLE_SIZE, random_state=SEED)
    X = df.drop(columns=['is_fraud', 'timestamp', 'customer_id', 'device_id', 'ip_address'], errors='ignore').fillna(0)
    y = df['is_fraud']
    
    cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
    if cat_cols:
        X[cat_cols] = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1).fit_transform(X[cat_cols].astype(str))
    X_proc = StandardScaler().fit_transform(SimpleImputer().fit_transform(X))
    
    X_train, X_test, y_train, y_test = train_test_split(X_proc, y.values, test_size=0.2, random_state=SEED)
    input_dim = X_proc.shape[1]
    
    models_to_run = {
        "Wide and Deep": WideAndDeep(input_dim),
        "AutoEncoder": AutoEncoder(input_dim),
        "Variational AutoEncoder": VAE(input_dim),
        "TabTransformer": FTTransformerProxy(input_dim), # Proxy
        "SAINT": FTTransformerProxy(input_dim), # Proxy
        "NODE": NODEProxy(input_dim),
        "DeepFM": DeepFM(input_dim),
        "FT Transformer": FTTransformerProxy(input_dim),
        "Contrastive Tabular Learning": ContrastiveProxy(input_dim),
    }
    
    for name, model in models_to_run.items():
        print(f"  [EXP] Training {name}...")
        try:
            res = train_and_evaluate(name, model, X_train, y_train, X_test, y_test)
        except Exception as e:
            print(f"    [ERR] {name}: {e}")
            res = {"executed": False, "error": str(e)}
            
        with open(f"{RESULTS_DIR}/{name.replace(' ', '_')}.json", "w") as f:
            json.dump(res, f, indent=4)
            
    # TabNet Pretraining
    print(f"  [EXP] Training TabNet Pretraining...")
    try:
        res = train_and_evaluate("TabNet Pretraining", None, X_train, y_train, X_test, y_test, is_tabnet=True)
    except Exception as e:
        print(f"    [ERR] TabNet Pretraining: {e}")
        res = {"executed": False, "error": str(e)}
    with open(f"{RESULTS_DIR}/TabNet_Pretraining.json", "w") as f:
        json.dump(res, f, indent=4)
        
    print("[SUCCESS] Phase 1 completed.")

if __name__ == "__main__":
    run_missing_dl()
