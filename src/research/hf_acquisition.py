import os
import pandas as pd
from datasets import load_dataset
import hashlib

INVENTORY_PATH = "data/catalog/master_dataset_inventory.csv"
RAW_DATA_DIR = "data/raw"

def get_hash(filepath):
    if not os.path.exists(filepath): return ""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def process_hf_datasets():
    df = pd.read_csv(INVENTORY_PATH)
    hf_mask = (df['source'] == "HuggingFace API") & (df['download_success'] == False)
    hf_datasets = df[hf_mask].copy()
    
    print(f"[INFO] Found {len(hf_datasets)} HuggingFace datasets to process.")
    
    for idx, row in hf_datasets.iterrows():
        name = row['dataset_name']
        cat = row['category']
        print(f"  [HF] Processing {name}...")
        
        try:
            # Load dataset (this downloads it to local cache)
            ds = load_dataset(name, trust_remote_code=True)
            
            # Save a sample to our data/raw to verify existence
            cat_dir = os.path.join(RAW_DATA_DIR, cat.replace(" ", "_"), name.replace("/", "_"))
            os.makedirs(cat_dir, exist_ok=True)
            
            # Convert first split to pandas and save as parquet
            first_split = list(ds.keys())[0]
            sample_df = ds[first_split].to_pandas()
            file_path = os.path.join(cat_dir, "data.parquet")
            sample_df.to_parquet(file_path, index=False)
            
            rows, feats = sample_df.shape
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            missing = sample_df.isnull().mean().mean() * 100
            chk = get_hash(file_path)
            
            # Update main dataframe
            df.loc[idx, 'local_path'] = file_path
            df.loc[idx, 'rows'] = rows
            df.loc[idx, 'features'] = feats
            df.loc[idx, 'size_mb'] = size_mb
            df.loc[idx, 'missing_percent'] = missing
            df.loc[idx, 'download_success'] = True
            df.loc[idx, 'checksum'] = chk
            df.loc[idx, 'verified'] = True
            
            print(f"    [SUCCESS] {name} downloaded and verified.")
            
        except Exception as e:
            print(f"    [ERROR] Failed {name}: {e}")
            
    df.to_csv(INVENTORY_PATH, index=False)
    print(f"[INFO] Inventory updated with HF datasets.")

if __name__ == "__main__":
    process_hf_datasets()
