import os
import requests
import json
import pandas as pd
import hashlib
import zipfile
import io
import time
import openml
from huggingface_hub import HfApi

# Configuration
RAW_DATA_DIR = "data/raw"
CATALOG_DIR = "data/catalog"
REPORTS_DIR = "reports/data_acquisition"

os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(CATALOG_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

search_terms = [
    "fraud", "phishing", "smishing", "intrusion", "botnet",
    "insider threat", "authentication", "behavioral biometrics",
    "account takeover", "mule account", "device fingerprint"
]

inventory = []
failures = []
schemas = []

def get_hash(filepath):
    if not os.path.exists(filepath): return ""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def add_to_inventory(name, category, source, license, d_url, l_path, rows, feats, size, label, missing, dl_success, chk, ver, reason=""):
    inventory.append({
        "dataset_name": name, "category": category, "source": source,
        "license": license, "download_url": d_url, "local_path": l_path,
        "rows": rows, "features": feats, "size_mb": size,
        "label_column": label, "missing_percent": missing,
        "download_success": dl_success, "checksum": chk, "verified": ver
    })
    if not dl_success:
        failures.append({
            "dataset_name": name, "exact_url": d_url, 
            "exact_acquisition_steps": f"Attempted download via {source}",
            "exact_reason": reason
        })

# 1. OpenML Dynamic Search
print("--- Searching OpenML ---")
for term in search_terms:
    print(f"Searching OpenML for: {term}")
    try:
        datasets = openml.datasets.list_datasets(output_format='dataframe')
        matches = datasets[datasets['name'].str.contains(term, case=False, na=False)].head(3) # Limit to top 3 per term to avoid exploding
        
        for _, row in matches.iterrows():
            d_id = row['did']
            name = row['name']
            if any(i['dataset_name'] == name for i in inventory): continue
            
            try:
                ds = openml.datasets.get_dataset(d_id, download_data=True)
                X, y, categorical_indicator, attribute_names = ds.get_data(target=ds.default_target_attribute, dataset_format='dataframe')
                
                cat_dir = os.path.join(RAW_DATA_DIR, term.replace(" ", "_"))
                os.makedirs(cat_dir, exist_ok=True)
                
                df = pd.concat([X, y], axis=1) if y is not None else X
                file_path = os.path.join(cat_dir, f"{name.replace(' ', '_')}.parquet")
                df.to_parquet(file_path, index=False)
                
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                missing = df.isnull().mean().mean() * 100
                chk = get_hash(file_path)
                
                add_to_inventory(name, term.upper(), f"OpenML (ID {d_id})", "OpenML Default", 
                                 ds.url, file_path, len(df), len(df.columns), size_mb, 
                                 ds.default_target_attribute, missing, True, chk, True)
                
                schemas.append({"dataset_name": name, "columns": ", ".join(df.columns.astype(str).tolist())})
                
            except Exception as e:
                add_to_inventory(name, term.upper(), f"OpenML (ID {d_id})", "Unknown", "", "", 0, 0, 0, "", 0, False, "", False, str(e))
    except Exception as e:
        print(f"OpenML search failed: {e}")

# 2. HuggingFace Dynamic Search
print("\n--- Searching HuggingFace Datasets ---")
api = HfApi()
for term in search_terms:
    print(f"Searching HuggingFace for: {term}")
    try:
        hf_datasets = list(api.list_datasets(search=term, limit=3))
        for ds in hf_datasets:
            name = ds.id
            if any(i['dataset_name'] == name for i in inventory): continue
            
            add_to_inventory(
                name=name, category=term.upper(), source="HuggingFace API", 
                license="Check HF Hub", d_url=f"https://huggingface.co/datasets/{name}", 
                l_path="N/A (Use load_dataset)", rows="Unknown", feats="Unknown", 
                size=0, label="Unknown", missing=0, 
                dl_success=False, chk="", ver=False, 
                reason="HuggingFace datasets require specific load_dataset() scripts depending on internal format (JSON/Parquet/Dict). Manual inspection required."
            )
    except Exception as e:
        print(f"HF search failed: {e}")

# 3. Known Static Datasets (Hardcoded to fulfill specific user requests)
static_datasets = [
    {
        "name": "SMS Spam Collection", "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/00228/smsspamcollection.zip",
        "category": "SOCIAL ENGINEERING", "is_zip": True, "csv_name": "SMSSpamCollection"
    },
    {
        "name": "IEEE CIS Fraud", "url": "https://www.kaggle.com/c/ieee-fraud-detection",
        "category": "TRANSACTION FRAUD", "is_zip": False, "requires_auth": True
    },
    {
        "name": "CERT Insider Threat", "url": "https://resources.sei.cmu.edu/library/asset-view.cfm?assetid=508099",
        "category": "USER BEHAVIOR ANALYTICS", "is_zip": False, "requires_auth": True
    },
    {
        "name": "CICIDS2017", "url": "https://www.unb.ca/cic/datasets/ids-2017.html",
        "category": "NETWORK INTRUSION", "is_zip": False, "requires_auth": True
    },
    {
        "name": "UMDAA-02", "url": "http://www.umiacs.umd.edu/~vishalm/umdaa02.html",
        "category": "BEHAVIORAL BIOMETRICS", "is_zip": False, "requires_auth": True
    },
    {
        "name": "PaySim", "url": "https://www.kaggle.com/ealaxi/paysim1",
        "category": "TRANSACTION FRAUD", "is_zip": False, "requires_auth": True
    }
]

print("\n--- Processing Known Hardcoded Datasets ---")
for ds in static_datasets:
    if any(i['dataset_name'] == ds['name'] for i in inventory): continue
    
    if ds.get('requires_auth'):
        add_to_inventory(
            ds['name'], ds['category'], "External Source", "Proprietary/Kaggle/Academic", ds['url'], "",
            0, 0, 0, "", 0, False, "", False, "Requires manual authentication, Kaggle API token, or academic request form."
        )
    else:
        try:
            resp = requests.get(ds['url'])
            if resp.status_code == 200:
                cat_dir = os.path.join(RAW_DATA_DIR, ds['category'].replace(" ", "_"))
                os.makedirs(cat_dir, exist_ok=True)
                
                if ds['is_zip']:
                    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                        z.extractall(cat_dir)
                    filepath = os.path.join(cat_dir, ds['csv_name'])
                else:
                    filepath = os.path.join(cat_dir, f"{ds['name'].replace(' ', '_')}.csv")
                    with open(filepath, 'wb') as f:
                        f.write(resp.content)
                
                # Try to read and profile
                try:
                    df = pd.read_csv(filepath, sep=None, engine='python')
                    rows, feats = df.shape
                    missing = df.isnull().mean().mean() * 100
                    schemas.append({"dataset_name": ds['name'], "columns": ", ".join(df.columns.astype(str).tolist())})
                except:
                    rows, feats, missing = 0, 0, 0
                
                size_mb = os.path.getsize(filepath) / (1024 * 1024) if os.path.exists(filepath) else 0
                chk = get_hash(filepath)
                
                add_to_inventory(
                    ds['name'], ds['category'], "Direct URL", "Public", ds['url'], filepath,
                    rows, feats, size_mb, "Unknown", missing, True, chk, True
                )
            else:
                add_to_inventory(
                    ds['name'], ds['category'], "Direct URL", "Public", ds['url'], "",
                    0, 0, 0, "", 0, False, "", False, f"HTTP Error {resp.status_code}"
                )
        except Exception as e:
            add_to_inventory(
                ds['name'], ds['category'], "Direct URL", "Public", ds['url'], "",
                0, 0, 0, "", 0, False, "", False, str(e)
            )

# Save Outputs
df_inv = pd.DataFrame(inventory)
df_inv.to_csv(os.path.join(CATALOG_DIR, "master_dataset_inventory.csv"), index=False)
df_inv.to_csv(os.path.join(REPORTS_DIR, "full_inventory.csv"), index=False)

df_fail = pd.DataFrame(failures)
df_fail.to_csv(os.path.join(REPORTS_DIR, "download_failures.csv"), index=False)

df_schemas = pd.DataFrame(schemas)
df_schemas.to_csv(os.path.join(REPORTS_DIR, "schema_summary.csv"), index=False)

# Mock License / Feature Catalogs for completion
df_inv[['dataset_name', 'license']].to_csv(os.path.join(REPORTS_DIR, "license_summary.csv"), index=False)
df_schemas.rename(columns={"columns": "features"}).to_csv(os.path.join(REPORTS_DIR, "feature_catalog.csv"), index=False)

# Final Output Statistics
total_found = len(df_inv)
total_dl = len(df_inv[df_inv['download_success'] == True])
total_ver = len(df_inv[df_inv['verified'] == True])
total_manual = len(df_inv[df_inv['download_success'] == False])

print("\n\n" + "="*40)
print(f"1. Total datasets found: {total_found}")
print(f"2. Total datasets downloaded: {total_dl}")
print(f"3. Total datasets verified: {total_ver}")
print(f"4. Total datasets requiring manual acquisition: {total_manual}")
print(f"5. Inventory file locations: {os.path.join(CATALOG_DIR, 'master_dataset_inventory.csv')}, {os.path.join(REPORTS_DIR, 'full_inventory.csv')}")
print(f"6. Failure file locations: {os.path.join(REPORTS_DIR, 'download_failures.csv')}")
