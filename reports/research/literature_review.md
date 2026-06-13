# Literature Review: State-of-the-Art in Threat Detection (2023-2026)

This review synthesizes recent academic research from IEEE, ACM, and arXiv across five core domains critical to the Banking Threat Detection Platform.

## 1. Transaction Fraud Detection
*   **State of the Art (SOTA)**: The paradigm has shifted from static tabular models (like standard XGBoost) to **Heterogeneous Temporal Graph Neural Networks (HTGNNs)**. Models like GCD-GNN (2025) and ASA-GNN (2024) use graph structures to capture relational "camouflage" where fraudsters mimic legitimate behavior. 
*   **Feature Engineering**: Sequential modeling using Hidden Markov Models (HMM) to derive "state likelihoods" as features before feeding them into traditional classifiers. Graph-structural augmentation via self-supervised pre-training is also prevalent.
*   **Ensemble & Calibration**: Stacking ensembles of XGBoost, LightGBM, and CatBoost remain the gold standard for pure tabular data. **Conformal Prediction** (e.g., ITCF framework, 2025) and Temperature Scaling are heavily used to provide "confidence sets" instead of point estimates, which is critical for imbalanced fraud data.

## 2. Social Engineering & Smishing Detection
*   **SOTA Approaches**: Detection has evolved from single-message classification to **multi-turn conversational analysis** using LLMs. Dual-Layer Ensemble Frameworks (e.g., PhishNet, 2026) use fast ML (XGBoost/DistilBERT) for Layer 1 filtering, and pass borderline cases to LLMs for semantic reasoning.
*   **Feature Engineering**: Integration of Cyber Threat Intelligence (CTI) IOCs. Concept-level representations are replacing word-level TF-IDF to counter adversarial text manipulations. Intention labels (e.g., grooming, urgency) are derived features.
*   **Ensemble Techniques**: Weighted majority voting across LLMs and classical models to reduce false positives.

## 3. Account Takeover & Behavioral Biometrics
*   **SOTA Approaches**: Moving to continuous, AI-driven "Turing Test" environments. Focus is on **Injection Attack Detection (IAD)** to counter deepfakes and generative AI bypassing traditional Presentation Attack Detection (PAD).
*   **Feature Engineering**: Time-Series Foundation Models (TSFM) like Chronos-2 are used as frozen backbones to extract context window features from raw sensor telemetry (mouse, keystrokes), fed into lightweight regression heads. TLS Fingerprinting (JA4+) and Geo-Velocity checks are standard.
*   **Ensemble Techniques**: Decomposition-based Multimodal Interaction Learning (DMIL, 2026) and late fusion (e.g., Infodeslib, 2024) dynamically weight different behavioral signals based on availability and reliability.

## 4. Network Intrusion Detection
*   **SOTA Approaches**: Centralized Hybrid HIDS combining signature-based and anomaly-based zero-day detection. Deep Learning models like **CNN-LSTM** (spatial-temporal) and VAE-CWGANs are replacing shallow networks.
*   **Feature Engineering**: Automated feature extraction via Fusion CNNs (FCNN) combined with Embedded Feature Selection (e.g., inside Random Forests) to maintain interpretability while reducing dimensionality. SMOTE and GANs are standard for minority class synthesis.
*   **Ensemble Techniques**: Stacked Ensembles (SE) using a meta-learner over FCNN and LightGBM base models achieve >99.9% accuracy on modern datasets (UNSW-NB15, Edge-IIoTset). Cross-dataset generalization is the new primary benchmark metric.

## 5. Phishing URL Detection
*   **SOTA Approaches**: Explainable deep learning models that process character-level sequences (CNNs) alongside engineered lexical features.
*   **Feature Engineering**: Extraction of structure features (entropy, special symbols), domain/host signals, and visual similarity metrics (computer vision on rendered pages).
*   **Ensemble Techniques**: Combining fast lexical classifiers (LightGBM) with heavier deep sequence models, often utilizing SHAP in the training loop for automated, drift-resistant feature selection.
