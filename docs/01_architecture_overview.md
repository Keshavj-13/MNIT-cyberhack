# 1. Architecture Overview

## 1.1 Platform Purpose

AURA is a multi-surface banking security platform that detects account takeover, payment fraud, phishing, smishing, device-risk, and network-risk signals in real time. It was designed as a production-grade prototype for the MNIT Cyberhack competition, combining isolated APIs, ML-driven risk scoring, cryptographic session management, and an autonomous AI investigator.

## 1.2 Four-Surface Isolation Architecture

The platform is split into four completely isolated product surfaces. Each surface has its own FastAPI backend, its own Vite/React frontend, its own authentication boundary, and its own CORS policy. No surface can call another surface's API.

| Surface | Backend Port | Frontend Port | Auth Model | Purpose |
|---------|:---:|:---:|---|---|
| **Customer Banking App** | 8001 | 3001 | JWT cookie + AES-256 AEAD encrypted payloads | Full banking flows: login, accounts, transfers, beneficiaries, SMS inbox |
| **Admin Security Dashboard** | 8002 | 3002 | JWT cookie | Risk monitoring, event investigation, ARIA investigations, provider health, config |
| **Attacker Threat Simulator** | 8003 | 3003 | JWT cookie, `sim_*` data isolation | Scripted and raw attack simulations against the risk engine |
| **Showcase Research Portal** | 8004 | 3004 | Public (read-only, no auth) | Model reports, dataset metadata, verification results for judges/reviewers |

### Isolation Rationale

Each surface binds to a distinct port pair and enforces strict CORS (only its own frontend origin is allowed). The Customer API encrypts all request/response payloads with per-session AES-256 keys. The Attacker API enforces `sim_*` prefixes on all user/session IDs to prevent simulation data from contaminating real customer records. The Showcase API is read-only with no credentials required.

### Architectural Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     AURA Platform                                │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │Customer  │  │Admin     │  │Attacker  │  │Showcase  │        │
│  │UI :3001  │  │UI :3002  │  │UI :3003  │  │UI :3004  │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │ AEAD        │ JWT        │ JWT+sim_*   │ public         │
│  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐        │
│  │Customer  │  │Admin     │  │Attacker  │  │Showcase  │        │
│  │API :8001 │  │API :8002 │  │API :8003 │  │API :8004 │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │              │              │              │              │
│       └──────────────┴──────────────┘              │              │
│                      │                              │              │
│              ┌───────▼──────────┐          ┌───────▼──────┐      │
│              │ Provider Registry│          │ Reports/     │      │
│              │ + Risk Engine    │          │ Datasets     │      │
│              └───────┬──────────┘          └──────────────┘      │
│                      │                                           │
│              ┌───────▼──────────┐                                │
│              │ SQLite DB        │                                │
│              │ security_platform│                                │
│              └──────────────────┘                                │
└──────────────────────────────────────────────────────────────────┘
```

## 1.3 Entry Points

### `run.py` — Platform Launcher

**Purpose**: Single command to start the entire platform.

**Algorithm**:
1. Kill any existing processes on all 8 ports (8001-8004, 3001-3004) using `netstat + taskkill` (Windows) or `fuser` (Linux).
2. Start 4 FastAPI backend processes via `uvicorn`, each bound to `127.0.0.1:800X`.
3. Wait 4 seconds for backends to boot.
4. Start 4 Vite dev server processes, each using its surface-specific `vite.config.ts`.
5. Enter a monitoring loop that detects if any subprocess exits unexpectedly.
6. On `Ctrl+C`, terminate all 8 processes.

**Input**: None (command-line invocation)  
**Output**: 8 running processes, console output with `[Surface Name]` prefixed log lines

### `seed_demo.py` — Demo Data Seeder

**Purpose**: Idempotent script that populates the database with demo data before a live demonstration.

**Algorithm**:
1. Ensure `demo_keshav` user exists with verified email/phone, hashed password (PBKDF2-SHA256, 260K iterations), and a recovery card (6×6 grid of random digits).
2. Seed 12 realistic Indian bank beneficiaries.
3. Create 4 security events with escalating risk (L1 ALLOW → L2 CHALLENGE → L3 RESTRICT → L4 CONTAIN) demonstrating a progressive ATO attack.
4. Create one ARIA investigation referencing those events.

**Input**: None  
**Output**: Populated `security_platform.db` with demo user, beneficiaries, events, investigation

## 1.4 Deployment Options

### Native Development
```bash
conda env create -f environment.yml
conda activate bank_threat
cd ui && npm install && cd ..
python run.py
```

### Docker (Windows Native)
```bash
build.bat    # builds qwen-base (once), app images, starts via Docker Desktop
```

Docker image structure:
- `Dockerfile` — slim Python base (no torch): Customer/Attacker/Showcase APIs
- `Dockerfile.admin` — extends `mnit-qwen-base`: Admin API with torch, SHAP, matplotlib, transformers
- `Dockerfile.qwen-base` — one-time build: torch CPU + Qwen3.5-0.8B weights baked in (~2GB)
- `ui/Dockerfile` — Node 20 multi-stage: builds all 4 frontend surfaces

### Configuration

- `environment.yml` — Conda environment specification
- `requirements.txt` — pip dependencies for all APIs
- `requirements-base.txt` — minimal deps (no torch) for Customer/Attacker/Showcase containers
- `requirements-admin.txt` — additional deps for Admin container (torch, transformers, SHAP)
- `config/risk_settings.json` — Configurable risk thresholds, provider weights, and transfer limits

## 1.5 End-to-End Data Flow

A typical interaction follows this pipeline:

```
User Action (click, type, transfer)
    │
    ▼
Customer UI (React) — captures keystroke/mouse/session telemetry
    │
    ▼  POST /customer/telemetry (encrypted via session AES key)
    │
Customer API — decrypts, stores TelemetryData in SQLite
    │
    ▼  User triggers action (e.g., transfer)
    │
    ▼  POST /customer/transfer (encrypted EncryptedPayload)
    │
Customer API → run_evaluation(payload, db)
    │
    ▼
evaluation_runner.py:
    1. Fetch all TelemetryData for this session
    2. FeatureExtractor.extract_features() → vectorized features
    3. Merge features into payload
    4. Fetch last 10 SecurityEvents for this user (history)
    5. Inject session_prior_risk if session already elevated
    6. RiskEngine.evaluate_all(enriched_payload, history)
    │
    ▼
RiskEngine:
    1. Load provider weights from config
    2. Contextual weight adjustment (new beneficiary → 1.5× Transaction weight)
    3. Each provider.evaluate(data) → RiskResult
    4. Weighted score fusion
    5. Session prior blending: score = min(1.0, score + prior * (1 - score))
    6. Attack-chain correlation multipliers (LURE→HOOK, EXPLOIT→MONETIZE)
    7. Threshold-based decision: ALLOW / CHALLENGE / RESTRICT / CONTAIN
    │
    ▼
evaluation_runner.py:
    1. Determine dominant event category
    2. Persist SecurityEvent to DB
    3. Return EngineResult to Customer API
    │
    ▼
Customer API:
    1. If escalation_level > current → shuffle_session_key() (rotate AES-256)
    2. If escalation_level == 4 → deactivate session (is_active=False)
    3. Encrypt response with (possibly new) session key
    4. Return encrypted response to UI
    │
    ▼
Customer UI:
    1. Decrypt response
    2. If key_rotated → update local AES key
    3. Show banking-language status ("Verification Required", "Transaction Under Review")
```

Meanwhile, running in parallel:
- **Admin Dashboard** polls `/admin/events`, `/admin/sessions`, `/admin/timeline` every few seconds
- **ARIA** runs a 12-second background scan loop, clustering SecurityEvents and creating investigations
