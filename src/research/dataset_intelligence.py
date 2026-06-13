import os
import pandas as pd
import numpy as np

INVENTORY_PATH = "data/catalog/master_dataset_inventory.csv"
REPORT_PATH = "reports/research/dataset_intelligence_report.md"

def analyze_datasets():
    print("[INFO] Starting Dataset Intelligence Analysis...")
    df_inv = pd.read_csv(INVENTORY_PATH)
    downloaded = df_inv[df_inv['download_success'] == True]
    
    report = "# Dataset Intelligence Report\n\n"
    
    domains = {
        "Transaction Fraud": [],
        "Phishing URLs": [],
        "Smishing / Social Engineering": [],
        "Account Takeover": [],
        "Device Trust": [],
        "Network Intrusion": [],
        "Behavioral Biometrics": [],
        "Authentication": [],
        "Botnet": [],
        "Insider Threat": []
    }
    
    # Map raw categories to domains
    cat_map = {
        "FRAUD": "Transaction Fraud",
        "TRANSACTION FRAUD": "Transaction Fraud",
        "PHISHING": "Phishing URLs",
        "SMISHING": "Smishing / Social Engineering",
        "SOCIAL ENGINEERING": "Smishing / Social Engineering",
        "ACCOUNT TAKEOVER": "Account Takeover",
        "DEVICE TRUST": "Device Trust",
        "NETWORK INTRUSION": "Network Intrusion",
        "INTRUSION": "Network Intrusion",
        "BEHAVIORAL BIOMETRICS": "Behavioral Biometrics",
        "AUTHENTICATION": "Authentication",
        "BOTNET": "Botnet",
        "INSIDER THREAT": "Insider Threat",
        "USER BEHAVIOR ANALYTICS": "Insider Threat"
    }

    report += "## 1. Dataset Analysis\n\n"
    
    for _, row in downloaded.iterrows():
        name = row['dataset_name']
        cat = row['category']
        path = row['local_path']
        domain = cat_map.get(cat.upper(), "Unknown")
        
        if domain in domains:
            domains[domain].append(name)
        
        print(f"  Analyzing: {name}")
        
        row_count = "Unknown"
        feature_count = "Unknown"
        target_col = row.get('label_column', 'Unknown')
        class_dist = "Unknown"
        data_type = "Mixed"
        quality_issues = "None detected."
        leakage_risks = "Low"
        
        try:
            if str(path).endswith('.parquet'):
                # Read metadata or sample
                from pyarrow.parquet import ParquetFile
                pf = ParquetFile(path)
                row_count = pf.metadata.num_rows
                feature_count = pf.metadata.num_columns
                
                # Sample for types and distribution
                sample_df = pd.read_parquet(path) if row_count < 100000 else next(pf.iter_batches(batch_size=10000)).to_pandas()
                
                # Guess target
                possible_targets = [col for col in sample_df.columns if col.lower() in ['class', 'label', 'target', 'result', 'isfraud', 'is_fraud']]
                if possible_targets and target_col == 'Unknown':
                    target_col = possible_targets[-1]
                elif target_col not in sample_df.columns and possible_targets:
                    target_col = possible_targets[-1]
                    
                if target_col in sample_df.columns:
                    dist = sample_df[target_col].value_counts(normalize=True).to_dict()
                    class_dist = ", ".join([f"{k}: {v*100:.1f}%" for k, v in dist.items()])
                    if sample_df[target_col].nunique() == 1:
                        quality_issues = "Only one class present in sample (potential severe imbalance or missing labels)."
                    elif any(v > 0.99 for v in dist.values()):
                        quality_issues = "Severe class imbalance detected (>99% majority class)."
                
                # Check data types
                types = sample_df.dtypes
                if all(pd.api.types.is_numeric_dtype(t) for t in types):
                    data_type = "Numeric"
                elif any(pd.api.types.is_string_dtype(t) for t in types):
                    if any("message" in c.lower() or "text" in c.lower() for c in sample_df.columns):
                        data_type = "Text"
                    else:
                        data_type = "Mixed (Categorical/Numeric)"
                
                # Leakage check
                if any("time" in c.lower() or "date" in c.lower() for c in sample_df.columns):
                    leakage_risks = "High (Temporal features present. Requires time-based splitting to prevent future leakage)."
                if any("id" in c.lower() or "index" in c.lower() for c in sample_df.columns):
                    leakage_risks = "Medium (ID features present. Must be dropped to prevent identity leakage)."

            elif str(path).endswith('.csv') or str(path).endswith('.data') or "SMSSpamCollection" in str(path):
                # Handle CSV/Text
                try:
                    df = pd.read_csv(path, nrows=10000, sep=None, engine='python')
                    row_count = row['rows'] if row['rows'] > 0 else "Unknown (CSV)"
                    feature_count = len(df.columns)
                    
                    if "message" in df.columns or "text" in df.columns or len(df.columns) <= 2:
                        data_type = "Text"
                        if len(df.columns) == 2: target_col = df.columns[0]
                    else:
                        data_type = "Mixed"
                        
                    if target_col in df.columns:
                        dist = df[target_col].value_counts(normalize=True).to_dict()
                        class_dist = ", ".join([f"{k}: {v*100:.1f}%" for k, v in dist.items()])
                except: pass
                
        except Exception as e:
            quality_issues = f"Error during analysis: {e}"

        report += f"### {name}\n"
        report += f"- **Category**: {cat}\n"
        report += f"- **Row Count**: {row_count}\n"
        report += f"- **Feature Count**: {feature_count}\n"
        report += f"- **Target Column**: {target_col}\n"
        report += f"- **Class Distribution (Sample)**: {class_dist}\n"
        report += f"- **Data Type**: {data_type}\n"
        report += f"- **Quality Issues**: {quality_issues}\n"
        report += f"- **Leakage Risks**: {leakage_risks}\n"
        report += f"- **Overlap with Other Datasets**: Check domain `{domain}`.\n\n"

    report += "## 2. Dataset Relationship Map\n\n"
    for domain, dsets in domains.items():
        if dsets:
            report += f"### {domain}\n"
            for d in dsets:
                report += f"- {d}\n"
            report += "\n"

    report += "## 3. Domain Recommendations\n\n"
    
    # Hardcoded strategic recommendations based on system architect view
    recommendations = {
        "Transaction Fraud": {
            "merge": "None directly (schemas differ). Evaluate independently or build ensemble of models trained on different domains.",
            "discard": "analcatdata_fraud (too small: 42 rows), PaySim (synthetic/simulator rules easily memorized)",
            "validation": "Use CreditCardFraudDetection for primary training. Use IEEE CIS Fraud (if acquired) for validation of feature engineering.",
            "leakage": "High risk from transaction time. Must split by time.",
            "overfit": "PaySim (highly synthetic)."
        },
        "Phishing URLs": {
            "merge": "Merge PhishingWebsites and Binary-Dataset-of-Phishing-and-Legitimate-URLs if feature sets align, otherwise keep separate.",
            "discard": "PhishingWebsites_seed_0_nrows_2000 (subset of main dataset).",
            "validation": "Mitake/PhishingURLsANDBenignURLs",
            "leakage": "Low.",
            "overfit": "Small subset datasets."
        },
        "Smishing / Social Engineering": {
            "merge": "Merge SMS Spam Collection, MOZ-Smishing, itsG/smishing-synthetic (if languages match) to form a robust multilingual/diverse corpus.",
            "discard": "None, data is scarce.",
            "validation": "bengali-sms-smishing-dataset (use for cross-lingual robustness test).",
            "leakage": "Medium (duplicate messages common).",
            "overfit": "Synthetic datasets like itsG/smishing-synthetic."
        },
        "Account Takeover": {
            "merge": "None. Very specific schemas.",
            "discard": "None.",
            "validation": "Use one subset for strict time-based holdout.",
            "leakage": "High (User IDs. Must group splits by User ID to prevent identity leakage).",
            "overfit": "Small academic datasets."
        },
        "Device Trust & Authentication": {
            "merge": "Banknote authentication datasets (they are mostly duplicates of the same UCI dataset).",
            "discard": "Keep only one banknote-authentication dataset, discard the others.",
            "validation": "N/A",
            "leakage": "Low.",
            "overfit": "High (Banknote dataset is trivial)."
        },
        "Network Intrusion": {
            "merge": "None. Too large.",
            "discard": "colabfit/BOTnet... (molecular dynamics datasets mistakenly tagged as botnet).",
            "validation": "CICIDS2017 (if available).",
            "leakage": "Extreme (Source/Dest IP and Ports cause identity leakage).",
            "overfit": "High (models often memorize IP addresses instead of attack signatures)."
        },
        "Insider Threat": {
            "merge": "None.",
            "discard": "QuantumSkynet/llama-4-maverick... (LLM generated synthetic reports, not telemetry).",
            "validation": "cert_insider_threat",
            "leakage": "High (User IDs).",
            "overfit": "High."
        }
    }
    
    for domain, rec in recommendations.items():
        if domain in domains and domains[domain]:
            report += f"### {domain}\n"
            report += f"- **Datasets to merge**: {rec['merge']}\n"
            report += f"- **Datasets to discard**: {rec['discard']}\n"
            report += f"- **Datasets for validation**: {rec['validation']}\n"
            report += f"- **Leakage risks**: {rec['leakage']}\n"
            report += f"- **Overfitting risks**: {rec['overfit']}\n\n"

    with open(REPORT_PATH, "w") as f:
        f.write(report)
    print(f"[SUCCESS] Dataset Intelligence Report saved to {REPORT_PATH}")

if __name__ == "__main__":
    analyze_datasets()
