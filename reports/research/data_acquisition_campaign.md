# Data Acquisition Campaign Report & Evaluation

## Objective
Identify, evaluate, and rank real-world datasets across eight categories to replace the synthetic data currently bottlenecking the Banking Threat Detection System.

---

## Dataset Evaluations

### 1. IEEE-CIS Fraud Detection
1. **Name**: IEEE-CIS Fraud Detection
2. **Source URL**: `https://www.kaggle.com/c/ieee-fraud-detection`
3. **License**: Free/Kaggle Competition Rules
4. **Size**: ~2 GB (Uncompressed)
5. **Number of records**: 590,540 (Train)
6. **Number of features**: 433
7. **Fraud label availability**: Yes (`isFraud`)
8. **Social engineering relevance**: Low
9. **Device intelligence relevance**: High (Vesta tracking, DeviceType, DeviceInfo, OS, Browser, Screen Resolution)
10. **Network security relevance**: Low
11. **Banking relevance**: High (Card-not-present ecommerce transactions)
12. **Ease of integration**: Medium (Requires heavy feature engineering and dimensionality reduction)
13. **Expected contribution**: Massive upgrade to **Transaction Risk** and **Device Trust** providers. It introduces real-world correlations between device fingerprints and fraud.

### 2. Credit Card Fraud Detection (ULB)
1. **Name**: Credit Card Fraud Detection
2. **Source URL**: `https://www.kaggle.com/mlg-ulb/creditcardfraud`
3. **License**: Open Database License (ODbL)
4. **Size**: 144 MB
5. **Number of records**: 284,807
6. **Number of features**: 31 (PCA transformed V1-V28, Time, Amount)
7. **Fraud label availability**: Yes (`Class`)
8. **Social engineering relevance**: Low
9. **Device intelligence relevance**: Low
10. **Network security relevance**: Low
11. **Banking relevance**: High (European cardholder transactions)
12. **Ease of integration**: High (Clean, numeric, perfectly formatted for immediate ML ingestion)
13. **Expected contribution**: Immediate drop-in replacement for the **Transaction Risk** model to validate the LightGBM/XGBoost architectures against a real-world, highly imbalanced (0.17%) target.

### 3. CERT Insider Threat Dataset (v6.2)
1. **Name**: CERT Insider Threat Dataset
2. **Source URL**: `https://resources.sei.cmu.edu/library/asset-view.cfm?assetid=508099`
3. **License**: Public Domain
4. **Size**: ~100 GB (Varies by version)
5. **Number of records**: Millions (Event logs)
6. **Number of features**: Varies by log type (Logon, HTTP, Email, File, Device)
7. **Fraud label availability**: Yes (Insider threat scenarios are explicitly marked)
8. **Social engineering relevance**: Medium (Contains anomalous email/phishing response patterns)
9. **Device intelligence relevance**: Medium (Removable media usage, unusual machine logins)
10. **Network security relevance**: High (HTTP traffic logs)
11. **Banking relevance**: Medium (Models internal employee threats/account takeover)
12. **Ease of integration**: Low (Requires massive data engineering to parse disparate logs into session features)
13. **Expected contribution**: Foundational data for the **Context Risk Provider** and future **Behavioral Risk** (UEBA) models.

### 4. UMDAA-02 (Active Authentication)
1. **Name**: UMDAA-02 (University of Maryland Active Authentication Dataset 2)
2. **Source URL**: `http://www.umiacs.umd.edu/~vishalm/umdaa02.html`
3. **License**: Academic Use
4. **Size**: ~10 GB
5. **Number of records**: Millions of sensor readings
6. **Number of features**: Multimodal (Touchscreen swipes, Keystrokes, Gyroscope, Accelerometer)
7. **Fraud label availability**: N/A (Used for continuous identity verification)
8. **Social engineering relevance**: Low
9. **Device intelligence relevance**: High (Hardware sensor characteristics)
10. **Network security relevance**: Low
11. **Banking relevance**: High (Simulates continuous authentication during a mobile banking session)
12. **Ease of integration**: Low (Raw sensor timeseries requires deep learning/CNN/RNN preprocessing)
13. **Expected contribution**: Will serve as the ground-truth data to build out the future **Behavioral Risk Provider** (BEACON placeholder).

### 5. LANL Comprehensive Cyber-Security Events
1. **Name**: Comprehensive, Multi-Source Cyber-Security Events (LANL)
2. **Source URL**: `https://csr.lanl.gov/data/cyber1/`
3. **License**: Public Domain
4. **Size**: 12 GB (Compressed)
5. **Number of records**: 1.6 Billion events over 58 days
6. **Number of features**: Varies (Auth logs, Process flows, DNS, NetFlow)
7. **Fraud label availability**: Yes (Red team compromise events labeled)
8. **Social engineering relevance**: Low
9. **Device intelligence relevance**: Low
10. **Network security relevance**: Very High
11. **Banking relevance**: Medium (Enterprise network intrusion)
12. **Ease of integration**: Low (Big data infrastructure required)
13. **Expected contribution**: Replaces the synthetic CICIDS2017 dataset for the **Network Risk Provider**, adding complex lateral movement and account takeover network signatures.

### 6. Phishing Websites Dataset (UCI)
1. **Name**: Phishing Websites Dataset
2. **Source URL**: `https://archive.ics.uci.edu/ml/datasets/Phishing+Websites`
3. **License**: CC0
4. **Size**: < 1 MB
5. **Number of records**: 11,055
6. **Number of features**: 30 (URL properties, domain registration, abnormal requests)
7. **Fraud label availability**: Yes (Phishing vs Legitimate)
8. **Social engineering relevance**: High
9. **Device intelligence relevance**: Low
10. **Network security relevance**: Low
11. **Banking relevance**: Medium (First stage of banking account takeover)
12. **Ease of integration**: High
13. **Expected contribution**: Can be used by the **Context Risk Provider** to evaluate if the traffic originated from a malicious link.

### 7. PaySim (Simulated Mobile Money Transactions)
1. **Name**: PaySim
2. **Source URL**: `https://www.kaggle.com/ealaxi/paysim1`
3. **License**: CC BY-SA 4.0
4. **Size**: ~470 MB
5. **Number of records**: 6,362,620
6. **Number of features**: 11
7. **Fraud label availability**: Yes (`isFraud`, `isFlaggedFraud`)
8. **Social engineering relevance**: Low
9. **Device intelligence relevance**: Low
10. **Network security relevance**: Low
11. **Banking relevance**: High (Simulates mobile money transactions)
12. **Ease of integration**: High
13. **Expected contribution**: While technically synthetic, it is generated via a robust agent-based model of real African mobile money logs. It is a good secondary validation for the **Transaction Risk Provider**.

### 8. BETH Dataset (Behavioral Evaluation of Threat Hunting)
1. **Name**: BETH Dataset
2. **Source URL**: `https://www.kaggle.com/datasets/kateeesponda/beth-dataset`
3. **License**: Apache 2.0
4. **Size**: ~500 MB
5. **Number of records**: 8.5 million
6. **Number of features**: 14
7. **Fraud label availability**: Yes (Anomaly/Attack)
8. **Social engineering relevance**: Low
9. **Device intelligence relevance**: Low
10. **Network security relevance**: High (Linux host-level logs)
11. **Banking relevance**: Medium (Server-side compromise detection)
12. **Ease of integration**: Medium
13. **Expected contribution**: Enhances the **Network Risk Provider** with host-level anomaly detection.

---

## Final Acquisition Ranking

Based on the goal of immediately upgrading the risk providers from random guessing (~0.50 AUC) to real predictive power, the datasets are ranked by the product of their **Banking Relevance**, **Integration Ease**, and **Feature Richness**:

1. **IEEE-CIS Fraud Detection** (Best overall context: Transactions + Devices)
2. **Credit Card Fraud Detection (ULB)** (Fastest path to validate Transaction ML)
3. **CERT Insider Threat Dataset** (Best for Context/Account Takeover modeling)
4. **UMDAA-02** (Critical for the future Behavioral Risk component)
5. **LANL Cyber Security Dataset** (Massive upgrade for Network Risk)
6. Phishing Websites Dataset (UCI)
7. PaySim
8. BETH Dataset

---

## Final Acquisition Plan (Top 5)

To dramatically improve the system, we will acquire the following top 5 datasets and route them to specific risk providers:

1. **Transaction Risk Provider upgrade:**
   - **Acquire**: `Credit Card Fraud Detection (ULB)`
   - **Action**: Use immediately to validate the LightGBM/Optuna pipeline on real, highly imbalanced financial data.

2. **Device Trust & Context Provider upgrade:**
   - **Acquire**: `IEEE-CIS Fraud Detection`
   - **Action**: Extract the `DeviceInfo`, `DeviceType`, and `Vesta` features. Use this to train a predictive model for Device Risk, replacing the current hard-coded rules.

3. **Behavioral Biometrics Preparation:**
   - **Acquire**: `UMDAA-02`
   - **Action**: Begin preprocessing the raw sensor data (swipes, keystrokes) to build the deep learning (CNN/RNN) backend for the `BehaviorRiskPlaceholderProvider`.

4. **Network Risk Provider upgrade:**
   - **Acquire**: `LANL Cyber-Security Events`
   - **Action**: Replace the synthetic CICIDS2017 flow data with LANL authentication and NetFlow events to capture real lateral movement.

5. **Account Takeover / Context Risk upgrade:**
   - **Acquire**: `CERT Insider Threat v6.2`
   - **Action**: Model unusual login times, new geographic access, and abnormal file access to feed the Context Risk Provider.
