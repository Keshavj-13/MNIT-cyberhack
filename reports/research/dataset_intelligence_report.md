# Dataset Intelligence Report

## 1. Dataset Analysis

### analcatdata_fraud
- **Category**: FRAUD
- **Row Count**: 42
- **Feature Count**: 12
- **Target Column**: class
- **Class Distribution (Sample)**: 0: 69.0%, 1: 31.0%
- **Data Type**: Mixed
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Transaction Fraud`.

### CreditCardFraudDetection
- **Category**: FRAUD
- **Row Count**: 284807
- **Feature Count**: 31
- **Target Column**: Class
- **Class Distribution (Sample)**: 0: 99.6%, 1: 0.4%
- **Data Type**: Numeric
- **Quality Issues**: Severe class imbalance detected (>99% majority class).
- **Leakage Risks**: High (Temporal features present. Requires time-based splitting to prevent future leakage).
- **Overlap with Other Datasets**: Check domain `Transaction Fraud`.

### PhishingWebsites
- **Category**: PHISHING
- **Row Count**: 11055
- **Feature Count**: 31
- **Target Column**: Result
- **Class Distribution (Sample)**: 1: 55.7%, -1: 44.3%
- **Data Type**: Mixed
- **Quality Issues**: None detected.
- **Leakage Risks**: Medium (ID features present. Must be dropped to prevent identity leakage).
- **Overlap with Other Datasets**: Check domain `Phishing URLs`.

### Binary-Dataset-of-Phishing-and-Legitimate-URLs
- **Category**: PHISHING
- **Row Count**: 11000
- **Feature Count**: 15
- **Target Column**: label
- **Class Distribution (Sample)**: 1: 50.0%, 0: 50.0%
- **Data Type**: Numeric
- **Quality Issues**: None detected.
- **Leakage Risks**: High (Temporal features present. Requires time-based splitting to prevent future leakage).
- **Overlap with Other Datasets**: Check domain `Phishing URLs`.

### PhishingWebsites_seed_0_nrows_2000_nclasses_10_ncols_100_stratify_True
- **Category**: PHISHING
- **Row Count**: 2000
- **Feature Count**: 31
- **Target Column**: Result
- **Class Distribution (Sample)**: 1: 55.7%, -1: 44.3%
- **Data Type**: Mixed
- **Quality Issues**: None detected.
- **Leakage Risks**: Medium (ID features present. Must be dropped to prevent identity leakage).
- **Overlap with Other Datasets**: Check domain `Phishing URLs`.

### banknote-authentication
- **Category**: AUTHENTICATION
- **Row Count**: 1372
- **Feature Count**: 5
- **Target Column**: Class
- **Class Distribution (Sample)**: 1: 55.5%, 2: 44.5%
- **Data Type**: Mixed
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Authentication`.

### Bank-Note-Authentication-UCI
- **Category**: AUTHENTICATION
- **Row Count**: 1372
- **Feature Count**: 5
- **Target Column**: class
- **Class Distribution (Sample)**: 0: 55.5%, 1: 44.5%
- **Data Type**: Numeric
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Authentication`.

### jslin09/Fraud_Case_Verdicts
- **Category**: FRAUD
- **Row Count**: Unknown
- **Feature Count**: Unknown
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed
- **Quality Issues**: Error during analysis: [WinError 3] Failed to open local file 'data/raw/FRAUD/jslin09_Fraud_Case_Verdicts/data.parquet'. Detail: [Windows error 3] The system cannot find the path specified.

- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Transaction Fraud`.

### anmorgan24/creditcard_fraud_csv
- **Category**: FRAUD
- **Row Count**: Unknown
- **Feature Count**: Unknown
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed
- **Quality Issues**: Error during analysis: [WinError 3] Failed to open local file 'data/raw/FRAUD/anmorgan24_creditcard_fraud_csv/data.parquet'. Detail: [Windows error 3] The system cannot find the path specified.

- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Transaction Fraud`.

### open-llm-leaderboard-old/details_jslin09__bloom-560m-finetuned-fraud
- **Category**: FRAUD
- **Row Count**: Unknown
- **Feature Count**: Unknown
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed
- **Quality Issues**: Error during analysis: [WinError 3] Failed to open local file 'data/raw/FRAUD/open-llm-leaderboard-old_details_jslin09__bloom-560m-finetuned-fraud/data.parquet'. Detail: [Windows error 3] The system cannot find the path specified.

- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Transaction Fraud`.

### Mitake/PhishingURLsANDBenignURLs
- **Category**: PHISHING
- **Row Count**: 886181
- **Feature Count**: 2
- **Target Column**: label
- **Class Distribution (Sample)**: 0: 68.7%, 1: 31.3%
- **Data Type**: Mixed (Categorical/Numeric)
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Phishing URLs`.

### bgspaditya/phishing-dataset
- **Category**: PHISHING
- **Row Count**: 651191
- **Feature Count**: 2
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed (Categorical/Numeric)
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Phishing URLs`.

### YousufEjaz/phishing_legitimate
- **Category**: PHISHING
- **Row Count**: 4140
- **Feature Count**: 1
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Text
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Phishing URLs`.

### itsG/smishing-synthetic
- **Category**: SMISHING
- **Row Count**: 143
- **Feature Count**: 3
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed (Categorical/Numeric)
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Smishing / Social Engineering`.

### MOZNLP/MOZ-Smishing
- **Category**: SMISHING
- **Row Count**: 2561
- **Feature Count**: 4
- **Target Column**: label
- **Class Distribution (Sample)**: Legitimate: 78.4%, Smishing: 21.6%
- **Data Type**: Text
- **Quality Issues**: None detected.
- **Leakage Risks**: Medium (ID features present. Must be dropped to prevent identity leakage).
- **Overlap with Other Datasets**: Check domain `Smishing / Social Engineering`.

### shariul-islam/bengali-sms-smishing-dataset
- **Category**: SMISHING
- **Row Count**: 5604
- **Feature Count**: 3
- **Target Column**: label
- **Class Distribution (Sample)**: smish: 40.1%, normal: 35.5%, promo: 24.4%
- **Data Type**: Text
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Smishing / Social Engineering`.

### GrayHatMwenda/INTRUSIONDETECTION
- **Category**: INTRUSION
- **Row Count**: Unknown
- **Feature Count**: Unknown
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed
- **Quality Issues**: Error during analysis: [WinError 3] Failed to open local file 'data/raw/INTRUSION/GrayHatMwenda_INTRUSIONDETECTION/data.parquet'. Detail: [Windows error 3] The system cannot find the path specified.

- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Network Intrusion`.

### Mutugi/intrusion-test
- **Category**: INTRUSION
- **Row Count**: Unknown
- **Feature Count**: Unknown
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed
- **Quality Issues**: Error during analysis: [WinError 3] Failed to open local file 'data/raw/INTRUSION/Mutugi_intrusion-test/data.parquet'. Detail: [Windows error 3] The system cannot find the path specified.

- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Network Intrusion`.

### shivamjaisingh/SIMARGL2021-Intrusion-Detection-Systems
- **Category**: INTRUSION
- **Row Count**: 40263811
- **Feature Count**: 50
- **Target Column**: LABEL
- **Class Distribution (Sample)**: SYN Scan - aggressive: 69.0%, Normal flow: 31.1%
- **Data Type**: Mixed (Categorical/Numeric)
- **Quality Issues**: None detected.
- **Leakage Risks**: Medium (ID features present. Must be dropped to prevent identity leakage).
- **Overlap with Other Datasets**: Check domain `Network Intrusion`.

### bornpresident/mirai_botnet
- **Category**: BOTNET
- **Row Count**: 3732319
- **Feature Count**: 48
- **Target Column**: label
- **Class Distribution (Sample)**: BenignTraffic: 29.6%, Mirai-greeth_flood: 26.5%, Mirai-udpplain: 24.6%, Mirai-greip_flood: 19.3%
- **Data Type**: Mixed (Categorical/Numeric)
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Botnet`.

### colabfit/BOTnet_ACAC_2022_Dihedral_scan
- **Category**: BOTNET
- **Row Count**: 45
- **Feature Count**: 42
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed (Categorical/Numeric)
- **Quality Issues**: None detected.
- **Leakage Risks**: Medium (ID features present. Must be dropped to prevent identity leakage).
- **Overlap with Other Datasets**: Check domain `Botnet`.

### colabfit/BOTnet_ACAC_2022_test_300K_MD
- **Category**: BOTNET
- **Row Count**: 650
- **Feature Count**: 42
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed (Categorical/Numeric)
- **Quality Issues**: None detected.
- **Leakage Risks**: Medium (ID features present. Must be dropped to prevent identity leakage).
- **Overlap with Other Datasets**: Check domain `Botnet`.

### jinmang2/cert_insider_threat
- **Category**: INSIDER THREAT
- **Row Count**: Unknown
- **Feature Count**: Unknown
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed
- **Quality Issues**: Error during analysis: [WinError 3] Failed to open local file 'data/raw/INSIDER_THREAT/jinmang2_cert_insider_threat/data.parquet'. Detail: [Windows error 3] The system cannot find the path specified.

- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Insider Threat`.

### smj1513/insider_threater
- **Category**: INSIDER THREAT
- **Row Count**: 7
- **Feature Count**: 5
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed (Categorical/Numeric)
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Insider Threat`.

### QuantumSkynet/llama-4-maverick-full-dataset-synthetic-insider-threat-reports
- **Category**: INSIDER THREAT
- **Row Count**: 13386
- **Feature Count**: 7
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed (Categorical/Numeric)
- **Quality Issues**: None detected.
- **Leakage Risks**: Medium (ID features present. Must be dropped to prevent identity leakage).
- **Overlap with Other Datasets**: Check domain `Insider Threat`.

### farish07/banknote-authentication-dataset
- **Category**: AUTHENTICATION
- **Row Count**: 1371
- **Feature Count**: 5
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Numeric
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Authentication`.

### emunah/authentication
- **Category**: AUTHENTICATION
- **Row Count**: 2000
- **Feature Count**: 4
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed (Categorical/Numeric)
- **Quality Issues**: None detected.
- **Leakage Risks**: Medium (ID features present. Must be dropped to prevent identity leakage).
- **Overlap with Other Datasets**: Check domain `Authentication`.

### MLLab-TS/banknote_authentication
- **Category**: AUTHENTICATION
- **Row Count**: 1372
- **Feature Count**: 5
- **Target Column**: class
- **Class Distribution (Sample)**: 0: 55.5%, 1: 44.5%
- **Data Type**: Numeric
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Authentication`.

### electricsheepafrica/africa-social-media-account-takeover
- **Category**: ACCOUNT TAKEOVER
- **Row Count**: 10000
- **Feature Count**: 186
- **Target Column**: label
- **Class Distribution (Sample)**: 1: 50.0%, 0: 50.0%
- **Data Type**: Mixed (Categorical/Numeric)
- **Quality Issues**: None detected.
- **Leakage Risks**: Medium (ID features present. Must be dropped to prevent identity leakage).
- **Overlap with Other Datasets**: Check domain `Account Takeover`.

### SwarmandBee/defendable-pain-account-takeover-pain-v0.1
- **Category**: ACCOUNT TAKEOVER
- **Row Count**: 14
- **Feature Count**: 5
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed (Categorical/Numeric)
- **Quality Issues**: None detected.
- **Leakage Risks**: Medium (ID features present. Must be dropped to prevent identity leakage).
- **Overlap with Other Datasets**: Check domain `Account Takeover`.

### SMS Spam Collection
- **Category**: SOCIAL ENGINEERING
- **Row Count**: Unknown
- **Feature Count**: Unknown
- **Target Column**: Unknown
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Smishing / Social Engineering`.

### IEEE CIS Fraud
- **Category**: TRANSACTION FRAUD
- **Row Count**: Unknown
- **Feature Count**: Unknown
- **Target Column**: nan
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Transaction Fraud`.

### CERT Insider Threat
- **Category**: USER BEHAVIOR ANALYTICS
- **Row Count**: Unknown
- **Feature Count**: Unknown
- **Target Column**: nan
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Insider Threat`.

### CICIDS2017
- **Category**: NETWORK INTRUSION
- **Row Count**: Unknown
- **Feature Count**: Unknown
- **Target Column**: nan
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Network Intrusion`.

### PaySim
- **Category**: TRANSACTION FRAUD
- **Row Count**: Unknown
- **Feature Count**: Unknown
- **Target Column**: nan
- **Class Distribution (Sample)**: Unknown
- **Data Type**: Mixed
- **Quality Issues**: None detected.
- **Leakage Risks**: Low
- **Overlap with Other Datasets**: Check domain `Transaction Fraud`.

## 2. Dataset Relationship Map

### Transaction Fraud
- analcatdata_fraud
- CreditCardFraudDetection
- jslin09/Fraud_Case_Verdicts
- anmorgan24/creditcard_fraud_csv
- open-llm-leaderboard-old/details_jslin09__bloom-560m-finetuned-fraud
- IEEE CIS Fraud
- PaySim

### Phishing URLs
- PhishingWebsites
- Binary-Dataset-of-Phishing-and-Legitimate-URLs
- PhishingWebsites_seed_0_nrows_2000_nclasses_10_ncols_100_stratify_True
- Mitake/PhishingURLsANDBenignURLs
- bgspaditya/phishing-dataset
- YousufEjaz/phishing_legitimate

### Smishing / Social Engineering
- itsG/smishing-synthetic
- MOZNLP/MOZ-Smishing
- shariul-islam/bengali-sms-smishing-dataset
- SMS Spam Collection

### Account Takeover
- electricsheepafrica/africa-social-media-account-takeover
- SwarmandBee/defendable-pain-account-takeover-pain-v0.1

### Network Intrusion
- GrayHatMwenda/INTRUSIONDETECTION
- Mutugi/intrusion-test
- shivamjaisingh/SIMARGL2021-Intrusion-Detection-Systems
- CICIDS2017

### Authentication
- banknote-authentication
- Bank-Note-Authentication-UCI
- farish07/banknote-authentication-dataset
- emunah/authentication
- MLLab-TS/banknote_authentication

### Botnet
- bornpresident/mirai_botnet
- colabfit/BOTnet_ACAC_2022_Dihedral_scan
- colabfit/BOTnet_ACAC_2022_test_300K_MD

### Insider Threat
- jinmang2/cert_insider_threat
- smj1513/insider_threater
- QuantumSkynet/llama-4-maverick-full-dataset-synthetic-insider-threat-reports
- CERT Insider Threat

## 3. Domain Recommendations

### Transaction Fraud
- **Datasets to merge**: None directly (schemas differ). Evaluate independently or build ensemble of models trained on different domains.
- **Datasets to discard**: analcatdata_fraud (too small: 42 rows), PaySim (synthetic/simulator rules easily memorized)
- **Datasets for validation**: Use CreditCardFraudDetection for primary training. Use IEEE CIS Fraud (if acquired) for validation of feature engineering.
- **Leakage risks**: High risk from transaction time. Must split by time.
- **Overfitting risks**: PaySim (highly synthetic).

### Phishing URLs
- **Datasets to merge**: Merge PhishingWebsites and Binary-Dataset-of-Phishing-and-Legitimate-URLs if feature sets align, otherwise keep separate.
- **Datasets to discard**: PhishingWebsites_seed_0_nrows_2000 (subset of main dataset).
- **Datasets for validation**: Mitake/PhishingURLsANDBenignURLs
- **Leakage risks**: Low.
- **Overfitting risks**: Small subset datasets.

### Smishing / Social Engineering
- **Datasets to merge**: Merge SMS Spam Collection, MOZ-Smishing, itsG/smishing-synthetic (if languages match) to form a robust multilingual/diverse corpus.
- **Datasets to discard**: None, data is scarce.
- **Datasets for validation**: bengali-sms-smishing-dataset (use for cross-lingual robustness test).
- **Leakage risks**: Medium (duplicate messages common).
- **Overfitting risks**: Synthetic datasets like itsG/smishing-synthetic.

### Account Takeover
- **Datasets to merge**: None. Very specific schemas.
- **Datasets to discard**: None.
- **Datasets for validation**: Use one subset for strict time-based holdout.
- **Leakage risks**: High (User IDs. Must group splits by User ID to prevent identity leakage).
- **Overfitting risks**: Small academic datasets.

### Network Intrusion
- **Datasets to merge**: None. Too large.
- **Datasets to discard**: colabfit/BOTnet... (molecular dynamics datasets mistakenly tagged as botnet).
- **Datasets for validation**: CICIDS2017 (if available).
- **Leakage risks**: Extreme (Source/Dest IP and Ports cause identity leakage).
- **Overfitting risks**: High (models often memorize IP addresses instead of attack signatures).

### Insider Threat
- **Datasets to merge**: None.
- **Datasets to discard**: QuantumSkynet/llama-4-maverick... (LLM generated synthetic reports, not telemetry).
- **Datasets for validation**: cert_insider_threat
- **Leakage risks**: High (User IDs).
- **Overfitting risks**: High.

