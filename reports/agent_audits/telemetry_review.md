# Telemetry Implementation Review: MNIT Security Platform
**Reviewer:** TELEMETRY_REVIEW_AGENT
**Timestamp (Start):** 2024-06-11 14:15:00 UTC
**Status:** CRITICAL FAIL - REVISION REQUIRED

## 1. Critical Logic & Data Bugs

### A. Non-Physical Feature Extraction (Backend)
- **Bug Location:** `src/engine/features.py` (via `src/api/server.py`)
- **Description:** The `FeatureExtractor` uses the database Primary Key (`e.id`) as a proxy for a time-based timestamp. 
- **Impact:** 
    - `avg_mouse_acceleration` is calculated as `delta_velocity / delta_id`, which is physically meaningless.
    - `mouse_click_density`, `navigation_speed`, and `interaction_density` are calculated by dividing counts by `(max_id - min_id) / 60000.0`. This treats database IDs as milliseconds, leading to wildly incorrect metrics.
    - **Result:** Behavioral biometrics models (like Account Takeover) are likely receiving garbage features, rendering the "Real Intelligence" claim in the audit report invalid.

### B. Broken Mouse Velocity Logic (Frontend)
- **Bug Location:** `ui/src/hooks/useTelemetry.ts`
- **Description:** `velocity` is calculated between the current move and the `lastMouseMove.current`. 
- **Impact:** If a user moves the mouse, stops for 1 minute, and moves it again, the velocity is calculated using `dt = 60000ms`. This produces an extremely low velocity that does not reflect actual user movement speed. It should reset if the gap exceeds a threshold.

### C. Mouse Path Straightness Inaccuracy
- **Bug Location:** `src/engine/features.py`
- **Description:** Straightness is calculated between the first and last mouse events of the *entire session*.
- **Impact:** If a user moves the mouse in a circle and then back to the start over a 10-minute session, the displacement is ~0, making "straightness" 0 regardless of individual movement quality. It must be calculated per-stroke or per-window.

---

## 2. Security & Privacy Risks

### A. PII / Sensitive Data Leak (High Risk)
- **Bug Location:** `ui/src/hooks/useTelemetry.ts`
- **Description:** The hook captures `key` and `code` for ALL `keydown` and `keyup` events globally.
- **Impact:** If the user types a password, credit card number, or PII into the `BankSimulator` (or any other part of the UI), it is recorded and sent to the backend in plain text.
- **Shortcut:** There is zero filtering or masking of sensitive fields.

---

## 3. Implementation Shortcuts & Technical Debt

### A. Unreliable Data Transmission
- **Shortcut:** `flushBuffer` clears the in-memory buffer *before* confirming the API request succeeded.
- **Impact:** If the network is flaky or the server returns a 500 error, the last 8 seconds of telemetry data are permanently lost. There is no retry logic or persistence (e.g., IndexedDB/localStorage backup).

### B. Cleanup & Unmount Data Loss
- **Shortcut:** Cleanup function in `useEffect` calls `flushBuffer()` using `axios.post`.
- **Impact:** Standard AJAX requests are frequently cancelled by browsers during page unload or navigation. `navigator.sendBeacon` should be used for the final flush to ensure delivery.

### C. Redundant Event Listeners
- **Shortcut:** `window.addEventListener` is called separately for the main handlers AND for `resetIdle` for the same events (`keydown`, `mousemove`, `click`).
- **Impact:** Increases overhead. `resetIdle` logic should be integrated into the primary handlers.

### D. Performance Bottleneck (Backend)
- **Shortcut:** `_run_evaluation` in `server.py` queries ALL telemetry events for the session on every single evaluation call.
- **Impact:** As session length increases, risk evaluation time will grow linearly (O(N)), eventually timing out the API.

---

## 4. Audit Report Critique

The `reports/agent_audits/telemetry_implementation.md` is **dangerously optimistic** and fails as a technical audit:
- It claims the system is "VERIFIED" and "LIVE" without checking if the data being collected is physically valid or used correctly by features.
- It fails to mention the massive privacy leak regarding plaintext keystroke logging.
- It describes the buffering logic as "Atomic Flush" to "prevent race conditions," ignoring the fact that it causes guaranteed data loss on network failure.

---

**Timestamp (Finish):** 2024-06-11 14:30:00 UTC
