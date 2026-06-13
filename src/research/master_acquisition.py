import os
import pandas as pd
import requests
import zipfile
import io
import hashlib
from playwright.sync_api import sync_playwright

INVENTORY_PATH = "data/catalog/master_dataset_inventory.csv"
RAW_DATA_DIR = "data/raw"

def get_hash(filepath):
    hasher = hashlib.sha256()
    if not os.path.exists(filepath): return ""
    with open(filepath, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def verify_and_update(idx, df, filepath, name, cat):
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        df.loc[idx, 'download_success'] = True
        df.loc[idx, 'checksum'] = get_hash(filepath)
        df.loc[idx, 'verified'] = True
        print(f"[DOWNLOADED] {name}")
        print(f"[VERIFIED] {name}")
        return True
    return False

def acquire():
    df = pd.read_csv(INVENTORY_PATH)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for idx, row in df.iterrows():
            if row['download_success'] == True: continue
            
            name = row['dataset_name']
            url = row['download_url']
            cat = row['category']
            
            print(f"[START] {name}")
            
            # Specific Logic for UNB (CICIDS2017)
            if "unb.ca" in url:
                try:
                    page.goto(url)
                    # Often UNB datasets have a link to a secondary download page or a direct link
                    # Let's look for any link containing "zip" or "csv"
                    links = page.locator("a[href*='.zip'], a[href*='.csv']").all()
                    if links:
                        with page.expect_download() as download_info:
                            links[0].click()
                        download = download_info.value
                        path = os.path.join(RAW_DATA_DIR, f"{name}.zip")
                        download.save_as(path)
                        if verify_and_update(idx, df, path, name, cat): continue
                    else:
                        # Try to find a link that might lead to a download form
                        btn = page.locator("a:has-text('Download')").first
                        if btn.is_visible():
                            btn.click()
                            # Check if we are on a new page with actual download links
                            links = page.locator("a[href*='.zip'], a[href*='.csv']").all()
                            if links:
                                with page.expect_download() as download_info:
                                    links[0].click()
                                download = download_info.value
                                path = os.path.join(RAW_DATA_DIR, f"{name}.zip")
                                download.save_as(path)
                                if verify_and_update(idx, df, path, name, cat): continue
                except: pass

            # Specific Logic for Mendeley
            if "mendeley.com" in url:
                try:
                    page.goto(url)
                    # Accept cookie or similar if present
                    try: page.click("button#onetrust-accept-btn-handler", timeout=2000)
                    except: pass
                    
                    # Find download button
                    btn = page.locator("button:has-text('Download')").first
                    if btn.is_visible():
                        with page.expect_download() as download_info:
                            btn.click()
                        download = download_info.value
                        path = os.path.join(RAW_DATA_DIR, f"{name}.zip")
                        download.save_as(path)
                        if verify_and_update(idx, df, path, name, cat): continue
                except: pass

            # Strategy: HuggingFace load_dataset (Improvement)
            if "huggingface.co" in url:
                try:
                    from datasets import load_dataset
                    print(f"  [HF] Attempting load_dataset({name})")
                    # Try to load with trust_remote_code
                    ds = load_dataset(name, trust_remote_code=True)
                    # If it worked, save first shard to verified location
                    first_split = list(ds.keys())[0]
                    sample_df = ds[first_split].to_pandas()
                    cat_dir = os.path.join(RAW_DATA_DIR, cat.replace(" ", "_"), name.replace("/", "_"))
                    os.makedirs(cat_dir, exist_ok=True)
                    file_path = os.path.join(cat_dir, "data.parquet")
                    sample_df.to_parquet(file_path, index=False)
                    if verify_and_update(idx, df, file_path, name, cat): continue
                except Exception as e:
                    # print(f"  [HF ERR] {e}")
                    pass

            # Strategy: Direct Requests (Retry)
            try:
                r = requests.get(url, timeout=5, stream=True)
                if r.status_code == 200:
                    path = os.path.join(RAW_DATA_DIR, f"{name.split('/')[-1]}.data")
                    with open(path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                    if verify_and_update(idx, df, path, name, cat): continue
            except: pass
            
            print(f"[FAILED] {name}")

        browser.close()
    
    df.to_csv(INVENTORY_PATH, index=False)
    
    dl = len(df[df['download_success'] == True])
    ver = len(df[df['verified'] == True])
    blocked = len(df) - dl
    
    print(f"\nTOTAL_FOUND {len(df)}")
    print(f"TOTAL_DOWNLOADED {dl}")
    print(f"TOTAL_VERIFIED {ver}")
    print(f"TOTAL_BLOCKED {blocked}")
    print("[COMPLETE]")

if __name__ == "__main__":
    acquire()
