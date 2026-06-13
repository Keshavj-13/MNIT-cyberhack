# Experiment Registry: Banking Threat Detection Platform

| Hypothesis | Implementation | Result | Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| Enforcing zero-shuffling (temporal split) will reveal true fraud performance. | `src/research/phase_24_transaction.py` | ROC AUC: 0.9801, Recall: 0.7333 | `reports/research/decision_log.md` | **ACCEPTED** |
| Rejecting proxy-trained models for Device Trust will improve truthfulness. | Reversion to heuristic rules in `DeviceTrustProvider`. | Improved platform integrity. | `reports/research/decision_log.md` | **ACCEPTED** |
| Cryptographic deduplication of SMS messages will increase generalization. | `src/research/phase_24_smishing.py` | ROC AUC: 0.9916, Rows reduced (5572 -> 5169). | `reports/research/decision_log.md` | **ACCEPTED** |
| Multi-modal fusion of text and structural URL features improves detection. | `PhishingRiskProvider` lexical-structural fusion. | Ready for integration. | `reports/models/PhishingRiskProvider_research.md` | **PENDING** |
| Stateful correlation (LURE -> HOOK) reduces false negatives in multi-stage attacks. | `src/engine/risk_engine.py` logic. | Theoretical improvement; awaiting E2E validation. | `reports/research/attack_chain_architecture.md` | **PROPOSED** |
