# Decision Registry: Banking Threat Detection Platform

| Decision | Reason | Date | Status | Superseded By |
| :--- | :--- | :--- | :--- | :--- |
| **Temporal Split for Transaction Fraud** | Prevents future-information leakage; provides 'true' lower bound of performance. | 2026-06-11 | **ACCEPTED** | - |
| **Provider Rationalization (Device/ATO)** | Rejected proxy-trained models (Banknotes/Social Media) for truthfulness; reverted to rules/heuristics. | 2026-06-11 | **ACCEPTED** | - |
| **Smishing Deduplication** | Increases real-world generalization by reducing vocabulary memorization of UCI samples. | 2026-06-11 | **ACCEPTED** | - |
| **Modular Provider Architecture** | Allows independent development and scaling of risk domains (Transaction, Network, etc.). | 2026-06-10 | **ACCEPTED** | - |
| **Weighted Risk Fusion** | Simple, explainable baseline for risk aggregation across domains. | 2026-06-10 | **ACCEPTED** | `RiskEngine` correlation logic (Proposed) |
| **SQLite Persistence** | Low-overhead event logging for initial session tracking and auditing. | 2026-06-10 | **ACCEPTED** | - |
