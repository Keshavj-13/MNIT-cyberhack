# Oversight Audit Report: Models & Fusion

**Date:** 2026-06-14
**Auditor:** OVERSIGHT_AGENT_2
**Audit Status:** FAIL - CRITICAL REMEDIATION REQUIRED

## 1. Executive Summary

This audit evaluates the implementation of Machine Learning Models and the Risk Fusion Engine against their respective review reports. Similar to the Telemetry audit (Oversight 1), this audit finds that the Implementation Agent failed to address critical scientific and architectural concerns raised by the Review Agent. 

Specifically, the **Environment Risk Model** remains scientifically invalid due to data leakage, and the **Risk Fusion Engine** contains structural vulnerabilities that allow high-severity threats to be "diluted" and ignored.

---

## 2. ML Models Audit

| Reviewer Concern | Valid? | Status in Code (`src/train_official_models.py`) |
| :--- | :--- | :--- |
| **Critical Data Leakage (Environment)** | **YES** | `TOTAL_FLOWS_EXP` is NOT dropped. This column is a sequence ID proxy, leading to the artificial 1.0 AUC. |
| **Over-optimistic Behavioral Split** | **YES** | Still uses `train_test_split` (random). `GroupKFold` by session was NOT implemented, leading to leakage of session patterns. |
| **Realistic Transaction Metrics** | **YES** | The ROC AUC of 0.78 is realistic; the implementation correctly identifies the challenge of the Feedzai BAF dataset. |
| **Intent Model Validity** | **YES** | Robust performance on SMS Spam is consistent with standard NLP benchmarks. |

### Severity: HIGH
The Environment model is a "black box" that has memorized the dataset index. It will fail completely on real-world network traffic where flow IDs are non-sequential or differently distributed. The Behavioral model's performance is likely inflated and may not generalize to new user sessions.

---

## 3. Risk Fusion Engine Audit

| Reviewer Concern | Valid? | Status in Code (`src/engine/risk_engine.py`) |
| :--- | :--- | :--- |
| **Risk Dilution Vulnerability** | **YES** | Implementation still uses simple weighted averaging. A "max signal" override for critical providers is missing. |
| **Hardcoded Magic Numbers** | **YES** | Multipliers (1.3, 1.5) and thresholds (0.2, 0.4, 0.7) remain hardcoded in Python instead of `risk_weights.yaml`. |
| **Negative Scaling (Normalization)** | **YES** | The `_normalize_weights` logic still dilutes core sensor weights as the number of registered providers increases. |
| **Confidence Dilution** | **YES** | Overall confidence is still a weighted average, allowing an "uncertain" primary provider to be drowned out by "certain" but irrelevant sensors. |

### Severity: CRITICAL
The "Dilution" vulnerability is a structural security flaw. Under current logic, a 100% certain "Account Takeover" signal (weight 0.15) could be averaged down to a "Low Risk" (0.15) if other sensors are silent, resulting in an **ALLOW** decision for a confirmed compromise.

---

## 4. Auditor Observations

1. **Failure to Iterate:** The Implementation Agent appears to have ignored the "Required Remediation" section of the `ML Model Audit Report` and the "Recommended Remediation" of the `Risk Fusion Engine Audit Report`.
2. **Persistence of Magic Numbers:** The reliance on hardcoded constants in the `RiskEngine` makes the system opaque to security analysts and impossible to tune without a full deployment cycle.
3. **Scientific Integrity:** The refusal to fix the `TOTAL_FLOWS_EXP` leakage suggests a priority on "perfect metrics" over actual detection capability.

## 5. Required Actions

1. **IMMEDIATE:** Update `src/train_official_models.py` to drop `TOTAL_FLOWS_EXP` and re-train the Environment model.
2. **REFACTOR:** Implement `GroupKFold` (by session) for the Behavioral model to get a valid performance estimate.
3. **RECODE:** Modify `RiskEngine.evaluate_all` to use a non-linear fusion approach: `final_score = max(weighted_sum, highest_critical_signal)`.
4. **EXTERNALIZZE:** Move all thresholds and multipliers from `src/engine/risk_engine.py` to `config/risk_weights.yaml`.

---
**Audit Started:** 2026-06-14 16:10:00
**Audit Finished:** 2026-06-14 16:25:00
