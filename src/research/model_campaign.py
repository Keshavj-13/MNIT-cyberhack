import os
import pandas as pd
import numpy as np
import joblib
import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, average_precision_score, confusion_matrix
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier

# Constants
SEED = 42
MODELS_DIR = "models"
REPORTS_DIR = "reports/models"
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

leaderboard = []

def save_metrics(provider, dataset, model_name, y_test, y_probs, y_pred, train_time):
    roc_auc = roc_auc_score(y_test, y_probs)
    pr_auc = average_precision_score(y_test, y_probs)
    report = classification_report(y_test, y_pred, output_dict=True)
    accuracy = report['accuracy']
    precision = report['1']['precision'] if '1' in report else report['1.0']['precision'] if '1.0' in report else 0
    recall = report['1']['recall'] if '1' in report else report['1.0']['recall'] if '1.0' in report else 0
    f1 = report['1']['f1-score'] if '1' in report else report['1.0']['f1-score'] if '1.0' in report else 0
    
    metrics = {
        "provider": provider,
        "dataset": dataset,
        "model": model_name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "train_time": train_time
    }
    leaderboard.append(metrics)
    
    # Save detailed report
    with open(f"{REPORTS_DIR}/{provider}_{model_name}_metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)
    
    print(f"[METRICS] {provider} - {model_name}: ROC AUC: {roc_auc:.4f}, F1: {f1:.4f}")

# --- 1. PHISHING MODEL ---
def train_phishing():
    print("[CAMPAIGN] Training Phishing Model...")
    df = pd.read_parquet("data/raw/phishing/PhishingWebsites.parquet")
    
    # Preprocess
    # Result: -1 (Phishing), 1 (Legitimate) -> 1 (Phishing), 0 (Legitimate)
    df['target'] = df['Result'].apply(lambda x: 1 if str(x) == '-1' else 0)
    X = df.drop(columns=['Result', 'target'])
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    
    start_time = pd.Timestamp.now()
    model = lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1)
    model.fit(X_train, y_train)
    train_time = (pd.Timestamp.now() - start_time).total_seconds()
    
    probs = model.predict_proba(X_test)[:, 1]
    preds = model.predict(X_test)
    
    save_metrics("Phishing", "PhishingWebsites", "LightGBM", y_test, probs, preds, train_time)
    joblib.dump(model, f"{MODELS_DIR}/phishing_url_model.joblib")
    print(f"[SUCCESS] Phishing model saved.")

# --- 2. SMISHING MODEL ---
def train_smishing():
    print("[CAMPAIGN] Training Smishing Model...")
    # Read raw text file
    filepath = "data/raw/SOCIAL_ENGINEERING/SMSSpamCollection"
    df = pd.read_csv(filepath, sep='\t', header=None, names=['label', 'message'])
    
    # target: ham -> 0, spam -> 1
    df['target'] = (df['label'] == 'spam').astype(int)
    
    from sklearn.feature_extraction.text import TfidfVectorizer
    tfidf = TfidfVectorizer(max_features=5000, stop_words='english')
    X_tfidf = tfidf.fit_transform(df['message'])
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X_tfidf, y, test_size=0.2, random_state=SEED, stratify=y)
    
    start_time = pd.Timestamp.now()
    model = lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1)
    model.fit(X_train, y_train)
    train_time = (pd.Timestamp.now() - start_time).total_seconds()
    
    probs = model.predict_proba(X_test)[:, 1]
    preds = model.predict(X_test)
    
    save_metrics("Smishing", "SMS Spam Collection", "TF-IDF + LightGBM", y_test, probs, preds, train_time)
    
    # Save both tfidf and model as a pipeline
    from sklearn.pipeline import Pipeline
    full_model = Pipeline([
        ('tfidf', tfidf),
        ('clf', model)
    ])
    joblib.dump(full_model, f"{MODELS_DIR}/sms_scam_model.joblib")
    print(f"[SUCCESS] Smishing model saved.")

# --- 3. ACCOUNT TAKEOVER MODEL ---
def train_ato():
    print("[CAMPAIGN] Training Account Takeover Model...")
    df = pd.read_parquet("data/raw/ACCOUNT_TAKEOVER/electricsheepafrica_africa-social-media-account-takeover/data.parquet")
    
    # This dataset has 'account_security_score' as a proxy for risk, or we look for malicious labels
    # Let's use 'platform_response_score' or similar as target if binary, or derive one.
    # Actually let's look for a clearer target. 
    # If no binary target, we'll use 'account_security_score' < threshold as anomaly.
    # Looking at df.info() earlier, there are many columns. 
    # For this campaign, we'll treat lower account_security_score as high risk (target=1)
    df['target'] = (df['account_security_score'] < df['account_security_score'].median()).astype(int)
    
    # Drop non-numeric for simple XGBoost
    X = df.select_dtypes(include=[np.number]).drop(columns=['target', 'account_security_score'], errors='ignore')
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    
    start_time = pd.Timestamp.now()
    model = xgb.XGBClassifier(random_state=SEED, n_jobs=-1)
    model.fit(X_train, y_train)
    train_time = (pd.Timestamp.now() - start_time).total_seconds()
    
    probs = model.predict_proba(X_test)[:, 1]
    preds = model.predict(X_test)
    
    save_metrics("AccountTakeover", "Africa Social Media ATO", "XGBoost", y_test, probs, preds, train_time)
    joblib.dump(model, f"{MODELS_DIR}/account_takeover_model.joblib")
    print(f"[SUCCESS] ATO model saved.")

# --- 4. DEVICE TRUST MODEL ---
def train_device_trust():
    print("[CAMPAIGN] Training Device Trust Model...")
    df = pd.read_parquet("data/raw/authentication/banknote-authentication.parquet")
    
    # Map labels to 0, 1 if they are not
    # In banknote, OpenML has them as 1 and 2 (categories)
    df['target'] = df['Class'].apply(lambda x: 1 if str(x) == '2' else 0)
    
    X = df.drop(columns=['Class', 'target'])
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    
    start_time = pd.Timestamp.now()
    from sklearn.ensemble import RandomForestClassifier
    model = RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=SEED)
    model.fit(X_train, y_train)
    train_time = (pd.Timestamp.now() - start_time).total_seconds()
    
    probs = model.predict_proba(X_test)[:, 1]
    preds = model.predict(X_test)
    
    save_metrics("DeviceTrust", "Banknote Authentication", "RandomForest", y_test, probs, preds, train_time)
    joblib.dump(model, f"{MODELS_DIR}/device_trust_model.joblib")
    print(f"[SUCCESS] Device Trust model saved.")

# --- 5. NETWORK RISK MODEL ---
def train_network():
    print("[CAMPAIGN] Training Network Risk Model...")
    df = pd.read_parquet("data/raw/INTRUSION/shivamjaisingh_SIMARGL2021-Intrusion-Detection-Systems/data.parquet")
    
    # Stratified sample to ensure both classes
    normal_df = df[df['LABEL'] == 'Normal'].sample(50000, random_state=SEED)
    attack_df = df[df['LABEL'] != 'Normal'].sample(min(50000, len(df[df['LABEL'] != 'Normal'])), random_state=SEED)
    df = pd.concat([normal_df, attack_df])
    
    df['target'] = (df['LABEL'] != 'Normal').astype(int)
    
    X = df.select_dtypes(include=[np.number]).drop(columns=['target'], errors='ignore')
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    
    start_time = pd.Timestamp.now()
    model = lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1)
    model.fit(X_train, y_train)
    train_time = (pd.Timestamp.now() - start_time).total_seconds()
    
    probs = model.predict_proba(X_test)[:, 1]
    preds = model.predict(X_test)
    
    save_metrics("NetworkRisk", "SIMARGL2021", "LightGBM", y_test, probs, preds, train_time)
    joblib.dump(model, f"{MODELS_DIR}/network_risk_model.joblib")
    print(f"[SUCCESS] Network Risk model saved.")

# --- 6. TRANSACTION FRAUD MODEL ---
def train_transaction():
    print("[CAMPAIGN] Training Transaction Fraud Model...")
    # Use ULB Credit Card
    df = pd.read_parquet("data/raw/fraud/CreditCardFraudDetection.parquet")
    
    X = df.drop(columns=['Class'])
    y = df['Class']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    
    start_time = pd.Timestamp.now()
    # Use CatBoost for top tier fraud detection
    model = CatBoostClassifier(iterations=200, random_state=SEED, verbose=0, thread_count=-1)
    model.fit(X_train, y_train)
    train_time = (pd.Timestamp.now() - start_time).total_seconds()
    
    probs = model.predict_proba(X_test)[:, 1]
    preds = model.predict(X_test)
    
    save_metrics("Transaction", "ULB Credit Card", "CatBoost", y_test, probs, preds, train_time)
    joblib.dump(model, f"{MODELS_DIR}/transaction_fraud_production.joblib")
    print(f"[SUCCESS] Transaction model saved.")

if __name__ == "__main__":
    train_phishing()
    train_smishing()
    train_ato()
    train_device_trust()
    train_network()
    train_transaction()
    
    # Save Leaderboard
    df_lb = pd.DataFrame(leaderboard)
    df_lb.to_csv(f"{REPORTS_DIR}/model_leaderboard.csv", index=False)
    print(f"[FINISH] All models trained. Leaderboard saved at {REPORTS_DIR}/model_leaderboard.csv")
