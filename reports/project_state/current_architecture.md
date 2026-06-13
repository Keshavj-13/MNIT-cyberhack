# System Architecture: Banking Threat Detection Platform

## A. System Architecture

### Backend
- **Framework**: FastAPI (Python)
- **Engine**: `src/engine/risk_engine.py` (Stateful RiskEngine with Attack Chain correlation).
- **Orchestration**: `src/api/server.py` (Active production server) bootstraps the `ProviderRegistry` and handles session history persistence.
- **Providers**: Modular pattern in `src/providers/`. Implementations in `src/providers/implementations.py`.
- **Database**: SQLite (`security_platform.db`) using SQLAlchemy (`src/db/models.py`).

### Frontend
- **Framework**: React / Vite / TypeScript (located in `ui/`).
- **Dashboard**: Displays real-time risk scores and decision recommendations.
- **Timeline**: Visualizes historical security events fetched from `/timeline`.

### Risk Engine
- **Aggregation**: Weighted arithmetic mean of provider scores.
- **Escalation Logic**: Threshold-based (ALLOW, CHALLENGE, RESTRICT, CONTAIN).
- **Correlation**: `RiskEngine` implements LURE -> HOOK/EXPLOIT correlation logic by analyzing the last 5 session events.

### Attack Chain Components
- **LURE**: Social Engineering / Smishing events.
- **HOOK**: Phishing URL interactions.
- **EXPLOIT**: Account Takeover / Device Anomaly.
- **MONETIZE**: Fraudulent Transactions.

## B. What Actually Exists

### Verified Code on Disk
- **Active Server**: `src/api/server.py` (Implements stateful `/evaluate` and `/timeline` endpoints).
- **Database Models**: `src/db/models.py` (SecurityEvent, AuditLog).
- **Providers**:
    - `TransactionRiskProvider`: Temporal split v2 model loaded from `models/transaction_fraud_v2_temporal.joblib`.
    - `SocialEngineeringRiskProvider`: Deduplicated v2 model loaded from `models/sms_scam_v2_dedup.joblib`.
    - `PhishingRiskProvider`: V2 Candidate model loaded from `models/phishing_provider_candidate.joblib`.
    - `NetworkRiskProvider`: V2 Candidate model loaded from `models/network_provider_candidate.joblib`.
    - `AccountTakeoverProvider`: Rule-based deterministic monitor.
    - `DeviceTrustProvider`: Rule-based hardware fingerprinting.
- **Stateful Engine**: `src/engine/risk_engine.py` (Verified `_apply_correlation` logic).
- **Models**: Serialized `.joblib` files for all domains in `models/`.

## C. What Is Claimed To Exist

- **Advanced State Machine**: While `_apply_correlation` exists, it is a heuristic correlation rather than a full Graph-based State Machine as proposed in research papers.

## D. Verification Status

| Component | Status | Evidence |
| :--- | :--- | :--- |
| **Modular Provider Pattern** | **VERIFIED** | `src/providers/base.py` and registry usage in `server.py`. |
| **Stateful Risk Engine** | **VERIFIED** | Integrated in `src/api/server.py`; history passed to `evaluate_all`. |
| **Attack Chain Correlation** | **VERIFIED** | `LURE -> HOOK` and `LURE/HOOK -> MONETIZE` logic in `RiskEngine`. |
| **Transaction Fraud v2** | **VERIFIED** | `models/transaction_fraud_v2_temporal.joblib` exists and is loaded. |
| **Smishing v2 (Dedup)** | **VERIFIED** | `models/sms_scam_v2_dedup.joblib` exists and is loaded. |
| **Device/ATO Rules** | **VERIFIED** | Rationalized to rules in `src/providers/implementations.py`. |
| **React Dashboard** | **VERIFIED** | Codebase in `ui/` folder; calls `/timeline` and `/evaluate`. |

## E. Open Technical Debt

1. **Graph-Based Attack Logic**: Moving from heuristic `if` statements in `_apply_correlation` to a formal DAG or State Machine.
2. **Legacy Files**: `src/api/main.py` and `src/ensemble.py` are stateless and confirmed legacy artifacts.

## F. Active Development Priorities

1. **Expand Correlation**: Adding more state transitions (e.g., `EXPLOIT -> MONETIZE`).
2. **UI Timeline Narrative**: Enhancing the frontend to show the "Narrative Chain" of the attack as described in research.
