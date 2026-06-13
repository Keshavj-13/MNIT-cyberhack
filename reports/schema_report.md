# Schema Report

## Dataset: CICIDS2017_sample.csv
- **Shape (Sample):** (1000, 9)
### Columns & Types
| Column | Type | Null % | Sample Value |
| --- | --- | --- | --- |
| Destination Port | int64 | 0.00% | 56422 |
| Flow Duration | int64 | 0.00% | 542643 |
| Total Fwd Packets | int64 | 0.00% | 23 |
| Total Backward Packets | int64 | 0.00% | 90 |
| Fwd Packet Length Max | float64 | 0.00% | 395.1054179337667 |
| Bwd Packet Length Max | float64 | 0.00% | 1362.6693085356023 |
| Flow Bytes/s | float64 | 0.00% | 617436.3798900691 |
| Flow Packets/s | float64 | 0.00% | 8084.904541911344 |
| Label | str | 0.00% | BENIGN |

## Dataset: Synthetic_Multi_Pattern_Banking_Transaction_Dataset.csv
- **Shape (Sample):** (1000, 13)
### Columns & Types
| Column | Type | Null % | Sample Value |
| --- | --- | --- | --- |
| timestamp | str | 0.00% | 2023-03-26 16:38:00 |
| customer_id | int64 | 0.00% | 1564 |
| account_id | int64 | 0.00% | 5267 |
| amount | float64 | 0.00% | 4921.67445420153 |
| currency | str | 0.00% | EUR |
| transaction_type | str | 0.00% | TRANSFER |
| merchant_category | str | 0.00% | ELECTRONICS |
| recipient_id | int64 | 0.00% | 4080 |
| is_fraud | int64 | 0.00% | 0 |
| device_id | str | 0.00% | dev_27 |
| ip_address | str | 0.00% | 192.168.1.72 |
| country | str | 0.00% | FRA |
| account_age_days | int64 | 0.00% | 628 |

## Feature Availability Matrix (Context Engine)
| Feature | Existing Column (Guess) | Availability |
| --- | --- | --- |
| Account Age | | |
| Beneficiary Info | | |
| Transaction Velocity | | |
| Geographic Info | | |
| Device Info | | |
| Timestamps | | |
