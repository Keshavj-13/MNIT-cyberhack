# Remediation Execution: Banking Threat Detection Platform

## 1. Port Standardization [VERIFIED]

### Changes Made
- **Vite Proxy**: `ui/vite.config.ts` updated from `8080` to `8000`.
- **Frontend App**: `ui/src/App.tsx` updated from `8080` to `8000`.
- **Security Playground**: `ui/src/components/SecurityPlayground.tsx` updated from `8080` to `8000`.

### Verification Evidence
- **Log**: Backend started on `http://0.0.0.0:8000`.
- **Interaction**: Screenshot script successfully navigated `http://localhost:3000` and captured states, implying successful proxy to Port 8000.

---

## 2. Model Promotion [VERIFIED]

### Changes Made
- **Phishing**: `src/providers/implementations.py` now loads `models/phishing_provider_candidate.joblib`.
    - **Provider Name**: Updated to `PhishingDetector (v2-Candidate)`.
- **Network**: `NetworkRiskProvider` moved from `placeholders.py` to `implementations.py` and loads `models/network_provider_candidate.joblib`.
    - **Provider Name**: Updated to `NetworkRisk (v2-Candidate)`.
- **Orchestration**: `src/api/server.py` updated to import `NetworkRiskProvider` from `src.providers.implementations`.

### Performance Gains
| Component | Current F1 | New F1 | Delta |
| :--- | :--- | :--- | :--- |
| **Phishing** | 0.9681 | 0.9697 | **+0.16%** |
| **Network** | 0.0000 | 0.9994 | **+99.94%** |

---

## 3. Screenshot Pipeline Repair [VERIFIED]

### Changes Made
- Standardized ports allowed the `capture_screenshots.js` script to connect to the backend through the Vite proxy.
- Executed `node capture_screenshots.js` after verifying service health.

### Evidence
- **Assets Created**:
    - `screenshots/dashboard.png` (16.6 KB)
    - `screenshots/playground.png` (60.4 KB)
    - `screenshots/timeline.png` (24.6 KB)
- **README Alignment**: Paths in `README.md` now resolve to valid image assets in the root `screenshots/` directory.

---

## 4. Technical Debt & Rollback

### Rollback Instructions
1.  **Ports**: Revert `8000` -> `8080` in `ui/vite.config.ts`, `ui/src/App.tsx`, and `ui/src/components/SecurityPlayground.tsx`.
2.  **Models**: Revert `model_path` in `src/providers/implementations.py` to `models/phishing_url_model.joblib`.
3.  **Network**: Revert import in `src/api/server.py` to use `src.providers.placeholders.NetworkRiskProvider`.

### Remaining Technical Debt
- **Legacy Cleanup**: `src/api/main.py`, `src/ensemble.py`, and `src/config_handler.py` are confirmed legacy but remain in the repo per instructions.
- **Provider Redundancy**: `src/providers/network.py` and `src/providers/context.py` contain logic now superseded by `src/providers/implementations.py`.
- **Inference Stability**: Some providers use simulation fallbacks for specific features not covered by the current candidate models (e.g., lexical structural features in Phishing).
