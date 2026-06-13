# Platform Optimization Decision Log

This log records the hypotheses, audits, and integration decisions made during the Autonomous Research and Optimization Loop (Phase 24).

## Principles
1. Evidence over metrics.
2. Platform quality over leaderboard performance.
3. Scientific validity over impressive numbers.

---

## [2026-06-11] Experiment 1: Transaction Fraud Temporal Validation
- **Hypothesis**: Enforcing zero-shuffling (temporal split) will reveal the 'true' lower bound of fraud performance and increase platform reliability.
- **Audit Results**: 
    - ROC AUC: 0.9801
    - Recall: 0.7333
    - Brier Score: 0.0004
- **Platform Improvement?**: YES. Prevents future-information leakage and provides a defensible estimate of real-world performance.
- **Decision**: **ACCEPTED**.
- **Action**: Serialized to `models/transaction_fraud_v2_temporal.joblib`.

## [2026-06-11] Experiment 2: Provider Rationalization
- **Hypothesis**: Rejecting proxy-trained ML models for Device Trust (Banknotes) and ATO (Social Media Surveys) will improve platform truthfulness.
- **Audit Results**: N/A (Architectural rejection).
- **Platform Improvement?**: YES. Eliminates misleading "perfect" metrics from invalid datasets.
- **Decision**: **ACCEPTED**.
- **Action**: Reverted `DeviceTrustProvider` and `AccountTakeoverProvider` to heuristic rules and unsupervised anomaly skeletons.

## [2026-06-11] Experiment 3: Smishing Robustness via Deduplication
- **Hypothesis**: Cryptographic deduplication of messages will lower metrics but increase real-world generalization.
- **Audit Results**:
    - ROC AUC: 0.9916
    - F1: 0.8230
    - Rows reduced from 5572 to 5169.
- **Platform Improvement?**: YES. Reduces vocabulary memorization and over-fitting to specific UCI spam samples.
- **Decision**: **ACCEPTED**.
- **Action**: Serialized to `models/sms_scam_v2_dedup.joblib`.
