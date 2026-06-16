import os
import json
import requests
import zipfile
import pandas as pd
import hashlib
from datetime import datetime
import traceback

DATASETS_ROOT = "datasets"
RAW_DIR = os.path.join(DATASETS_ROOT, "raw")
REPORTS_DIR = "reports/dataset_validation"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

DATASET_INFO = {
    "sms_spam_collection": {
        "url": "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip",
        "format": "TXT/CSV",
        "license": "CC BY 4.0",
        "citation": "Almeida, T.A., Gómez Hidalgo, J.M., Yamakami, A. Contributions to the Study of SMS Spam Filtering: New Collection and Results. Proceedings of the 2011 ACM Symposium on Document Engineering (DOCENG'11), Mountain View, CA, USA, 2011.",
        "paper_url": "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip" # Actually points to zip, but user had it
    },
    "phishing_websites": {
        "url": "https://archive.ics.uci.edu/static/public/327/phishing+websites.zip",
        "format": "ARFF",
        "license": "Open Access",
        "citation": "Mohammad, R. M., Thabtah, F., & McCluskey, L. (2012). An assessment of features related to phishing websites using an automated technique. International Journal of Information Security and Intelligence, 1(2), 27-48.",
        "paper_url": "https://eprints.hud.ac.uk/id/eprint/19204/1/MohammadPhishing14.pdf"
    },
    "cmu_keystroke": {
        "url": "https://www.cs.cmu.edu/~keystroke/DSL-StrongPasswordData.csv",
        "format": "CSV",
        "license": "CC BY-NC 3.0",
        "citation": "Killourhy, K. S., & Maxion, R. A. (2009). Comparing Anomaly-Detection Algorithms for Keystroke Dynamics. In IEEE/IFIP International Conference on Dependable Systems & Networks (DSN).",
        "paper_url": "https://www.cs.cmu.edu/~keystroke/KillourhyMaxion09.pdf"
    },
    "balabit": {
        "url": "https://github.com/balabit/Mouse-Dynamics-Challenge/archive/refs/heads/master.zip",
        "format": "CSV",
        "license": "Open Research",
        "citation": "Antal, M., & Egyed-Zsigmond, E. (2019). Intrusion detection using mouse dynamics. IET Biometrics.",
        "paper_url": "http://ceur-ws.org/Vol-1638/paper15.pdf"
    },
    "amlsim": {
        "url": "https://github.com/IBM/AMLSim/archive/refs/heads/master.zip",
        "format": "JSON/CSV",
        "license": "Apache 2.0",
        "citation": "Suzumura, T., & Kanezashi, H. (2019). Scalable Graph Learning for Anti-Money Laundering: A First Look. arXiv:1812.00076.",
        "paper_url": "https://arxiv.org/pdf/1812.00076.pdf"
    },
    "banknote_authentication": {
        "url": "https://archive.ics.uci.edu/static/public/267/banknote+authentication.zip",
        "format": "CSV",
        "license": "Open Access",
        "citation": "Gillich, E., & Lohweg, V. (2010). Banknote Authentication. UCI Machine Learning Repository.",
        "paper_url": "https://archive.ics.uci.edu/static/public/267/banknote+authentication.zip"
    }
}

HF_DATASETS = {
    "simargl2021": {
        "repo": "shivamjaisingh/SIMARGL2021-Intrusion-Detection-Systems",
        "files": ["dataset-part1.csv.zip", "dataset-part2.csv.zip"],
        "license": "CC BY-SA 4.0",
        "citation": "Mihailescu, M. E., et al. (2021). The Proposition and Evaluation of the RoEduNet-SIMARGL2021 Network Intrusion Detection Dataset. Sensors."
    },
    "beacon": {
        "repo": "beacon-gui/BEACON-Dataset",
        "files": ["metadata/public_participant_session_manifest.csv", "data/raw_gameplay_data.parquet"],
        "license": "CC BY-NC 4.0",
        "citation": "Singh, I., et al. (2026). BEACON: A Multimodal Dataset for Learning Behavioral Fingerprints from Gameplay Data. arXiv:2605.10867."
    },
    "africa_social_media_ato": {
        "repo": "electricsheepafrica/africa-social-media-account-takeover",
        "files": ["data/train-00000-of-00001.parquet"],
        "license": "CC BY 4.0",
        "citation": "Electric Sheep Africa (2025). Africa Social Media Account Takeover Survey Dataset."
    },
    "creditcard_fraud": {
        "repo": "anmorgan24/creditcard_fraud_csv",
        "files": ["creditcard.csv"], 
        "license": "CC BY-NC-SA 4.0",
        "citation": "Dal Pozzolo et al. (2015). Calibrating Probability with Undersampling for Unbalanced Classification."
    }
}

KAG_DATASETS = ["paysim", "ieee_cis", "cicids2017", "cert_insider_threat"]

def get_checksum(file_path):
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def download_file(url, dest_path):
    print(f"Downloading {url} to {dest_path}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    token = os.environ.get("HF_TOKEN")
    if "huggingface.co" in url and token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        if response.status_code == 404:
            print(f"Skipping 404: {url}")
            return False
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

def validate_usability(dataset_name, raw_path):
    files = []
    for root, _, filenames in os.walk(raw_path):
        for f in filenames:
            files.append(os.path.join(root, f))
    
    report = {
        "dataset": dataset_name,
        "timestamp": datetime.now().isoformat(),
        "files_found": len(files),
        "validation_results": []
    }

    for f in files:
        if f.endswith(".csv"):
            try:
                df = pd.read_csv(f, nrows=100)
                report["validation_results"].append({
                    "file": os.path.basename(f),
                    "status": "SUCCESS",
                    "rows_preview": len(df),
                    "columns": list(df.columns)
                })
            except Exception as e:
                report["validation_results"].append({
                    "file": os.path.basename(f),
                    "status": "FAILED",
                    "error": str(e)
                })
        elif f.endswith(".parquet"):
            try:
                df = pd.read_parquet(f)
                report["validation_results"].append({
                    "file": os.path.basename(f),
                    "status": "SUCCESS",
                    "rows_preview": len(df),
                    "columns": list(df.columns)
                })
            except Exception as e:
                report["validation_results"].append({
                    "file": os.path.basename(f),
                    "status": "FAILED",
                    "error": str(e)
                })
        elif f.endswith(".json"):
            try:
                with open(f, 'r') as jf:
                    data = json.load(jf)
                report["validation_results"].append({
                    "file": os.path.basename(f),
                    "status": "SUCCESS",
                    "type": "JSON"
                })
            except Exception as e:
                report["validation_results"].append({
                    "file": os.path.basename(f),
                    "status": "FAILED",
                    "error": str(e)
                })
    
    return report

def setup_metadata(name, info, source_url):
    meta_path = os.path.join(DATASETS_ROOT, name, "metadata")
    os.makedirs(meta_path, exist_ok=True)
    
    with open(os.path.join(meta_path, "citation.bib"), "w") as f:
        f.write(info.get("citation", "No citation available."))
    
    with open(os.path.join(meta_path, "license.txt"), "w") as f:
        f.write(info.get("license", "No license specified."))

    with open(os.path.join(meta_path, "README.md"), "w") as f:
        f.write(f"# {name}\n\nSource: {source_url}\n\n{info.get('citation', '')}")

    with open(os.path.join(meta_path, "schema.md"), "w") as f:
        f.write(f"# Schema for {name}\n\nTo be populated after validation.")

def process_standard_dataset(name, info):
    print(f"\n--- Processing {name} ---")
    raw_path = os.path.join(RAW_DIR, name)
    os.makedirs(raw_path, exist_ok=True)
    
    filename = os.path.basename(info["url"])
    local_file = os.path.join(raw_path, filename)

    success = True
    if not os.path.exists(local_file):
        success = download_file(info["url"], local_file)
    
    if success:
        if local_file.endswith(".zip"):
            try:
                with zipfile.ZipFile(local_file, 'r') as zip_ref:
                    zip_ref.extractall(raw_path)
            except Exception as e:
                print(f"Failed to unzip {local_file}: {e}")
        
        setup_metadata(name, info, info["url"])
        
        # Manifest
        manifest = {
            "source_url": info["url"],
            "download_date": datetime.now().isoformat(),
            "checksum": get_checksum(local_file),
            "file_size": os.path.getsize(local_file),
            "license": info["license"],
            "citation": info["citation"],
            "status": "COMPLETED"
        }
        with open(os.path.join(DATASETS_ROOT, name, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=4)
        
        # Validation
        report = validate_usability(name, raw_path)
        with open(os.path.join(REPORTS_DIR, f"{name}_validation.json"), "w") as f:
            json.dump(report, f, indent=4)
        print(f"Completed {name}")
    else:
        print(f"Failed to process {name}")

def process_hf_dataset(name, info):
    print(f"\n--- Processing HF {name} ---")
    raw_path = os.path.join(RAW_DIR, name)
    os.makedirs(raw_path, exist_ok=True)
    
    repo = info["repo"]
    files_to_download = info["files"]
    
    if not files_to_download:
        # Try to discover files
        try:
            r = requests.get(f"https://huggingface.co/api/datasets/{repo}")
            if r.status_code == 200:
                siblings = r.json().get("siblings", [])
                files_to_download = [s["rfilename"] for s in siblings if not s["rfilename"].startswith(".")]
        except:
            pass
    
    if not files_to_download:
        print(f"No files found for HF {name}, marking manual.")
        os.makedirs(os.path.join(DATASETS_ROOT, name), exist_ok=True)
        manifest = {
            "status": "MANUAL_DOWNLOAD_REQUIRED",
            "notes": f"Could not automatically discover files for HF repo {repo}. Might be gated or empty.",
            "source_url": f"https://huggingface.co/datasets/{repo}"
        }
        with open(os.path.join(DATASETS_ROOT, name, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=4)
        return

    all_success = True
    downloaded_files = []
    for f in files_to_download:
        url = f"https://huggingface.co/datasets/{repo}/resolve/main/{f}"
        dest = os.path.join(raw_path, f.replace("/", "_"))
        if not os.path.exists(dest):
            try:
                if download_file(url, dest):
                    downloaded_files.append(dest)
                else:
                    all_success = False
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    print(f"Unauthorized to download {url}. Dataset might be gated.")
                    all_success = False
                else:
                    raise e
        else:
            downloaded_files.append(dest)

    if downloaded_files:
        # ...
        os.makedirs(os.path.join(DATASETS_ROOT, name), exist_ok=True)
        setup_metadata(name, info, f"https://huggingface.co/datasets/{repo}")
        
        manifest = {
            "source_url": f"https://huggingface.co/datasets/{repo}",
            "download_date": datetime.now().isoformat(),
            "license": info["license"],
            "citation": info["citation"],
            "status": "COMPLETED" if all_success else "PARTIAL"
        }
        with open(os.path.join(DATASETS_ROOT, name, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=4)
        
        # Validation
        report = validate_usability(name, raw_path)
        with open(os.path.join(REPORTS_DIR, f"{name}_validation.json"), "w") as f:
            json.dump(report, f, indent=4)
        print(f"Completed HF {name}")
    else:
        print(f"Failed to process HF {name}, marking manual.")
        os.makedirs(os.path.join(DATASETS_ROOT, name), exist_ok=True)
        manifest = {
            "status": "MANUAL_DOWNLOAD_REQUIRED",
            "notes": f"Failed to download files for HF repo {repo}. Might be gated.",
            "source_url": f"https://huggingface.co/datasets/{repo}"
        }
        with open(os.path.join(DATASETS_ROOT, name, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=4)

if __name__ == "__main__":
    for name, info in DATASET_INFO.items():
        try:
            process_standard_dataset(name, info)
        except Exception:
            print(f"Error processing {name}")
            traceback.print_exc()

    for name, info in HF_DATASETS.items():
        try:
            process_hf_dataset(name, info)
        except Exception:
            print(f"Error processing HF {name}")
            traceback.print_exc()

    for name in KAG_DATASETS:
        print(f"\n--- Marking Kaggle {name} ---")
        meta_path = os.path.join(DATASETS_ROOT, name, "metadata")
        os.makedirs(meta_path, exist_ok=True)
        manifest_path = os.path.join(DATASETS_ROOT, name, "manifest.json")
        manifest = {
            "status": "MANUAL_DOWNLOAD_REQUIRED",
            "notes": "Requires Kaggle API or manual access from official source.",
            "source": f"Kaggle: {name}"
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=4)
        
        # Placeholder metadata files
        setup_metadata(name, {"citation": "Manual citation required.", "license": "Manual license check required."}, "Kaggle")
