# Modeling Strategy: Advanced Architectures & Pipelines

Based on the Dataset Intelligence Report and the Literature Review (2023-2026), the following custom modeling strategies are proposed for each risk domain. These architectures avoid vanilla models in favor of state-of-the-art hybrid and ensemble approaches.

## 1. Transaction Fraud (TransactionRiskProvider)
*   **Preprocessing Pipeline**: 
    *   Iterative Imputation for missing values.
    *   QuantileTransformer for non-linear scaling of monetary features.
    *   Target Encoding for high-cardinality categoricals (e.g., Merchant ID, Device ID).
*   **Feature Engineering Pipeline**: 
    *   Velocity features (transactions per hour/day).
    *   Deviation features (amount vs. historical average, z-scores).
    *   Geographic/IP velocity (impossible travel calculations).
*   **Custom Architecture**: **HTGNN-Inspired Hybrid Ensemble**
    *   Since true graph databases are unavailable, we approximate graph connectivity using aggregated neighbor features (e.g., shared IPs, shared devices).
    *   Base Models: CatBoost (handles categoricals naturally) + LightGBM + Isolation Forest (for unsupervised anomaly scoring).
*   **Ensemble Strategy**: Stacking Classifier with Logistic Regression meta-learner.
*   **Calibration Strategy**: Isotonic Regression to ensure probabilities reflect true fraud rates.
*   **Explainability Strategy**: SHAP TreeExplainer for instance-level feature attributions.

## 2. Social Engineering / Smishing (SocialEngineeringRiskProvider)
*   **Preprocessing Pipeline**: 
    *   Text normalization (casing, punctuation, URL replacement tokens).
    *   Subword tokenization (BPE or WordPiece).
*   **Feature Engineering Pipeline**: 
    *   Extract explicit IOCs (URLs, phone numbers, crypto addresses).
    *   Derive Intention Labels: regex/rule-based scoring for urgency, threats, or financial requests.
*   **Custom Architecture**: **Dual-Layer Contextual Ensemble**
    *   Layer 1: TF-IDF + XGBoost for fast, lexical filtering.
    *   Layer 2: Pre-trained Sentence-BERT embeddings fed into a deep MLP for semantic understanding of complex lures.
*   **Ensemble Strategy**: Confidence-Weighted Average (Layer 2 only triggered if Layer 1 confidence is low/borderline).
*   **Calibration Strategy**: Platt Scaling (Sigmoid).
*   **Explainability Strategy**: LIME for text, highlighting specific suspicious words/phrases.

## 3. Phishing URLs (PhishingRiskProvider)
*   **Preprocessing Pipeline**: 
    *   URL parsing (scheme, netloc, path, query).
*   **Feature Engineering Pipeline**: 
    *   Structural metrics: entropy, length, subdomain count, special character density.
    *   Lexical heuristics: presence of brand names in path, IP-based URLs.
*   **Custom Architecture**: **Lexical-Structural Fusion**
    *   Character-level 1D CNN (learning sequence patterns) concatenated with a LightGBM model trained on the engineered structural features.
*   **Ensemble Strategy**: Late Fusion (Averaging probabilities).
*   **Calibration Strategy**: Temperature Scaling.
*   **Explainability Strategy**: SHAP for structural features, Integrated Gradients for CNN character attributions.

## 4. Account Takeover (AccountTakeoverProvider)
*   **Preprocessing Pipeline**: 
    *   Time-series windowing (grouping by Session ID / User ID).
    *   RobustScaler for outlier resistance.
*   **Feature Engineering Pipeline**: 
    *   Login velocity, failed attempt ratios.
    *   Device switching frequency, IP subnet changes.
    *   Time-of-day behavioral anomalies.
*   **Custom Architecture**: **Temporal Anomaly & Risk Graph**
    *   LSTM to capture the sequence of session events.
    *   One-Class SVM trained on historical "normal" behavior per user segment.
*   **Ensemble Strategy**: Voting Ensemble (Soft Voting).
*   **Calibration Strategy**: Isotonic Regression.
*   **Explainability Strategy**: Permutation Importance on the engineered behavioral features.

## 5. Network Intrusion (NetworkRiskProvider)
*   **Preprocessing Pipeline**: 
    *   Strict deduplication and constant-feature removal.
    *   SMOTE-Tomek for extreme class imbalance (minority attack types).
    *   MinMaxScaler for network flows.
*   **Feature Engineering Pipeline**: 
    *   Flow-level aggregations (bytes/sec, packets/sec).
    *   Protocol ratios.
    *   Boruta algorithm for automated, aggressive feature selection to reduce dimensionality.
*   **Custom Architecture**: **FCNN-SE (Fusion CNN Stacked Ensemble) Proxy**
    *   LightGBM (for high-speed tabular processing) + TabNet (for interpretable deep learning on tabular data).
*   **Ensemble Strategy**: Blending via a secondary LightGBM meta-learner.
*   **Calibration Strategy**: Isotonic Regression.
*   **Explainability Strategy**: TabNet's native sparse attention masks for global/local explainability.

## 6. Device Trust (DeviceTrustProvider)
*   **Preprocessing Pipeline**: 
    *   Categorical encoding of User-Agents, OS, hardware concurrency.
*   **Feature Engineering Pipeline**: 
    *   Hash-based device fingerprinting (Canvas, WebGL hashes).
    *   Velocity of fingerprint changes.
*   **Custom Architecture**: **Probabilistic Trust Scorer**
    *   Random Forest combined with an empirical Bayes rule engine.
*   **Ensemble Strategy**: Rule-engine override (if strict IOCs match, score=1.0) with Random Forest probabilistic fallback.
*   **Calibration Strategy**: Platt Scaling.
*   **Explainability Strategy**: SHAP TreeExplainer.
