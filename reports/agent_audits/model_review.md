# ML Model Audit Report

**Date**: 2026-06-11
**Auditor**: Gemini CLI (MODEL_REVIEW_AGENT)

## 1. Executive Summary
The model audit revealed a **Critical Data Leakage** in the Environment Risk Model and suspicious performance in the Behavioral Risk Model. While the Transaction and Intent models appear robust, the perfect metrics of the Environment model are a direct result of feature leakage. Dataset provenance is verified and legitimate across all models.

## 2. Detailed Findings

### 2.1 Environment Risk Model (Simargl 2021)
- **Status**: **FAILED AUDIT**
- **Metric**: ROC AUC 1.0000, F1 1.0000
- **Issue**: **Critical Feature Leakage**.
- **Evidence**:
    - The training script `src/train_official_models.py` explicitly drops `FLOW_ID` to prevent leakage.
    - However, it fails to drop `TOTAL_FLOWS_EXP`.
    - Verification confirmed that `TOTAL_FLOWS_EXP` is **identical** to `FLOW_ID` (a unique sequence identifier).
    - A Random Forest model can easily use this unique identifier to perfectly partition the data, especially if anomalies occur in specific temporal/sequential blocks.
- **Impact**: The model has zero generalization value and has merely "memorized" the dataset structure.

### 2.2 Behavioral Risk Model (CMU Keystroke)
- **Status**: **CAUTION**
- **Metric**: ROC AUC 0.9952
- **Issue**: Potential Over-optimism / Overfitting.
- **Analysis**:
    - While target leakage (ID) is handled by dropping `subject`, an AUC of 0.995 is exceptionally high for keystroke dynamics.
    - The dataset contains multiple "reps" of the same passphrase within the same session. If the train/test split is done randomly (as it is in `train_official_models.py`), samples from the same session appear in both sets.
- **Recommendation**: Implement a "Leave-One-Session-Out" or "GroupKFold" split to ensure the model generalizes to new sessions/days.

### 2.3 Intent Risk Model (SMS Spam)
- **Status**: **PASSED**
- **Metric**: ROC AUC 0.9934
- **Analysis**: This performance is consistent with state-of-the-art results on the UCI SMS Spam Collection dataset using TF-IDF and Random Forest. No obvious leakage detected.

### 2.4 Transaction Risk Model (Feedzai BAF)
- **Status**: **PASSED**
- **Metric**: ROC AUC 0.7886
- **Analysis**: Realistic performance on a notoriously difficult and imbalanced dataset. The low F1-score (0.11) reflects the model's struggle with extreme class imbalance, which is expected for this baseline.

## 3. Dataset Provenance Verification
All datasets used have been verified against their `manifest.json` metadata:

| Dataset | Source | License | Status |
|---------|--------|---------|--------|
| Feedzai BAF | Kaggle / NeurIPS 2022 | CC BY-NC-SA 4.0 | Verified |
| CMU Keystroke | Carnegie Mellon University | CC BY-NC 3.0 | Verified |
| SMS Spam | UCI Machine Learning Repo | CC BY 4.0 | Verified |
| Simargl 2021 | HuggingFace / Sensors | CC BY-SA 4.0 | Verified |

## 4. Required Remediation
1. **Fix Environment Risk Model**: Update `src/train_official_models.py` to drop `TOTAL_FLOWS_EXP` (and any other sequence-based identifiers like timestamps) before training.
2. **Refine Behavioral Model Evaluation**: Update the splitting logic to use `GroupKFold` based on `subject` or session-level grouping to provide a realistic AUC estimate.
3. **Re-train and Re-audit**: After fixes, all metrics must be re-validated.

---
*Report generated automatically. Finish Timestamp: 2026-06-11 12:48:00*
