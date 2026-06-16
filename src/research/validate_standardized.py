import os
import pandas as pd
import json

DATASETS_ROOT = "datasets/raw"
REPORT_DIR = "reports/dataset_validation"
os.makedirs(REPORT_DIR, exist_ok=True)

def validate_dataset(name, file_path, sep=',', header='infer', names=None):
    report = {
        "dataset": name,
        "file": file_path,
        "status": "FAILED",
        "error": ""
    }
    try:
        if file_path.endswith('.arff'):
            # Simple check for ARFF - just see if it exists and has content
            with open(file_path, 'r') as f:
                content = f.read(1000)
                if "@relation" in content.lower():
                    report["status"] = "SUCCESS (ARFF)"
                    report["preview"] = content[:200]
                else:
                    report["error"] = "Not a valid ARFF file"
        elif file_path.endswith('.parquet'):
            df = pd.read_parquet(file_path)
            report["status"] = "SUCCESS"
            report["rows"] = len(df)
            report["columns"] = list(df.columns)
            report["status"] = "SUCCESS"
        else:
            df = pd.read_csv(file_path, sep=sep, header=header, names=names, nrows=1000)
            report["status"] = "SUCCESS"
            report["rows_approx"] = "Unknown (Sampled 1000)"
            report["columns"] = list(df.columns)
            
        print(f"Validated {name}: {report['status']}")
    except Exception as e:
        report["error"] = str(e)
        print(f"Failed to validate {name}: {e}")
    
    with open(os.path.join(REPORT_DIR, f"{name}_manual_validation.json"), "w") as f:
        json.dump(report, f, indent=4)

if __name__ == "__main__":
    # SMS Spam
    validate_dataset("sms_spam_collection", "datasets/raw/sms_spam_collection/SMSSpamCollection", sep='\t', names=['label', 'text'])
    
    # Phishing
    validate_dataset("phishing_websites", "datasets/raw/phishing_websites/Training Dataset.arff")
    
    # CMU Keystroke
    validate_dataset("cmu_keystroke", "datasets/raw/cmu_keystroke/DSL-StrongPasswordData.csv")
    
    # Balabit
    validate_dataset("balabit", "datasets/raw/balabit/Mouse-Dynamics-Challenge-master/training_files/user7/session_0041905381")

    # SIMARGL
    validate_dataset("simargl2021", "datasets/raw/simargl2021/dataset-part1.csv")

    # Africa ATO
    validate_dataset("africa_social_media_ato", "datasets/raw/africa_social_media_ato/data_train-00000-of-00001.parquet")

    # PaySim
    validate_dataset("paysim", "datasets/raw/paysim/PS_20174392719_1491204439457_log.csv")

    # Credit Card Fraud
    validate_dataset("creditcard_fraud", "datasets/raw/creditcard_fraud/creditcard.csv")

    # Feedzai BAF
    validate_dataset("feedzai_baf", "datasets/raw/feedzai_baf/Base.csv")
