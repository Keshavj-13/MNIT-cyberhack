import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.io import arff
import shap
import warnings

warnings.filterwarnings("ignore")

# Define directories
PLOTS_DIR = "ui/public/plots"
REPORTS_DIR = "reports/verification_run"
os.makedirs(PLOTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

sns.set_theme(style="darkgrid")
plt.rcParams.update({
    "figure.facecolor": "#0a0a0a",
    "axes.facecolor": "#0d0d0d",
    "text.color": "#f0f0f0",
    "axes.labelcolor": "#f0f0f0",
    "xtick.color": "#b0b0b0",
    "ytick.color": "#b0b0b0",
    "grid.color": "#1e1e1e"
})

def calculate_anomalies(df, num_cols):
    """Calculate the number of outliers using IQR method."""
    if len(num_cols) == 0:
        return 0
    outliers_count = 0
    for col in num_cols:
        if col not in df.columns:
            continue
        col_clean = df[col].replace([np.inf, -np.inf], np.nan).dropna()
        if len(col_clean) == 0:
            continue
        q25 = col_clean.quantile(0.25)
        q75 = col_clean.quantile(0.75)
        iqr = q75 - q25
        lower = q25 - 1.5 * iqr
        upper = q75 + 1.5 * iqr
        outliers_count += ((col_clean < lower) | (col_clean > upper)).sum()
    return int(outliers_count)

def generate_verification_report(name, label, df, target_col, num_cols, cat_cols, row_description):
    print(f"[VERIFY] Analyzing {name}...")
    
    # Strip whitespace from column names
    df.columns = df.columns.str.strip()
    target_col = target_col.strip()
    num_cols = [c.strip() for c in num_cols]
    cat_cols = [c.strip() for c in cat_cols]
    
    # Simple cleaning: replace infs with nan
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    # Drop rows where target is missing
    df = df.dropna(subset=[target_col])
    
    # Calculate stats
    total_rows = len(df)
    total_cols = len(df.columns)
    null_count = int(df.isnull().sum().sum())
    null_pct = float((null_count / (total_rows * total_cols)) * 100) if total_cols > 0 else 0.0
    duplicate_count = int(df.duplicated().sum())
    
    # Class imbalance
    class_counts = df[target_col].value_counts().to_dict()
    class_imbalance = {str(k): int(v) for k, v in class_counts.items()}
    
    # Anomaly/Outlier count
    anomalies = calculate_anomalies(df, num_cols)
    
    # Zero variance columns
    zero_var_cols = []
    for col in num_cols:
        if col in df.columns:
            col_var = df[col].var()
            if col_var == 0 or np.isnan(col_var):
                zero_var_cols.append(col)
                
    # Prepare sample rows safely for JSON serialization
    sample_df = df.head(3).fillna("")
    sample_rows = []
    for _, row in sample_df.iterrows():
        clean_row = {}
        for k, v in row.items():
            k_str = str(k)
            if isinstance(v, bytes):
                clean_row[k_str] = v.decode('utf-8', errors='ignore')
            elif isinstance(v, (np.integer, np.int64, int)):
                clean_row[k_str] = int(v)
            elif isinstance(v, (np.floating, np.float64, float)):
                clean_row[k_str] = float(v)
            else:
                clean_row[k_str] = str(v)
        sample_rows.append(clean_row)
            
    stats = {
        "name": name,
        "label": label,
        "rows": total_rows,
        "columns": total_cols,
        "null_count": null_count,
        "null_pct": null_pct,
        "duplicate_count": duplicate_count,
        "class_imbalance": class_imbalance,
        "anomalies": anomalies,
        "zero_variance_cols": zero_var_cols,
        "target": target_col,
        "row_description": row_description,
        "sample_rows": sample_rows
    }
    
    # Create dataset-specific plot directory
    ds_plot_dir = os.path.join(PLOTS_DIR, name)
    os.makedirs(ds_plot_dir, exist_ok=True)
    
    # --- 1. EXPLORATION PLOTS ---
    print(f"  Generating Exploration Plots for {name}...")
    
    # Class Distribution Plot
    fig, ax = plt.subplots(figsize=(6, 4))
    classes = list(class_imbalance.keys())
    counts = list(class_imbalance.values())
    sorted_indices = np.argsort(counts)[::-1]
    classes = [classes[i] for i in sorted_indices][:min(10, len(classes))]
    counts = [counts[i] for i in sorted_indices][:min(10, len(counts))]
    
    colors = ["#0ea5e9", "#f43f5e", "#10b981", "#a855f7", "#eab308", "#f97316", "#ec4899", "#84cc16", "#06b6d4", "#6366f1"][:len(classes)]
    bars = ax.bar(classes, counts, color=colors, edgecolor="#ffffff22")
    ax.set_title("Class Label Distribution (Top 10)", fontsize=12, fontweight="bold", pad=15)
    ax.set_ylabel("Count")
    ax.set_xlabel("Class")
    plt.xticks(rotation=30, ha='right')
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + (total_rows * 0.01), f"{yval:,}", ha='center', va='bottom', fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(ds_plot_dir, "class_distribution.png"), dpi=150)
    plt.close()

    # Feature Distribution Plot
    valid_num_cols = [c for c in num_cols if c in df.columns]
    if len(valid_num_cols) > 0:
        plot_cols = valid_num_cols[:min(3, len(valid_num_cols))]
        fig, axes = plt.subplots(1, len(plot_cols), figsize=(4 * len(plot_cols), 4))
        if len(plot_cols) == 1:
            axes = [axes]
        for idx, col in enumerate(plot_cols):
            sns.histplot(df[col].dropna(), kde=True, ax=axes[idx], color="#0ea5e9", bins=30)
            axes[idx].set_title(f"Distribution: {col}", fontsize=10, fontweight="semibold")
            axes[idx].set_xlabel("")
        plt.tight_layout()
        plt.savefig(os.path.join(ds_plot_dir, "feature_distribution.png"), dpi=150)
        plt.close()
        
    # Correlation Matrix
    if len(valid_num_cols) > 1:
        corr_cols = valid_num_cols[:min(10, len(valid_num_cols))]
        fig, ax = plt.subplots(figsize=(8, 6))
        corr = df[corr_cols].corr()
        sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", ax=ax, cbar=True,
                    vmin=-1, vmax=1, annot_kws={"size": 8},
                    xticklabels=corr.columns, yticklabels=corr.columns)
        ax.set_title("Feature Correlation Matrix (Subset)", fontsize=12, fontweight="bold", pad=15)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        plt.savefig(os.path.join(ds_plot_dir, "correlation_matrix.png"), dpi=150)
        plt.close()

    # --- 2. TESTING & QUALITY PLOTS ---
    print(f"  Generating Testing & Quality Plots for {name}...")
    
    # Outliers Boxplot
    if len(valid_num_cols) > 0:
        box_cols = valid_num_cols[:min(5, len(valid_num_cols))]
        fig, ax = plt.subplots(figsize=(8, 5))
        df_scaled = df[box_cols].copy()
        for col in box_cols:
            col_std = df_scaled[col].std()
            if col_std > 0:
                df_scaled[col] = (df_scaled[col] - df_scaled[col].mean()) / col_std
        sns.boxplot(data=df_scaled, ax=ax, palette="Set2")
        ax.set_title("Outlier Analysis (Standardized Features)", fontsize=12, fontweight="bold", pad=15)
        ax.set_ylabel("Standardized Values (Z-Score)")
        plt.xticks(rotation=30, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(ds_plot_dir, "outliers_boxplot.png"), dpi=150)
        plt.close()

    # Missingness plot
    fig, ax = plt.subplots(figsize=(6, 4))
    null_pcounts = df.isnull().mean() * 100
    if null_pcounts.sum() > 0:
        null_pcounts = null_pcounts[null_pcounts > 0].sort_values(ascending=False)[:10]
        null_pcounts.plot(kind='bar', color="#f43f5e", ax=ax)
        ax.set_title("Missing Values Percentage per Feature", fontsize=12, fontweight="bold", pad=15)
        ax.set_ylabel("% Missing")
        plt.xticks(rotation=45, ha='right')
    else:
        ax.bar(["All Features"], [100.0], color="#10b981", edgecolor="#ffffff22")
        ax.set_title("Data Completeness Verification", fontsize=12, fontweight="bold", pad=15)
        ax.set_ylabel("% Populated")
        ax.set_ylim(0, 115)
        ax.text(0, 103, "100% Complete (No Missing Values)", ha='center', va='bottom', color="#10b981", fontweight="semibold")
    plt.tight_layout()
    plt.savefig(os.path.join(ds_plot_dir, "missingness.png"), dpi=150)
    plt.close()

    # --- 3. EXPLAINABILITY PLOTS ---
    print(f"  Generating Explainability & SHAP Plots for {name}...")
    
    try:
        if name == "sms_spam_collection":
            vectorizer = TfidfVectorizer(max_features=20)
            X = pd.DataFrame(vectorizer.fit_transform(df['text']).toarray(), columns=vectorizer.get_feature_names_out())
            y = df[target_col].map({"ham": 0, "spam": 1})
        else:
            X = df[valid_num_cols].copy()
            X = X.drop(columns=[c for c in zero_var_cols if c in X.columns])
            X = X.fillna(X.mean())
            y = df[target_col]
            if y.dtype == object or isinstance(y.iloc[0], bytes):
                from sklearn.preprocessing import LabelEncoder
                y = LabelEncoder().fit_transform(y)

        unique_classes = np.unique(y)
        
        if len(unique_classes) > 1 and len(X.columns) > 0:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            clf = RandomForestClassifier(n_estimators=30, random_state=42, max_depth=5, n_jobs=-1)
            clf.fit(X_train, y_train)
            
            # Feature Importance Plot
            importances = clf.feature_importances_
            indices = np.argsort(importances)[::-1]
            top_k = min(10, len(X.columns))
            
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.barh(range(top_k), importances[indices[:top_k]][::-1], color="#a855f7", align="center")
            ax.set_yticks(range(top_k))
            ax.set_yticklabels([X.columns[i] for i in indices[:top_k]][::-1])
            ax.set_xlabel("Relative Importance")
            ax.set_title("Random Forest Feature Importances", fontsize=12, fontweight="bold", pad=15)
            plt.tight_layout()
            plt.savefig(os.path.join(ds_plot_dir, "feature_importance.png"), dpi=150)
            plt.close()
            
            # SHAP Plot
            explainer = shap.TreeExplainer(clf)
            X_shap = X_test.sample(min(100, len(X_test)), random_state=42)
            shap_values = explainer.shap_values(X_shap)
            
            plt.figure(figsize=(7, 5))
            if isinstance(shap_values, list):
                shap.summary_plot(shap_values[1] if len(shap_values) > 1 else shap_values[0], X_shap, show=False)
            elif len(shap_values.shape) == 3:
                shap.summary_plot(shap_values[:, :, 1] if shap_values.shape[2] > 1 else shap_values[:, :, 0], X_shap, show=False)
            else:
                shap.summary_plot(shap_values, X_shap, show=False)
                
            plt.title("SHAP Summary Plot", fontsize=12, fontweight="bold", pad=15)
            plt.tight_layout()
            plt.savefig(os.path.join(ds_plot_dir, "shap_summary.png"), dpi=150)
            plt.close()
        else:
            print(f"  [SKIP] Skipping RF training for {name} (insufficient classes or features).")
            
    except Exception as e:
        print(f"  [ERROR] Failed to run explainability pipeline for {name}: {e}")
        
    return stats

def main():
    print("[START] Raw Data Verification Campaign...")
    summary_reports = []

    # 1. PaySim Transaction Fraud (Huge, load sample)
    try:
        path = "datasets/raw/paysim/PS_20174392719_1491204439457_log.csv"
        df = pd.read_csv(path, nrows=50000)
        num_cols = ["amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest", "step"]
        cat_cols = ["type", "nameOrig", "nameDest"]
        stats = generate_verification_report(
            "paysim", "PaySim (Transaction Fraud)", df, "isFraud", num_cols, cat_cols,
            "A single synthetic mobile transaction record containing origin, recipient, and transaction values."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] PaySim Verification Failed: {e}")

    # 2. SIMARGL 2021 Network Intrusion (Huge, load sample)
    try:
        path = "datasets/raw/simargl2021/dataset-part1.csv"
        df = pd.read_csv(path, nrows=50000)
        num_cols = ["FLOW_DURATION_MILLISECONDS", "IN_BYTES", "IN_PKTS", "OUT_BYTES", "OUT_PKTS", "FRAME_LENGTH", "L4_SRC_PORT", "L4_DST_PORT"]
        cat_cols = ["BIFLOW_DIRECTION", "DIRECTION", "PROTOCOL_MAP"]
        stats = generate_verification_report(
            "simargl2021", "SIMARGL (Network Intrusion)", df, "LABEL", num_cols, cat_cols,
            "A network flow record capturing network traffic metadata and communication patterns between IP addresses."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] SIMARGL Verification Failed: {e}")

    # 3. Phishing Websites
    try:
        path = "datasets/raw/phishing_websites/Training Dataset.arff"
        data, meta = arff.loadarff(path)
        df = pd.DataFrame(data)
        for col in df.columns:
            if df[col].dtype == object or isinstance(df[col].iloc[0], bytes):
                df[col] = df[col].str.decode('utf-8').astype(int)
        num_cols = [c for c in df.columns if c != "Result"]
        cat_cols = []
        stats = generate_verification_report(
            "phishing_websites", "Phishing Websites", df, "Result", num_cols, cat_cols,
            "A set of hand-crafted features extracted from website HTML, domain registrar records, and URLs."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] Phishing Websites Verification Failed: {e}")

    # 4. SMS Spam Collection
    try:
        path = "datasets/raw/sms_spam_collection/SMSSpamCollection"
        df = pd.read_csv(path, sep='\t', names=['label', 'text'])
        df['text_len'] = df['text'].str.len()
        df['word_count'] = df['text'].apply(lambda x: len(str(x).split()))
        num_cols = ['text_len', 'word_count']
        cat_cols = []
        stats = generate_verification_report(
            "sms_spam_collection", "SMS Spam (Smishing)", df, "label", num_cols, cat_cols,
            "A raw mobile text message containing message contents, labeled as ham (legitimate) or spam (smishing)."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] SMS Spam Verification Failed: {e}")

    # 5. CMU Keystroke
    try:
        path = "datasets/raw/cmu_keystroke/DSL-StrongPasswordData.csv"
        df = pd.read_csv(path)
        num_cols = [c for c in df.columns if c not in ["subject", "sessionIndex", "rep"]]
        cat_cols = []
        stats = generate_verification_report(
            "cmu_keystroke", "CMU Keystroke Dynamics", df, "subject", num_cols, cat_cols,
            "Keyboard hold times and key press interval times (in seconds) for a user typing a standardized password."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] CMU Keystroke Verification Failed: {e}")

    # 6. Banknote Authentication
    try:
        path = "datasets/raw/banknote_authentication/data_banknote_authentication.txt"
        df = pd.read_csv(path, header=None, names=['variance', 'skewness', 'curtosis', 'entropy', 'class'])
        num_cols = ['variance', 'skewness', 'curtosis', 'entropy']
        cat_cols = []
        stats = generate_verification_report(
            "banknote_authentication", "Banknote Authentication", df, "class", num_cols, cat_cols,
            "Wavelet transformed features extracted from digital images of genuine and forged banknotes."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] Banknote Verification Failed: {e}")

    # 7. Africa Social Media ATO
    try:
        path = "datasets/raw/africa_social_media_ato/data_train-00000-of-00001.parquet"
        df = pd.read_parquet(path)
        num_cols = ["password_reused", "no_mfa", "phishing_link_clicked", "fake_login_page", "sim_swap_used"]
        cat_cols = ["country", "intelligence_source"]
        stats = generate_verification_report(
            "africa_social_media_ato", "Africa Social Media ATO", df, "attack_type", num_cols, cat_cols,
            "Social media platform security log indicating threat intelligence metrics and account takeover details."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] Africa Social Media ATO Verification Failed: {e}")

    # 8. AMLSim Anti-Money Laundering
    try:
        tx_path = "datasets/raw/amlsim/AMLSim-master/sample/outputs/tx.csv"
        alerts_path = "datasets/raw/amlsim/AMLSim-master/sample/outputs/alerts.csv"
        df_tx = pd.read_csv(tx_path)
        df_alerts = pd.read_csv(alerts_path)
        df_tx['is_fraud'] = df_tx['ACCOUNT_ID'].isin(df_alerts['ACCOUNT_ID']).astype(int)
        num_cols = ["TXN_AMOUNT_ORIG", "tx_count"]
        cat_cols = ["TXN_SOURCE_TYPE_CODE"]
        stats = generate_verification_report(
            "amlsim", "AMLSim (Money Laundering)", df_tx, "is_fraud", num_cols, cat_cols,
            "A simulated transaction record showing account transfer amounts and source categories."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] AMLSim Verification Failed: {e}")

    # 9. Balabit Mouse Dynamics
    try:
        path = "datasets/raw/balabit/Mouse-Dynamics-Challenge-master/training_files/user7/session_0041905381"
        df = pd.read_csv(path, nrows=50000)
        num_cols = ["record timestamp", "client timestamp", "x", "y"]
        cat_cols = ["button"]
        stats = generate_verification_report(
            "balabit", "Balabit Mouse Dynamics", df, "state", num_cols, cat_cols,
            "A single mouse cursor pointer tracking event containing coordinate details and click states."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] Balabit Verification Failed: {e}")

    # 10. CERT Insider Threat
    try:
        path = "datasets/raw/cert_insider_threat/psychometric.csv"
        df = pd.read_csv(path)
        df['high_neuroticism'] = (df['N'] > 30).astype(int)
        num_cols = ["O", "C", "E", "A"]
        cat_cols = []
        stats = generate_verification_report(
            "cert_insider_threat", "CERT Insider Threat", df, "high_neuroticism", num_cols, cat_cols,
            "An employee profile containing Big Five personality score traits (Openness, Conscientiousness, etc.) used for insider risk scoring."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] CERT Insider Threat Verification Failed: {e}")

    # 11. CICIDS2017 DDoS
    try:
        path = "datasets/raw/cicids2017/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv"
        df = pd.read_csv(path, nrows=50000)
        df.columns = df.columns.str.strip()
        num_cols = ["Flow Duration", "Total Fwd Packets", "Total Backward Packets", "Fwd Packet Length Max", "Bwd Packet Length Max"]
        cat_cols = []
        stats = generate_verification_report(
            "cicids2017", "CICIDS2017 DDoS", df, "Label", num_cols, cat_cols,
            "A packet capture flow statistics record containing traffic volume, packet headers, and duration profiles."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] CICIDS2017 Verification Failed: {e}")

    # 12. Credit Card Fraud (Kaggle)
    try:
        path = "datasets/raw/creditcard_fraud/creditcard.csv"
        df = pd.read_csv(path, nrows=50000)
        num_cols = ["Time", "Amount", "V1", "V2", "V3", "V4", "V5"]
        cat_cols = []
        stats = generate_verification_report(
            "creditcard_fraud", "Credit Card Fraud (Kaggle)", df, "Class", num_cols, cat_cols,
            "An anonymized real credit card transaction containing PCA-transformed features and transaction amount."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] Credit Card Fraud Verification Failed: {e}")

    # 13. IEEE CIS Fraud Detection
    try:
        path = "datasets/raw/ieee_cis/train_transaction.csv"
        df = pd.read_csv(path, nrows=50000)
        num_cols = ["TransactionAmt", "card1", "card2", "card3", "card5"]
        cat_cols = ["ProductCD"]
        stats = generate_verification_report(
            "ieee_cis", "IEEE-CIS Fraud Detection", df, "isFraud", num_cols, cat_cols,
            "A commercial online transaction containing payment method details, card brands, and billing regions."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] IEEE CIS Verification Failed: {e}")

    # 14. Feedzai Bank Account Fraud (NEW)
    try:
        path = "datasets/raw/feedzai_baf/Base.csv"
        df = pd.read_csv(path, nrows=50000)
        num_cols = ["income", "name_email_similarity", "current_address_months_count", "customer_age", "intended_balcon_amount", "velocity_6h", "velocity_24h"]
        cat_cols = ["payment_type", "employment_status", "housing_status", "device_os"]
        stats = generate_verification_report(
            "feedzai_baf", "Feedzai Bank Account Fraud", df, "fraud_bool", num_cols, cat_cols,
            "A bank account application containing applicant income, email matching similarity, credit risk parameters, and fraud status."
        )
        summary_reports.append(stats)
    except Exception as e:
        print(f"[ERROR] Feedzai BAF Verification Failed: {e}")

    # Save summary report JSON
    with open(os.path.join(REPORTS_DIR, "summary.json"), "w") as f:
        json.dump(summary_reports, f, indent=4)
        
    print(f"\n[SUCCESS] Raw Data Verification Campaign Completed! Summary saved to {REPORTS_DIR}/summary.json")

if __name__ == "__main__":
    main()
