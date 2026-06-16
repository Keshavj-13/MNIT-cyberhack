# FINAL EVIDENCE REPORT: MNIT Security Platform Audit
**Timestamp (Start):** 2026-06-14 17:00:00
**Status:** CRITICAL FAIL - SYSTEM INTEGRITY COMPROMISED

## 1. Executive Summary
This report synthesizes evidence from 10 agent audits and direct code inspection. While the platform achieves "surface-level" functionality, it contains critical architectural flaws, security risks (PII leakage), and scientifically invalid models (data leakage).

## 2. Evidence Mapping

| CLAIM | EVIDENCE FILE | CODE LOCATION |
| :--- | :--- | :--- |
| **Global Keystroke Keylogging** | `ui/src/hooks/useTelemetry.ts` | `handleKeyDown` (Line 66), `handleKeyUp` (Line 79). Captures all keys (including passwords) in plaintext. |
| **Catastrophic Timestamp Corruption** | `src/api/server.py` | Line 103: `events_list = [{"type": e.type, "data": e.data, "timestamp": e.id} for e in telemetry_events]`. Uses DB ID as time proxy. |
| **Invalid Behavioral Features** | `src/engine/features.py` | `_extract_behavioral_features` (Line 43), `_extract_mouse_features` (Line 56). Math is corrupted by ID-as-timestamp bug. |
| **Risk Dilution Vulnerability** | `src/engine/risk_engine.py` | `evaluate_all` (Line 51). Uses simple weighted averaging which suppresses critical high-severity signals. |
| **ML Data Leakage (Environment)** | `src/train_official_models.py` | `train_environment_model` (Line 115). Fails to drop `TOTAL_FLOWS_EXP`, resulting in artificial 1.0 AUC. |
| **Stateful Attack Correlation** | `src/engine/risk_engine.py` | `_apply_correlation` (Line 94). Multipliers (1.3x, 1.5x) are hardcoded "magic numbers" without probabilistic basis. |
| **Unreliable Telemetry Buffer** | `ui/src/hooks/useTelemetry.ts` | `flushBuffer` (Line 144). Clears buffer BEFORE confirmation of successful API delivery. |
| **Realistic Transaction Metrics** | `reports/models/training_summary.json` | `transaction_risk` ROC AUC: 0.7886. Valid baseline for Feedzai BAF dataset. |

## 3. Real-Time Success Criteria Check

| CRITERIA | STATUS | EVIDENCE |
| :--- | :--- | :--- |
| **PII Protection** | **FAIL** | Keystrokes logged in plaintext (`useTelemetry.ts`). |
| **Behavioral Accuracy** | **FAIL** | Timestamps are corrupted by DB IDs (`server.py`). |
| **Model Validity** | **FAIL** | Environment model contains sequence leakage (`train_official_models.py`). |
| **Risk Sensitivity** | **FAIL** | High-risk signals are diluted by normalization (`risk_engine.py`). |

## 4. Final Recommendation
The system is **NOT production-ready**. Immediate remediation is required for PII filtering, timestamp logic, and model training pipelines.

**Timestamp (Finish):** 2026-06-14 17:15:00
