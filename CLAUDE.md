# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the platform

**Native (development):**
```bash
python run.py          # starts all 4 APIs (8001-8004) + kills previous processes
```

Each UI surface runs as a separate Vite dev server from `ui/`:
```bash
cd ui
npx vite --config surfaces/customer/vite.config.ts   # port 3001
npx vite --config surfaces/admin/vite.config.ts      # port 3002
npx vite --config surfaces/attacker/vite.config.ts   # port 3003
npx vite --config surfaces/showcase/vite.config.ts   # port 3004
```

**Docker (production-like):**
```bash
bash build.sh          # builds qwen-base once, then all app images, then starts
```
Build once: `wsl -d archlinux bash build.sh` from Windows. Uses `network_mode: host` + WSL2 mirrored networking (`.wslconfig` already set). Subsequent code changes: rsync src/ to `~/mnit/` in WSL and `docker compose restart <service>`.

**Rebuild only UI after code change:**
```bash
docker compose build ui && docker compose up -d ui
```

## Architecture

### Four isolated surfaces (API + UI pairs)
| Surface | API port | UI port | Auth |
|---|---|---|---|
| Customer banking | 8001 | 3001 | JWT cookie + AES-GCM encrypted payloads |
| Admin dashboard | 8002 | 3002 | JWT cookie |
| Attacker simulator | 8003 | 3003 | JWT cookie, writes `sim_*`-prefixed events only |
| Showcase portal | 8004 | 3004 | Public (read-only) |

All 4 UIs live under `ui/surfaces/{name}/` — each has its own `vite.config.ts`, `App.tsx`, and `index.html`. They share the root `ui/package.json` and `node_modules`.

### Backend entry points
- `src/api/{customer,admin,attacker,showcase}_api.py` — one FastAPI app per surface
- `src/api/internal/evaluation_runner.py` — shared evaluation pipeline (imports all providers, runs `RiskEngine`)
- `src/api/internal/session_crypto.py` — pure-Python HMAC-CTR AEAD + HS256 JWT (no Rust deps, works under Windows AppLocker)

### Risk engine
`src/engine/risk_engine.py` → `RiskEngine.evaluate_all()` → weighted ensemble of all registered providers → returns `EngineResult` with `overall_risk`, `decision`, `escalation_level`, `provider_breakdown`, attack-chain correlation multipliers (LURE→MONETIZE, EXPLOIT→MONETIZE).

`src/engine/features.py` → `FeatureExtractor` converts raw telemetry events (keystroke/mouse/session) stored in `TelemetryData` table into the scalar features that providers consume. Also emits `inter_event_timings` (raw ms deltas) for BEACON and `current_url` from `page_load` events for the URL phishing model.

`src/api/internal/evaluation_runner.py` → fetches telemetry for the session, extracts features, runs `RiskEngine`, persists `SecurityEvent` to DB.

### ML providers (`src/providers/implementations.py`)
All providers registered at import time in `evaluation_runner.py`. YAGNI: all torch-dependent classes are inside `if _TORCH:` guard so customer/attacker/showcase containers run without torch.

| Provider | Model | Dataset | Key feature |
|---|---|---|---|
| `TransactionRiskProvider` | LightGBM | Feedzai BAF 500K | Feedzai BAF 31 features, F1-optimal threshold |
| `SocialEngineeringRiskProvider` | GBM | phishing_websites 11K | 8 URL-lexical features from `current_url` |
| `AccountTakeoverProvider` | GBM + RobustScaler | CMU Keystroke 20K | 10 aggregated dwell/flight/latency features |
| `NetworkRiskProvider` | Heuristics | — | vpn/tor/impossible_geo/blacklisted_ip flags |
| `DeviceTrustProvider` | Rules | — | rooted/vpn flags |
| `BeaconBehavioralProvider` | VarCNN `.pth` (frozen) | BEACON (Singh et al. 2026) | 512-d GAP embedding cosine drift + stat check |

Model artifacts live in `models/artifacts/` (joblib bundles with `{model, features, threshold, ...}`). BEACON weights at `models/beacon/best_model_varcnn_60WS_90OL_seq1024_thr0.99.pth`.

### BEACON integration detail
The pre-trained VarCNN (Singh et al. 2026, arXiv:2605.10867) was trained on gameplay behavioral sequences — **not retrained**. Architecture recovered from checkpoint keys: stem Conv1d(1,64,7) → 4 ResNet stages (64→128→256→512 via identity + projection blocks) → GAP(512) + metadata_fc(10→128) → classifier(640→28 classes).

At inference we use the **512-d GAP embedding**, not the 28-class softmax (class predictions collapse to user-02 due to distribution shift from banking data). Risk signal = cosine drift of the embedding versus a per-session baseline locked after 3 warmup events. Secondary stat check (mean IET + CV vs baseline) catches gradual drift that the embedding misses.

Input: `inter_event_timings` (raw ms deltas from telemetry, min-max normalised to preserve timing shape — NOT z-score, which collapses all distributions to N(0,1)) padded to 1024 points.

### Explainability + ARIA
`src/explainability/explain.py` — `contributions_for_provider()` computes top-5 feature contributions (importance × normalised value) for GBM models; `make_chart()` renders base64 PNG bar chart; `make_grid_chart()` stitches multi-provider charts for VLM.

`src/agents/aria.py` — autonomous background loop (60s cycle) that:
1. Clusters `SecurityEvent` by `user_id` in 10-min rolling window
2. Investigates clusters ≥3 events with risk ≥0.3
3. Classifies attack pattern, generates explainability charts, calls Qwen3.5-0.8B VLM
4. Persists `AriaInvestigation` to DB; admin board polls `/admin/aria/investigations`

ARIA starts via `asyncio.create_task(aria.run())` in `admin_api.py` startup. VLM: if `VLM_API_URL` env set → OpenAI-compatible remote endpoint; else → local `transformers` pipeline (Dockerfile.admin has weights baked in).

### Database
SQLite at `./security_platform.db` (configurable via `SQLALCHEMY_DATABASE_URL` env). Tables: `SecurityEvent`, `TelemetryData`, `CustomerSession`, `User`, `OTPVerification`, `RevokedToken`, `AriaInvestigation`. Schema migrations in `models.py:_migrate_schema()` via raw `ALTER TABLE` (SQLite doesn't support `CREATE TABLE IF NOT EXISTS` for columns).

### Security model
- Passwords: PBKDF2-SHA256 with random salt (stdlib, no bcrypt)
- Session keys: AES-256 (HMAC-CTR AEAD, pure Python) rotated on escalation level increase
- JWT: pure-Python HS256, secrets from env vars (`CUSTOMER_JWT_SECRET`, etc.); defaults only if `ALLOW_DEFAULT_SECRETS=1`
- Telemetry endpoint requires valid active session (prevents score injection)
- Attacker API enforces `sim_*` prefix on all user/session IDs

## Docker image structure
- `Dockerfile` — slim base (python:3.12-slim + requirements-base.txt, no torch): customer/attacker/showcase APIs
- `Dockerfile.admin` — `FROM mnit-qwen-base:latest` + requirements-admin.txt: admin API with torch, shap, matplotlib, transformers
- `Dockerfile.qwen-base` — builds once: torch CPU + transformers + Qwen3.5-0.8B weights baked in (∼2GB layer, cached by Docker)
- `ui/Dockerfile` — node:20-alpine multi-stage: builds all 4 surfaces, serves on 3001-3004
- `build.sh` — checks if `mnit-qwen-base` exists before building (skip 800MB download on subsequent builds)

## Key env vars
| Var | Default | Notes |
|---|---|---|
| `ALLOW_DEFAULT_SECRETS` | — | Set to `1` in dev to suppress JWT secret warning |
| `SECURE_COOKIES` | `false` | Set `true` in HTTPS prod |
| `SQLALCHEMY_DATABASE_URL` | `sqlite:///./security_platform.db` | Override for Docker volume path |
| `VLM_API_URL` | — | If set, ARIA calls this OpenAI-compatible endpoint instead of local transformers |
| `VLM_MODEL` | `Qwen/Qwen3.5-0.8B` | Model name for VLM calls |
| `ADMIN_PASSWORD` / `ATTACKER_PASSWORD` | `admin123` / `attack123` | Override in prod |

## Code style
Follows `AGENTS.md` (ponytail / lazy senior dev ruleset): YAGNI, single-line where readable, comments explain WHY not WHAT, no abstractions beyond what the task requires, deletion over addition.
