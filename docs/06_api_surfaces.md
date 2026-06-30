# 6. API Surfaces

AURA exposes four distinct API surfaces, each bound to a specific port and serving a specific frontend. This strict isolation prevents cross-contamination of sessions and data.

---

## 6.1 Customer Banking API (Port 8001)

**File**: `src/api/customer_api.py`

The Customer API handles all real-user (or simulated victim) interactions with the banking application. It enforces strict cryptographic payload security.

### Key Security Features
- **Strict CORS**: Only accepts requests from `localhost:3001`.
- **JWT Authentication**: `HS256` token passed in the `customer_session` HTTPOnly cookie or `Authorization` header.
- **End-to-End AEAD Encryption**: All sensitive request bodies and responses are encrypted using `AES-GCM` (HMAC-CTR under the hood) with a dynamic session key.
- **Dynamic Key Rotation**: When the risk engine escalates a session's risk level, the API immediately shuffles the AES key, forcing the client to resynchronize or face a cryptographic lock-out.

### Endpoints

| Endpoint | Method | Encrypted Payload | Purpose |
|----------|--------|-------------------|---------|
| `/customer/auth/register` | POST | No | Create new user (requires strict password policy). |
| `/customer/auth/send-otp` | POST | No | Generate and send PBKDF2-hashed OTP to email/phone. |
| `/customer/auth/verify-otp` | POST | No | Verify OTP and mark contact channel as verified. |
| `/customer/auth/login` | POST | No | Verify credentials, issue JWT, and establish initial AES key. |
| `/customer/auth/logout` | POST | No | Blacklist JWT JTI and deactivate CustomerSession. |
| `/customer/auth/me` | GET | No | Returns basic session info (key version, risk level) to hydrate UI. |
| `/customer/auth/recovery-card`| GET | No | Returns base64 PNG of the user's 6x6 recovery grid. |
| `/customer/account` | POST | Yes | Fetch mocked banking balances. |
| `/customer/statements` | POST | Yes | Fetch mocked transaction history. |
| `/customer/beneficiaries` | POST | Yes | List saved payees, or add a new payee (triggers silent risk eval). |
| `/customer/transfer` | POST | Yes | Submit a transfer. Triggers full risk evaluation and possible escalation. |
| `/customer/telemetry` | POST | Yes (optional) | Ingest behavioral keystroke/mouse/session telemetry. |

---

## 6.2 Admin Security Board API (Port 8002)

**File**: `src/api/admin_api.py`

The Admin API serves the SOC (Security Operations Center) dashboard. It provides read-only views into the risk engine's state and ARIA's autonomous investigations.

### Key Security Features
- **Strict CORS**: Only accepts requests from `localhost:3002`.
- **JWT Authentication**: Requires `admin_session` cookie.

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/admin/auth/login` | POST | Admin login (demo uses hardcoded env credentials). |
| `/admin/events` | GET | List recent `SecurityEvent` records, sorted by risk. |
| `/admin/sessions` | GET | List all active customer sessions and their crypto states. |
| `/admin/sessions/{id}/live` | GET | Live telemetry, features, and risk breakdown for a specific session. |
| `/admin/sessions/{id}/timeline`| GET | Chronological event timeline (used for Watch panel). |
| `/admin/config` | GET/POST | Read or update engine weights and escalation thresholds. |
| `/admin/events/{id}` | GET | Detailed event view, generating Biometric Visuals (Timings, SHAP, etc). |
| `/admin/events/{id}/explain` | GET | Generate SHAP feature contribution charts for an event. |
| `/admin/events/{id}/analyze` | POST | Trigger on-demand VLM analysis for a specific event. |
| `/admin/aria/investigations` | GET | List ARIA clusters. |
| `/admin/aria/investigations/{id}`| GET | Get full ARIA investigation details (charts, VLM assessment). |

---

## 6.3 Attacker Threat Simulator API (Port 8003)

**File**: `src/api/attacker_api.py`

The Attacker API allows reviewers to simulate threats. It injects telemetry and triggers the risk engine exactly as the Customer API would, but carefully isolates the data.

### Key Security Features
- **Strict CORS**: Only accepts requests from `localhost:3003`.
- **Data Isolation (`sim_*`)**: All requests to `/raw` and `/run` force `user_id` and `session_id` to be prefixed with `sim_`. This ensures simulated data does not pollute the Admin dashboard's live view.

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/attacker/scenarios` | GET | List predefined threat scenarios (e.g., `elderly_victim`, `account_takeover`). |
| `/attacker/scenarios/{name}/run`| POST | Run a scenario in isolated mode (creates `sim_` user and session). Returns step-by-step risk escalation results. |
| `/attacker/scenarios/{name}/run-live`| POST | **DANGER**: Runs a scenario against the *live* `demo_keshav` session. This actively attacks the running Customer UI, triggering real-time key rotations and lockouts visible to the user. |
| `/attacker/evaluate/raw` | POST | Direct access to `run_evaluation()` for arbitrary payload testing. Forces `sim_` isolation. |
| `/attacker/simulate/event` | POST | Inject arbitrary telemetry events into a `sim_` session. |

---

## 6.4 Showcase Research Portal API (Port 8004)

**File**: `src/api/showcase_api.py`

The Showcase API is a public, read-only interface meant for hackathon judges and researchers to inspect the ML models without logging in.

### Key Security Features
- **Strict CORS**: Only accepts requests from `localhost:3004`.
- **No Auth**: Fully public.

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/model-reports` | GET | Aggregates training summaries, feature schemas, and explainability benchmarks for all registered ML providers. |
| `/verification-reports` | GET | Returns validation benchmark summaries (AUC, F1, PR-AUC) from offline test runs. |
| `/showcase/models` | GET | Alias for `/model-reports`. |
| `/showcase/datasets` | GET | Alias for `/verification-reports`. |
| `/showcase/papers` | GET | Returns mocked academic paper citations related to the models. |
