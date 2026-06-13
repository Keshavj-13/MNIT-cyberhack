# Implementation Decision Report - Phase 1

## Dataset Discovery Summary
- **Transaction Dataset**: Synthetic Multi Pattern Banking Transaction Dataset.
  - *Status*: Automatic download failed (403). Synthetic dev data generated with matching schema.
  - *Key Features Found*: `timestamp`, `customer_id`, `amount`, `is_fraud`, `device_id`, `ip_address`, `country`, `account_age_days`.
- **Network Dataset**: CIC IDS 2017.
  - *Status*: Synthetic dev data generated with key representative features.
  - *Key Features Found*: `Destination Port`, `Flow Duration`, `Flow Bytes/s`, `Label`.

## Context Engine Feasibility
| Feature | Existence | Derivation Logic |
| --- | --- | --- |
| Account Age | Existing | `account_age_days` column. |
| Beneficiary Info | Existing | `recipient_id` (can derive "new beneficiary" flag). |
| Transaction Velocity | Derived | Calculated from `timestamp` per `customer_id`. |
| Geographic Info | Existing | `country` and `ip_address`. |
| Device Info | Existing | `device_id` (can derive "new device" flag). |
| Timestamps | Existing | `timestamp`. |

## Architectural Adjustments
- The **Context Provider** will focus on:
  - `transaction_velocity`: Count of transactions in last 24h.
  - `amount_deviation`: Current amount vs customer's mean.
  - `new_beneficiary`: Flag if `recipient_id` not seen before for this `customer_id`.
  - `new_device`: Flag if `device_id` not seen before.
  - `time_risk`: High risk if transaction is between 11PM - 5AM.

## Next Steps
- **Phase 2**: Implement preprocessing pipelines to handle these derivations and cache as `.parquet`.
- **Phase 3/4**: Train models using these enriched features.
