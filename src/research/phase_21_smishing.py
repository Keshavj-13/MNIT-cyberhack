import os
import pandas as pd
import numpy as np
import time
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import lightgbm as lgb
import xgboost as xgb
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin

SEED = 42
REPORTS_DIR = "reports/models"
MODELS_DIR = "models"
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

class TextFeatureExtractor(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self
        
    def transform(self, X):
        df = pd.DataFrame({'text': list(X)})
        df['urgency'] = df['text'].str.lower().str.contains('urgent|immediate|asap|now').astype(int)
        df['threat'] = df['text'].str.lower().str.contains('block|suspend|close|terminate').astype(int)
        df['financial'] = df['text'].str.lower().str.contains('bank|account|payment|refund|prize|cash|won').astype(int)
        df['warning'] = df['text'].str.lower().str.contains('alert|warning|unauthorized|activity').astype(int)
        return df[['urgency', 'threat', 'financial', 'warning']].values

def run_smishing():
    print("[PHASE 21] Smishing Provider Research")
    
    filepath = "data/raw/SOCIAL_ENGINEERING/SMSSpamCollection"
    df = pd.read_csv(filepath, sep='\t', header=None, names=['label', 'message'])
    df['target'] = (df['label'] == 'spam').astype(int)
    
    X = df['message'].fillna('')
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    
    # Dual Layer Ensemble concept: Fast rules/TF-IDF first, then ML. We build pipelines to represent this.
    # Feature extraction combined with ML
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import FeatureUnion
    
    # Text pipeline
    tfidf = TfidfVectorizer(max_features=5000, stop_words='english', ngram_range=(1,2))
    
    feature_union = FeatureUnion([
        ('tfidf', tfidf),
        ('custom_features', TextFeatureExtractor())
    ])
    
    models = {
        "LogisticRegression": Pipeline([
            ('features', feature_union),
            ('clf', LogisticRegression(random_state=SEED, max_iter=1000))
        ]),
        "LightGBM": Pipeline([
            ('features', feature_union),
            ('clf', lgb.LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1))
        ]),
        "XGBoost": Pipeline([
            ('features', feature_union),
            ('clf', xgb.XGBClassifier(random_state=SEED, n_jobs=-1, eval_metric='logloss'))
        ])
    }
    
    best_f1 = 0
    best_model_name = ""
    report_md = "# Social Engineering Provider Research\n\n"
    report_md += "**Datasets Used**: SMS Spam Collection\n\n"
    report_md += "**Feature Engineering**: Extracted TF-IDF, Ngrams (1-2), Urgency, Threat, Financial bait, and Account warning indicators.\n\n"
    
    for name, model in models.items():
        start = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - start
        
        train_probs = model.predict_proba(X_train)[:, 1]
        test_probs = model.predict_proba(X_test)[:, 1]
        test_preds = model.predict(X_test)
        
        train_auc = roc_auc_score(y_train, train_probs)
        test_auc = roc_auc_score(y_test, test_probs)
        f1 = f1_score(y_test, test_preds)
        prec = precision_score(y_test, test_preds)
        rec = recall_score(y_test, test_preds)
        
        report_md += f"### Model: {name}\n"
        report_md += f"- **Train AUC**: {train_auc:.4f}\n"
        report_md += f"- **Test AUC**: {test_auc:.4f}\n"
        report_md += f"- **Test F1**: {f1:.4f} (Prec: {prec:.4f}, Rec: {rec:.4f})\n"
        report_md += f"- **Train Time**: {train_time:.2f}s\n\n"
        
        if train_auc - test_auc > 0.1:
            report_md += f"**WARNING**: {name} exhibits severe overfitting (Train-Test AUC gap > 0.1).\n\n"
            
        if f1 > best_f1:
            best_f1 = f1
            best_model_name = name
            joblib.dump(model, f"{MODELS_DIR}/sms_provider_candidate.joblib")
            
    report_md += f"**Winner**: {best_model_name} (F1: {best_f1:.4f})\n"
    report_md += "**Observed Weaknesses**: Highly imbalanced dataset. While F1 is high, it relies on historical vocabulary which is prone to drift.\n"
    
    with open(f"{REPORTS_DIR}/SocialEngineeringRiskProvider_research.md", "w") as f:
        f.write(report_md)
        
    print(f"[SUCCESS] Smishing research complete. Winner: {best_model_name}")

if __name__ == "__main__":
    run_smishing()
