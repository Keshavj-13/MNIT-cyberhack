# 8. UI Surfaces

AURA's frontends are built using React 18 and Vite. They share a common tech stack but are deployed as completely separate monolithic applications, running on separate ports, communicating only with their respective backends.

---

## 8.1 Shared Architecture

All four UI surfaces (Customer, Admin, Attacker, Showcase) share these characteristics:
- **Build Tool**: Vite (`vite.config.ts`)
- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS (via `index.css`)
- **Icons**: Lucide React
- **HTTP Client**: Native `fetch` with credential inclusion

---

## 8.2 Customer Banking UI (Port 3001)

**Path**: `ui/surfaces/customer/`

The Customer UI is a fully functional banking simulation that secretly captures behavioral telemetry and negotiates cryptographic sessions with the backend.

### Key Components

- `App.tsx`: Main router and state holder. Manages the cryptographic state (`aesKey`, `keyVersion`, `sessionId`) and handles the AEAD encryption/decryption of API responses.
- `useTelemetry.ts`: A React hook that attaches global event listeners to the `window` object to capture:
  - `mousemove`, `click` (Mouse dynamics)
  - `keydown`, `keyup` (Keystroke dynamics)
  - `focus`, `blur` (Session context)
  - `paste` (Intent monitoring)
  It batches these events and flushes them to `/customer/telemetry` every few seconds, encrypting the payload with the current session key.
- `BankSimulator.tsx`: The primary banking dashboard layout.
- `TransferMoney.tsx`: The core transaction form. Initiating a transfer triggers a synchronous risk evaluation. The component listens for the `transfer_status` response and reacts to cryptographic escalations (e.g., showing a locked-out screen if containment is triggered).
- `PhishingPage.tsx`: A simulated phishing site used in demo scenarios to capture malicious intent.

### Cryptographic Synchronization

The UI maintains a state object:
```typescript
{ aesKey: string, keyVersion: number, sessionId: string, riskLevel: number }
```
When an API request is made:
1. The payload is JSON-stringified.
2. It is encrypted using AES-GCM (HMAC-CTR) with the current `aesKey`.
3. The encrypted blob, along with `session_id` and `key_version`, is sent to the API.
4. The response is decrypted.
5. If the response contains `key_rotated: true`, the UI immediately updates its `aesKey` and `keyVersion` to remain synchronized.

---

## 8.3 Admin Security Dashboard (Port 3002)

**Path**: `ui/surfaces/admin/`

The Admin UI is a SOC (Security Operations Center) dashboard providing real-time visibility into the risk engine and ARIA's investigations.

### Key Components

- `RiskDashboard.tsx`: Main dashboard view showing high-level stats, recent critical alerts, and active sessions.
- `Timeline.tsx`: A chronological feed of all security events across the platform.
- `ModelIntelligence.tsx`: A deep-dive view into a specific event. Displays:
  - The biometric timing sequence chart.
  - The temporal risk/confidence history chart.
  - SHAP attribution charts fetched from the `/admin/events/{id}/explain` endpoint.
  - ARIA's VLM assessments.

### Data Fetching
The Admin UI relies on aggressive polling (e.g., `setInterval` fetching `/admin/events` every 3-5 seconds) to ensure the SOC operator sees threat escalations in near real-time during a demo.

---

## 8.4 Attacker Threat Simulator (Port 3003)

**Path**: `ui/surfaces/attacker/`

A control panel for running scripted threat scenarios against the risk engine.

### Key Components

- `App.tsx`: Manages the simulation state and provides the UI to select and execute scenarios.
- The UI fetches predefined scenarios from `/attacker/scenarios`.
- When "Run Simulation" is clicked, it calls `/attacker/scenarios/{name}/run` (for isolated mode) or `/attacker/scenarios/{name}/run-live` (to actively attack the running customer session).
- Renders a step-by-step timeline of the attack, showing exactly how the risk engine reacted to each injected telemetry batch and transfer attempt.

---

## 8.5 Showcase Research Portal (Port 3004)

**Path**: `ui/surfaces/showcase/`

A read-only, public-facing portal for presenting the ML models, datasets, and research papers behind AURA.

### Key Components

- `App.tsx`: The main landing page.
- `ModelIntelligence.tsx`: (Different from the Admin version) Displays the ML model registry, fetching data from `/showcase/models`. Shows the input schemas, dataset names, and training metrics for the models.
- `DataVerification.tsx`: Displays the offline validation benchmarks (AUC, F1) fetched from `/showcase/datasets`.
