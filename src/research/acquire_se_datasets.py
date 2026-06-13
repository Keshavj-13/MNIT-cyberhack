import os
import requests
import zipfile
import io
import pandas as pd
from scipy.io import arff
import hashlib

DATA_DIR = "data/raw/se_datasets"
INVENTORY_FILE = "reports/research/dataset_inventory.csv"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("reports/research", exist_ok=True)

datasets = []

def get_hash(filepath):
    if not os.path.exists(filepath): return ""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def download_sms_spam():
    print("[INFO] Downloading SMS Spam Collection...")
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00228/smsspamcollection.zip"
    resp = requests.get(url)
    if resp.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            z.extractall(DATA_DIR)
        
        filepath = os.path.join(DATA_DIR, "SMSSpamCollection")
        df = pd.read_csv(filepath, sep='\t', header=None, names=['label', 'message'])
        df.to_csv(os.path.join(DATA_DIR, "sms_spam.csv"), index=False)
        
        datasets.append({
            "dataset_name": "SMS Spam Collection",
            "source": url,
            "license": "Public",
            "rows": len(df),
            "features": 1,
            "target_variable": "label",
            "missing_percent": df.isnull().mean().mean() * 100,
            "social_engineering_score": 10,
            "fraud_score": 4,
            "ato_score": 2,
            "device_score": 0,
            "behavior_score": 2,
            "network_score": 0,
            "overall_score": 8
        })
        print("[SUCCESS] SMS Spam Collection downloaded and parsed.")
    else:
        print("[ERROR] Failed to download SMS Spam.")

def download_phishing():
    print("[INFO] Downloading Phishing Websites Dataset...")
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00327/Training%20Dataset.arff"
    filepath = os.path.join(DATA_DIR, "phishing.arff")
    resp = requests.get(url)
    if resp.status_code == 200:
        with open(filepath, 'wb') as f:
            f.write(resp.content)
            
        try:
            data, meta = arff.loadarff(filepath)
            df = pd.DataFrame(data)
            # Decode byte strings to normal strings/ints
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].str.decode('utf-8').astype(int)
                    
            df.to_csv(os.path.join(DATA_DIR, "phishing.csv"), index=False)
            
            datasets.append({
                "dataset_name": "Phishing Websites",
                "source": url,
                "license": "Public",
                "rows": len(df),
                "features": len(df.columns) - 1,
                "target_variable": "Result",
                "missing_percent": df.isnull().mean().mean() * 100,
                "social_engineering_score": 9,
                "fraud_score": 5,
                "ato_score": 6,
                "device_score": 0,
                "behavior_score": 0,
                "network_score": 3,
                "overall_score": 7
            })
            print("[SUCCESS] Phishing dataset downloaded and parsed.")
        except Exception as e:
            print(f"[ERROR] Failed to parse ARFF: {e}")
    else:
        print("[ERROR] Failed to download Phishing dataset.")

if __name__ == "__main__":
    download_sms_spam()
    download_phishing()
    
    if datasets:
        df_inv = pd.DataFrame(datasets)
        # Append if exists
        if os.path.exists(INVENTORY_FILE):
            existing = pd.read_csv(INVENTORY_FILE)
            df_inv = pd.concat([existing, df_inv]).drop_duplicates(subset=['dataset_name'], keep='last')
        df_inv.sort_values(by="overall_score", ascending=False, inplace=True)
        df_inv.to_csv(INVENTORY_FILE, index=False)
        print(f"[INFO] Inventory updated at {INVENTORY_FILE}")
