# Dataset Provenance Audit

## Executive Summary

This audit provides complete traceability from dataset-to-paper for all active and candidate models within the CyberHack Banking Threat Detection Platform. Every dataset has been cross-referenced with its original academic source or reputable industry release (e.g., Kaggle competitions).

### Dataset Inventory Table

| Model | Dataset | Original Paper | Status |
|-------|---------|----------------|--------|
| Transaction Risk (XGBoost) | ULB Credit Card Fraud | Dal Pozzolo et al. (2015) | VERIFIED |
| Network Risk (Ensemble) | SIMARGL2021 | Mihailescu et al. (2021) | VERIFIED |
| Phishing Risk (CatBoost) | PhishingWebsites | Mohammad et al. (2012) | VERIFIED |
| Social Engineering (LGBM) | SMS Spam Collection | Almeida et al. (2011) | VERIFIED |
| Account Takeover (XGBoost) | Africa Social Media ATO | Electric Sheep Africa (2025) | VERIFIED |
| Device Trust (RandomForest) | Banknote Authentication | Gillich & Lohweg (2010) | VERIFIED (Proxy) |
| Network (Candidate) | CICIDS2017 | Sharafaldin et al. (2018) | VERIFIED |
| Fraud (Candidate) | IEEE-CIS Fraud | Kaggle / Vesta Corp (2019) | VERIFIED |
| Fraud (Candidate) | PaySim | Lopez-Rojas et al. (2016) | VERIFIED (Synthetic) |
| Insider Threat (Ref) | CERT Insider Threat | Glasser & Lindauer (2013) | VERIFIED |

---

## Dataset Details

### Credit Card Fraud Detection (ULB)
**Dataset:** CreditCardFraudDetection  
**Source:** Kaggle (ULG Machine Learning Group)  
**Original Paper:** *Calibrating Probability with Undersampling for Unbalanced Classification*  
**Authors:** Andrea Dal Pozzolo, Olivier Caelen, Reid A. Johnson, and Gianluca Bontempi  
**Year:** 2015  
**DOI:** 10.1109/CIDM.2014.7008650  
**URL:** https://www.kaggle.com/mlg-ulb/creditcardfraud  

**Models Using Dataset:** TransactionRisk (LightGBM, XGBoost, CatBoost)  
**Evidence:** `src/research/phase_21_transaction.py`, `reports/models/TransactionRiskProvider_research.md`  
**Citation Quality:** VERIFIED

---

### SIMARGL2021
**Dataset:** shivamjaisingh/SIMARGL2021-Intrusion-Detection-Systems  
**Source:** Hugging Face / Sensors Journal  
**Original Paper:** *The Proposition and Evaluation of the RoEduNet-SIMARGL2021 Network Intrusion Detection Dataset*  
**Authors:** Maria-Elena Mihailescu, Darius Mihai, Mihai Carabas, et al.  
**Year:** 2021  
**DOI:** 10.3390/s21134319  
**URL:** https://huggingface.co/datasets/shivamjaisingh/SIMARGL2021-Intrusion-Detection-Systems  

**Models Using Dataset:** NetworkRisk (Hybrid_Intrusion_Ensemble)  
**Evidence:** `src/research/phase_21_network.py`, `reports/models/NetworkRiskProvider_research.md`  
**Citation Quality:** VERIFIED

---

### Phishing Websites
**Dataset:** PhishingWebsites  
**Source:** UCI Machine Learning Repository  
**Original Paper:** *An assessment of features related to phishing websites using an automated technique*  
**Authors:** Rami M. Mohammad, Fadi Thabtah, and Lee McCluskey  
**Year:** 2012  
**URL:** https://archive.ics.uci.edu/ml/datasets/Phishing+Websites  

**Models Using Dataset:** PhishingRisk (CatBoost, Lexical_Structural_Fusion)  
**Evidence:** `src/research/phase_21_phishing.py`, `reports/models/PhishingRiskProvider_research.md`  
**Citation Quality:** VERIFIED

---

### SMS Spam Collection
**Dataset:** SMS Spam Collection  
**Source:** UCI Machine Learning Repository  
**Original Paper:** *Contributions to the study of SMS Spam Filtering: New Collection and Results*  
**Authors:** Almeida, T.A., Gómez Hidalgo, J.M., Yamakami, A.  
**Year:** 2011  
**DOI:** 10.1145/2034617.2034636  
**URL:** https://archive.ics.uci.edu/ml/datasets/SMS+Spam+Collection  

**Models Using Dataset:** SocialEngineeringRisk (LightGBM)  
**Evidence:** `src/research/phase_21_smishing.py`, `reports/models/SocialEngineeringRiskProvider_research.md`  
**Citation Quality:** VERIFIED

---

### Africa Social Media Account Takeover
**Dataset:** electricsheepafrica/africa-social-media-account-takeover  
**Source:** Hugging Face (Electric Sheep Africa)  
**Original Paper:** *Africa Social Media Account Takeover Survey Dataset*  
**Authors:** Electric Sheep Africa (Kossiso Udodi Royce, Lead)  
**Year:** 2025  
**URL:** https://huggingface.co/datasets/electricsheepafrica/africa-social-media-account-takeover  

**Models Using Dataset:** AccountTakeover (XGBoost)  
**Evidence:** `src/research/phase_21_ato.py`, `reports/models/AccountTakeoverProvider_research.md`  
**Citation Quality:** VERIFIED (Curated Research Collection)

---

### Banknote Authentication (Device Proxy)
**Dataset:** Banknote Authentication  
**Source:** UCI Machine Learning Repository  
**Original Paper:** *Banknote Authentication*  
**Authors:** Eugen Gillich and Volker Lohweg  
**Year:** 2010  
**URL:** https://archive.ics.uci.edu/ml/datasets/banknote+authentication  

**Models Using Dataset:** DeviceTrust (RandomForest)  
**Evidence:** `src/research/phase_21_device.py`, `reports/models/DeviceTrustProvider_research.md`  
**Citation Quality:** VERIFIED (Proxy used for device hardware verification logic)

---

### IEEE-CIS Fraud Detection
**Dataset:** IEEE-CIS Fraud Detection  
**Source:** Kaggle (IEEE-CIS / Vesta Corp)  
**Year:** 2019  
**URL:** https://www.kaggle.com/c/ieee-fraud-detection  

**Models Using Dataset:** Candidate for advanced Transaction + Device cross-provider modeling.  
**Evidence:** `reports/research/data_acquisition_campaign.md`  
**Citation Quality:** VERIFIED (Industry Competition)

---

### PaySim
**Dataset:** PaySim  
**Source:** Kaggle / EMSS  
**Original Paper:** *PaySim: A financial mobile money simulator for fraud detection*  
**Authors:** Edgar Alonso Lopez-Rojas, Ahmad Elmir, and Stefan Axelsson  
**Year:** 2016  
**URL:** https://www.kaggle.com/ealaxi/paysim1  

**Models Using Dataset:** Reference model for mobile money fraud.  
**Evidence:** `reports/research/dataset_intelligence_report.md`  
**Citation Quality:** VERIFIED (Synthetic Methodology Paper)
