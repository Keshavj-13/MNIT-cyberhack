import os
import pandas as pd
import requests
from tqdm import tqdm

DATA_DIR = "data/raw"

DATASETS = {
    "transaction": {
        "url": "https://data.mendeley.com/public-files/datasets/89s6f2z5j2/files/5f8b9e6e-1d3f-4e5a-8b1e-7f6e8b5d5d5d/file_download", # Placeholder URL
        "filename": "Synthetic_Multi_Pattern_Banking_Transaction_Dataset.csv",
        "description": "Synthetic Multi Pattern Banking Transaction Dataset (Mendeley)"
    },
    "network": {
        "url": "https://www.unb.ca/cic/datasets/ids-2017.html", # Landing page, direct download usually restricted
        "filename": "CICIDS2017_sample.csv",
        "description": "CIC IDS 2017 (UNB)"
    }
}

def download_file(url, filename):
    local_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(local_path):
        print(f"[INFO] {filename} already exists.")
        return True
    
    print(f"[INFO] Attempting to download {filename} from {url}...")
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        with open(local_path, 'wb') as f, tqdm(
            total=total_size, unit='iB', unit_scale=True, desc=filename
        ) as bar:
            for data in response.iter_content(chunk_size=1024):
                size = f.write(data)
                bar.update(size)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download {filename}: {e}")
        print(f"[ACTION] Please manually download the dataset and place it in {DATA_DIR}")
        print(f"         Target Filename: {filename}")
        if filename == "Synthetic_Multi_Pattern_Banking_Transaction_Dataset.csv":
            print("         Source: https://data.mendeley.com/datasets/89s6f2z5j2/1")
        elif "CICIDS2017" in filename:
            print("         Source: https://www.unb.ca/cic/datasets/ids-2017.html")
        return False

def check_datasets():
    missing = []
    for key, info in DATASETS.items():
        if not os.path.exists(os.path.join(DATA_DIR, info["filename"])):
            missing.append(info)
    
    if not missing:
        print("[SUCCESS] All datasets found.")
        return True
    
    print("[WARNING] Missing datasets detected.")
    for info in missing:
        download_file(info["url"], info["filename"])
    
    # Final check
    still_missing = [i["filename"] for i in DATASETS.values() if not os.path.exists(os.path.join(DATA_DIR, i["filename"]))]
    if still_missing:
        print(f"[CRITICAL] Still missing: {still_missing}")
        return False
    return True

if __name__ == "__main__":
    check_datasets()
