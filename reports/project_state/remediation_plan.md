# Remediation Plan: Banking Threat Detection Platform

This plan outlines the steps required to align the platform implementation with the verified runtime truth and resolve architectural discrepancies.

## 1. Model Wiring Audit & Promotion

| Provider | Currently Loaded Model | Latest Model on Disk | Recommendation |
| :--- | :--- | :--- | :--- |
| **TransactionRisk** | `transaction_fraud_v2_temporal.joblib` | `transaction_fraud_v2_temporal.joblib` | **REMAIN**. Already using latest temporal split model. |
| **SocialEngineering**| `sms_scam_v2_dedup.joblib` | `sms_scam_v2_dedup.joblib` | **REMAIN**. Already using latest deduplicated model. |
| **PhishingRisk** | `phishing_url_model.joblib` | `phishing_provider_candidate.joblib` | **PROMOTE**. Candidate model is newer (17:44 vs 14:02). |
| **AccountTakeover** | Rules (Deterministic) | `ato_provider_candidate.joblib` | **STAY RULES**. Maintain rationalized deterministic logic for demo transparency. |
| **DeviceTrust** | Rules (Deterministic) | `device_provider_candidate.joblib` | **STAY RULES**. Maintain rationalized deterministic logic for demo transparency. |
| **NetworkRisk** | Placeholder (None) | `network_provider_candidate.joblib` | **PROMOTE**. Replace placeholder with candidate model. |

- **Risk Assessment**: Low. Promoting validated models improves detection accuracy without breaking the interface.
- **Evidence**: `ls -l models/` and `src/providers/implementations.py`.

## 2. Port Configuration Alignment

- **Issue**: Backend runs on **8000** (`server.py`), but Frontend expects **8080** (`App.tsx`, `vite.config.ts`).
- **Evidence**:
    - `src/api/server.py`: Line 139 (`port=8000`)
    - `ui/vite.config.ts`: Lines 11-13 (`proxy: ... 8080`)
    - `ui/src/components/SecurityPlayground.tsx`: Line 5 (`default 8080`)
- **Impact**: Frontend fails to connect to backend by default, breaking the "out-of-the-box" experience.
- **Fix**: Harmonize all components to use **8000** as the canonical port.
- **Effort**: Low (3 file edits).

## 3. Screenshot Failure Remediation

- **Issue**: README images are missing; `screenshots/` directory is empty.
- **Failure Chain**:
    1. `capture_screenshots.js` requires active services on specific ports.
    2. Port mismatch (8000/8080) causes frontend to show empty/error states.
    3. No automated trigger for the capture script.
- **Missing Assets**: `dashboard.png`, `playground.png`, `timeline.png`.
- **Fix**:
    1. Fix port discrepancy first.
    2. Ensure backend and frontend are running.
    3. Execute `node capture_screenshots.js` from the `ui/` directory.
- **Risk**: High (Visual only, but impacts first impression).

## 4. Legacy Artifact Decommissioning

| File | Status | Evidence |
| :--- | :--- | :--- |
| `src/api/main.py` | **LEGACY** | Not imported by `server.py` or any active component. |
| `src/ensemble.py` | **LEGACY** | Only imported by `main.py`. |
| `src/config_handler.py` | **LEGACY** | Only imported by `main.py`. |
| `src/providers/transaction.py` | **LEGACY** | Superseded by `implementations.py`. |
| `src/providers/context.py` | **LEGACY** | Superseded by `implementations.py`. |

- **Action**: Mark for removal or move to `archive/` to prevent confusion and reduce maintenance surface.
- **Evidence**: `Select-String` cross-references show zero active imports.

## 5. Summary Table

| Issue | Impact | Fix | Risk | Effort |
| :--- | :--- | :--- | :--- | :--- |
| **Model Drift** | Medium | Update `implementations.py` to use candidate models. | Low | Med |
| **Port Mismatch** | High | Standardize on Port 8000. | Low | Low |
| **Broken Images** | High | Run capture script after port fix. | Low | Low |
| **Dead Code** | Low | Archive `main.py`, `ensemble.py`, and legacy providers. | Low | Low |
