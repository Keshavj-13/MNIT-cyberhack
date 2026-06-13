# Reproducibility Report

- **Date**: Thu Jun 11 14:19:36 2026
- **Random Seed**: 42
- **K-Folds**: 3

## Task: transaction
- **Dataset Size (Sample)**: 5000
- **Features**: ['account_id', 'amount', 'currency', 'transaction_type', 'merchant_category', 'recipient_id', 'country', 'account_age_days', 'tx_velocity_24h', 'amount_deviation', 'is_new_beneficiary', 'hour', 'time_risk']
### Baseline Experiment (Mean Impute + Std Scale + RF)
- **Status**: VALIDATED
- **ROC AUC**: 0.4887
- **Duration**: 0.44s

## Task: network
- **Dataset Size (Sample)**: 5000
- **Features**: ['Destination Port', 'Flow Duration', 'Total Fwd Packets', 'Total Backward Packets', 'Fwd Packet Length Max', 'Bwd Packet Length Max', 'Flow Bytes/s', 'Flow Packets/s']
### Baseline Experiment (Mean Impute + Std Scale + RF)
- **Status**: VALIDATED
- **ROC AUC**: 0.5001
- **Duration**: 0.47s

