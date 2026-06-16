# Dataset Cleanup Report

## Summary
The project dataset repository has been audited, standardized, and cleaned. Non-human-readable artifacts and proprietary exports have been replaced with official dataset releases where possible. A new standardized directory structure has been established in `datasets/`.

## Datasets Standardized & Replaced
The following datasets have been successfully downloaded from official sources, validated, and documented with metadata and manifests.

| Dataset | Status | Source | Format |
| ------- | ------ | ------ | ------ |
| SIMARGL2021 | COMPLETED | Hugging Face | CSV |
| Phishing Websites | COMPLETED | UCI | ARFF |
| SMS Spam Collection | COMPLETED | UCI | TXT/CSV |
| Africa Social Media ATO | COMPLETED | Hugging Face | Parquet |
| Banknote Authentication | COMPLETED | UCI | CSV |
| AMLSim | COMPLETED | GitHub | JSON/CSV |
| Balabit | COMPLETED | GitHub | CSV |
| CMU Keystroke | COMPLETED | CMU | CSV |
| PaySim | COMPLETED | Kaggle | CSV |
| IEEE-CIS Fraud | COMPLETED | Kaggle (Mirror) | CSV |
| CICIDS2017 | COMPLETED | Kaggle (Mirror) | CSV |
| CERT Insider Threat | COMPLETED | Kaggle (Mirror) | CSV |
| Credit Card Fraud (ULB) | COMPLETED | Kaggle | CSV |
| Feedzai BAF | COMPLETED | Kaggle | CSV |

## Datasets Requiring Manual Acquisition
The following datasets require manual download due to license restrictions or gated access on Hugging Face.

| Dataset | Status | Notes |
| ------- | ------ | ----- |
| BEACON | MANUAL_DOWNLOAD_REQUIRED | Gated access on Hugging Face. Requires manual approval. |

## Storage & Artifact Cleanup
The following obsolete or non-standard artifacts were removed:

- `data/raw/INTRUSIONDETECTION.data`
- `data/raw/phishing/` (all sub-files)
- `data/raw/se_datasets/` (all sub-files)
- `data/raw/ACCOUNT_TAKEOVER/` (all sub-files)
- `data/raw/authentication/` (all sub-files)
- `data/raw/BOTNET/` (all sub-files)
- `data/raw/fraud/` (all sub-files)
- `data/raw/INSIDER_THREAT/` (all sub-files)
- `data/raw/INTRUSION/` (all sub-files)
- `data/raw/real_fraud/` (all sub-files)
- `data/raw/SMISHING/` (all sub-files)
- `data/raw/SOCIAL_ENGINEERING/` (all sub-files)
- `data/raw/CICIDS2017_sample.csv`
- `data/raw/Synthetic_Multi_Pattern_Banking_Transaction_Dataset.csv`
- `data/raw/Fraud_Case_Verdicts.data`
- `data/raw/intrusion-test.data`

## Storage Reclaimed
Estimated Storage Reclaimed: ~250 MB (based on removed parquet and temporary files).

## Success Criterion Verification
- [x] Official datasets downloaded and stored in `datasets/raw/`.
- [x] Metadata (citation, license, paper) stored in `datasets/<name>/metadata/`.
- [x] `manifest.json` generated for every dataset.
- [x] Usability validated with pandas and documented in `reports/dataset_validation/`.
- [x] Obsolete .data and temporary files removed.
