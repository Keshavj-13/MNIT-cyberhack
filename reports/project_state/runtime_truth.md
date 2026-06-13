# Runtime Ground Truth: Banking Threat Detection Platform

## 1. Request Path Trace
**From Frontend Click to Backend Decision**

1.  **UI Trigger**: User interacts with `SecurityPlayground.tsx` (Manual Injection or Scenario Load).
2.  **API Call**: Frontend issues an `axios.post` to `/evaluate` (standardized to Port 8000). [**VERIFIED**]
3.  **Backend Entry**: `src/api/server.py` receives the request at the `/evaluate` endpoint. [**VERIFIED**]
4.  **Session Correlation**:
    *   The backend queries SQLite `security_events` for the last 10 events of the `user_id`. [**VERIFIED**]
    *   History is converted to `SessionEvent` objects and passed to `engine.evaluate_all(payload, history)`. [**VERIFIED**]
5.  **Risk Engine Execution**:
    *   `RiskEngine` (`src/engine/risk_engine.py`) iterates through providers registered in `ProviderRegistry`. [**VERIFIED**]
    *   `_apply_correlation` logic is triggered, checking for sequences like `LURE -> HOOK`. [**VERIFIED**]
6.  **Provider Evaluation**:
    *   Registered providers execute their `evaluate` method. [**VERIFIED**]
    *   Models are loaded once during provider initialization. [**VERIFIED**]
7.  **Final Response**: Engine aggregates scores, persists the new event to SQLite, and returns an `EngineResult` to the frontend. [**VERIFIED**]

---

## 2. Session History Propagation
- **Does RiskEngine receive history?** [**VERIFIED: YES**]
    - `src/api/server.py` explicitly fetches history from the database and passes it to `engine.evaluate_all`.
    - `src/engine/risk_engine.py` receives the `history` argument and uses it in `_apply_correlation`.

---

## 3. Frontend API Endpoints
- **Endpoints Called**:
    - `GET /scenarios`: Fetches pre-defined attack vectors. [**VERIFIED**]
    - `POST /evaluate`: Primary risk assessment endpoint. [**VERIFIED**]
    - `GET /timeline`: Fetches event history for the `Timeline` component. [**VERIFIED**]
- **Port Standardization**: All components (Vite proxy, `App.tsx`, `server.py`) now use Port **8000**. [**VERIFIED**]

---

## 4. Model Loading Status (Runtime)
- **Active Models (Successfully Loaded)**:
    - `models/transaction_fraud_v2_temporal.joblib` (V2) [**VERIFIED**]
    - `models/sms_scam_v2_dedup.joblib` (V2) [**VERIFIED**]
    - `models/phishing_provider_candidate.joblib` (V2) [**VERIFIED**]
    - `models/network_provider_candidate.joblib` (V2) [**VERIFIED**]
- **Rule-Based (No Model Loaded)**:
    - `DeviceTrustProvider`: Purely deterministic logic. [**VERIFIED**]
    - `AccountTakeoverProvider`: Purely deterministic logic. [**VERIFIED**]

---

## 5. Visual Asset Verification
- **README Screenshots**: `dashboard.png`, `playground.png`, `timeline.png`.
- **Status**: [**VERIFIED**]
    - Screenshots generated via Playwright and stored in `screenshots/`.
    - README paths resolve to valid image assets.

---

## 6. Legacy / Unused Files
- **`src/api/main.py`**: Legacy entry point. [**VERIFIED LEGACY**]
- **`src/ensemble.py`**: Legacy stateless engine. [**VERIFIED LEGACY**]
- **`src/config_handler.py`**: Legacy config loader. [**VERIFIED LEGACY**]
- **`src/providers/transaction.py` / `context.py`**: Superseded by `implementations.py`. [**VERIFIED LEGACY**]

---

## 7. Audit Evidence Summary

| Claim | Ground Truth Status | Evidence |
| :--- | :--- | :--- |
| System is stateful | **VERIFIED** | `src/api/server.py` fetches DB history. |
| V2 Models are integrated | **VERIFIED** | Providers updated to use candidate V2 models in `implementations.py`. |
| All providers are ML-based | **FALSE** | Device and ATO are rule-based in `src/providers/`. |
| Screenshots are present | **VERIFIED** | Generated and moved to `screenshots/`. |
| Frontend uses Port 8000 | **VERIFIED** | Frontend code and proxy updated to 8000. |
