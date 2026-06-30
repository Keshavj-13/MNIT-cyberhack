# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AURA Design Language (READ FIRST — applies to ALL UI and slides)

**White backgrounds, always.** Off-white / very-light-gray panels. Never pure-black or dark-mode backgrounds, never neon, gradients, glassmorphism, glowing borders, hacker-green, or "AI/cyberpunk" styling. If a past surface is dark, it is wrong and should be migrated to white.

AURA is **enterprise banking operations software** used by fraud analysts inside a national bank — not a "cybersecurity dashboard." It must communicate **trust, professionalism, clarity, accessibility, evidence**. Reference feel: Bloomberg Terminal density + Microsoft Defender organization + Azure Portal restraint + ServiceNow usability + IEEE conference figures + modern banking software. Calm, credible, expensive. When nothing is wrong, the interface should almost disappear.

- **Color:** predominantly white; slate/gray/navy/muted-blue for structure. Reserve **yellow/orange/red ONLY for actual incidents/severity** — color is never the only indicator (always pair with a label).
- **Typography:** large, readable, "boring," accessible — Office / Windows / government / banking feel. No tiny labels, no condensed/futuristic fonts. Assume every judge is 60+ and reads it from across a table. Big, thick, legible.
- **Information density:** high but not cluttered — tables, timelines, small charts, status chips, progress bars, sparklines, trend indicators instead of large decorative graphics. Strict grid: consistent spacing, margins, card heights. Whitespace is intentional. No floating/overlapping/decorative widgets.
- **Charts dominate** (esp. admin). Use **real charts backed by real backend state** — if a chart can't be generated from real data, remove it. Examples: live telemetry timelines, risk evolution, provider-contribution bars, BEACON confidence trend, behavioral drift, keystroke-timing histogram, mouse-velocity timeline, session event timeline, crypto state transitions, transfer-risk history, incidents by severity, escalation frequency, investigation queue, recovery stats.
- **IEEE figure style for all viz:** white background, thin gray gridlines, restrained colors, clear legends, axis labels, precise titles, readable type. No 3D, no shadows, no decoration. Publication-quality, not presentation-flashy.
- **Icons:** simple, monochrome, Material/Fluent style. Labels always accompany icons. No shields/padlocks/hacker symbols.
- **Motion:** minimal, only to communicate state changes (new incident slides in, chart updates, chip changes color). Never decorative.
- **Visual hierarchy:** Critical Alert → Current Incident → Evidence → Timeline → Provider Analysis → Historical Trends → Other Sessions. Answer "What is happening?" before "Why?" before "What should I do?"
- **Customer Portal:** looks like a real bank — white, clean, minimal, banking-only language. No telemetry/AI/crypto/engineering terms. Security surfaces as ordinary banking notices: "Protected", "Verification Required", "Transaction Under Review", "Additional Verification Needed", "Session Secured".
- **Admin Dashboard:** exposes everything (telemetry, BEACON, embeddings, provider scores, timelines, investigations, policy engine, crypto actions, inference latency, feature importance) but still resembles enterprise banking software, not a hacking dashboard.
- **Success criterion:** a context-free screenshot should read as "software used inside a bank or SOC," never "a hackathon AI project."

**Slides (PPTX):** same language — white/off-white, IEEE-style charts, big accessible fonts, banking look, NO product screenshots. Keep technical depth light (high-level only); the deep technical material belongs in the technical write-up, per the CBI POC guidelines.

## Running the platform

**Native (development):**
```bash
python run.py          # starts all 4 APIs (8001-8004) + kills previous processes
python seed_demo.py    # populate DB with demo user, 12 beneficiaries, recovery card, events
```

Each UI surface runs as a separate Vite dev server from `ui/`:
```bash
cd ui
npx vite --config surfaces/customer/vite.config.ts   # port 3001
npx vite --config surfaces/admin/vite.config.ts      # port 3002
npx vite --config surfaces/attacker/vite.config.ts   # port 3003
npx vite --config surfaces/showcase/vite.config.ts   # port 3004
```

Vite proxies must target `127.0.0.1:800X`, not `localhost:800X` — uvicorn binds to IPv4 only and Vite defaults to IPv6 `[::1]`.

**Docker (Windows native, no WSL):**
```bash
build.bat              # builds qwen-base once, then all app images, then starts via Docker Desktop
```
`build.bat` checks if `mnit-qwen-base` exists before building (skips 800MB download on subsequent runs). Subsequent code changes: `docker compose build ui && docker compose up -d ui` for frontend; `docker compose restart customer` for backend.

**Demo credentials:**
- Customer: `demo_keshav` / `DemoPass@Mnit2026!` (email: `demo@mnit.ac.in`)
- Admin: `admin` / `admin123`
- Attacker: `attacker` / `attack123`

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
- `src/api/internal/evaluation_runner.py` — shared evaluation pipeline (imports all providers, runs `RiskEngine`, persists `SecurityEvent`)
- `src/api/internal/session_crypto.py` — pure-Python HMAC-CTR AEAD + HS256 JWT (no Rust deps, works under Windows AppLocker)
- `src/api/internal/recovery_card.py` — `generate_card()` (6×6 grid of random digits), `make_challenge(n)` (pick random positions), `render_card_png()` (Pillow PNG, SVG fallback)

### Risk engine
`src/engine/risk_engine.py` → `RiskEngine.evaluate_all()` → weighted ensemble of all registered providers → returns `EngineResult` with `overall_risk`, `decision`, `escalation_level`, `provider_breakdown`, attack-chain correlation multipliers (LURE→MONETIZE, EXPLOIT→MONETIZE).

Decision thresholds (configurable in `config/risk_settings.json`):
- `< 0.2` → L1 ALLOW
- `0.2–0.4` → L2 CHALLENGE
- `0.4–0.7` → L3 RESTRICT
- `≥ 0.7` → L4 CONTAIN

**Cumulative/session prior risk:** `evaluation_runner.py` injects `session_prior_risk = (risk_level - 1) * 0.25` into the payload when a session is already elevated (L2→+0.25, L3→+0.50). `risk_engine.py` blends this as `score = min(1.0, score + prior * (1.0 - score))` before correlation, so risk accumulates across actions within a session.

`src/engine/features.py` → `FeatureExtractor` converts raw telemetry events (keystroke/mouse/session) stored in `TelemetryData` into the scalar features providers consume. Also emits `inter_event_timings` (raw ms deltas) for BEACON and `current_url` from `page_load` events for the phishing model.

### ML providers (`src/providers/implementations.py`)
All providers registered at import time in `evaluation_runner.py`. All torch-dependent classes are inside `if _TORCH:` guard so customer/attacker/showcase containers run without torch.

| Provider | Model | Dataset | Key feature |
|---|---|---|---|
| `TransactionRiskProvider` | LightGBM | Feedzai BAF 500K | 31 BAF features, F1-optimal threshold |
| `SocialEngineeringRiskProvider` | GBM | phishing_websites 11K | 8 URL-lexical features from `current_url` |
| `AccountTakeoverProvider` | GBM + RobustScaler | CMU Keystroke 20K | 10 aggregated dwell/flight/latency features |
| `NetworkRiskProvider` | Heuristics | — | vpn/tor/impossible_geo/blacklisted_ip flags |
| `DeviceTrustProvider` | Rules | — | rooted/vpn flags |
| `BeaconBehavioralProvider` | VarCNN `.pth` (frozen) | BEACON (Singh et al. 2026) | 512-d GAP embedding cosine drift + stat check |

Model artifacts live in `models/artifacts/` (joblib bundles with `{model, features, threshold, ...}`). BEACON weights at `models/beacon/best_model_varcnn_60WS_90OL_seq1024_thr0.99.pth`.

### BEACON integration detail
The pre-trained VarCNN (Singh et al. 2026, arXiv:2605.10867) was trained on gameplay behavioral sequences — **not retrained**. Architecture recovered from checkpoint keys: stem Conv1d(1,64,7) → 4 ResNet stages (64→128→256→512 via identity + projection blocks) → GAP(512) + metadata_fc(10→128) → classifier(640→28 classes).

At inference we use the **512-d GAP embedding**, not the 28-class softmax (class predictions collapse to user-02 due to distribution shift from banking data). Risk signal = cosine drift of the embedding versus a per-session baseline locked after 3 warmup events. Secondary stat check (mean IET + CV vs baseline) catches gradual drift that the embedding misses.

Input: `inter_event_timings` (raw ms deltas from telemetry, min-max normalised — NOT z-score, which collapses all distributions to N(0,1)) padded to 1024 points.

### Four-tier security escalation
Risk levels map to customer-facing consequences:

| Level | Decision | Customer experience | Recovery path |
|---|---|---|---|
| L1 | ALLOW | Normal banking | — |
| L2 | CHALLENGE | OTP required before sensitive actions | Enter email OTP via `POST /customer/auth/challenge-otp` |
| L3 | RESTRICT | Password reset required; sensitive ops locked | OTP + new password via `POST /customer/auth/password-reset` |
| L4 | CONTAIN | Session deactivated (`is_active=False`) | OTP + Recovery Card coordinates + new password via `POST /customer/auth/tier4-verify` |

**Key escalation behaviour:** `shuffle_session_key()` rotates the AES-256 session key on every level increase. L4 also sets `is_active=False`. The `get_current_user_payload` dependency only validates the JWT, not `is_active`, so recovery endpoints work even on deactivated sessions.

**Recovery Card:** Generated at enrollment via `generate_card()` — a 6×6 grid (columns A-F, rows 1-6) of random digits stored as JSON in `User.recovery_card_data`. `make_challenge(n=2)` picks random positions for the Tier 4 challenge. `render_card_png()` returns a Pillow PNG (or SVG fallback).

### Ghost recipient system
When a transfer or beneficiary add targets an unknown name, `_create_ghost_recipient()` creates a non-loginable `User` record (`is_active=False`, `is_ghost=True`) and a `Beneficiary` row. The risk engine sees `is_new_beneficiary=True`, boosting `TransactionRiskProvider` weight by 1.5× before normalisation. This makes "unknown recipient" a real signal without requiring pre-seeded recipients.

### Explainability + ARIA
`src/explainability/explain.py` — `contributions_for_provider()` computes top-5 feature contributions (importance × normalised value) for GBM models; `make_chart()` renders base64 PNG bar chart; `make_grid_chart()` stitches multi-provider charts for VLM.

`src/agents/aria.py` — autonomous background loop (12s scan cycle) that:
1. Clusters `SecurityEvent` by `user_id` in 10-min rolling window
2. Investigates clusters ≥3 events with risk ≥0.3
3. Classifies attack pattern, generates explainability charts, calls Qwen3.5-0.8B VLM
4. Persists `AriaInvestigation` to DB; admin board polls `/admin/aria/investigations`

ARIA starts via `asyncio.create_task(aria.run())` in `admin_api.py` startup. VLM: if `VLM_API_URL` env set → OpenAI-compatible remote endpoint; else → local `transformers` pipeline (Dockerfile.admin has weights baked in).

### Database
SQLite at `./security_platform.db` (configurable via `SQLALCHEMY_DATABASE_URL` env).

Tables: `SecurityEvent`, `TelemetryData`, `CustomerSession`, `User`, `OTPVerification`, `RevokedToken`, `AriaInvestigation`, `Beneficiary`.

Key non-obvious columns:
- `User.is_ghost` — non-loginable ghost account created for unknown transfer recipients
- `User.recovery_card_data` — JSON `{A1: 7, B3: 2, ...}` for Tier 4 challenges
- `CustomerSession.risk_level` — current escalation level (1–4); drives cumulative risk injection
- `OTPVerification.purpose` — `"registration"` vs `"security_challenge"` (Tier 2/3/4 OTPs)

Schema migrations in `models.py:_migrate_schema()` via raw `ALTER TABLE` — SQLite doesn't support adding columns in `CREATE TABLE IF NOT EXISTS`, so new columns are added there with `PRAGMA table_info()` guard.

### Admin API: Live session monitoring
`GET /admin/sessions/{session_id}/live` — returns session state, last 20 telemetry events, live `FeatureExtractor` output, and the latest provider breakdown. Admin UI polls this every 2 seconds when a session is selected in the Sessions tab (Watch button).

### Security model
- Passwords: PBKDF2-SHA256 with random salt, 260K iterations (stdlib, no bcrypt)
- Session keys: AES-256 (HMAC-CTR AEAD, pure Python) rotated on every escalation level increase
- JWT: pure-Python HS256, secrets from env vars (`CUSTOMER_JWT_SECRET`, etc.); defaults only if `ALLOW_DEFAULT_SECRETS=1`
- Telemetry endpoint requires valid active session (prevents score injection)
- Attacker API enforces `sim_*` prefix on all user/session IDs

## Docker image structure
- `Dockerfile` — slim base (python:3.12-slim + requirements-base.txt, no torch): customer/attacker/showcase APIs
- `Dockerfile.admin` — `FROM mnit-qwen-base:latest` + requirements-admin.txt: admin API with torch, shap, matplotlib, transformers
- `Dockerfile.qwen-base` — builds once: torch CPU + transformers + Qwen3.5-0.8B weights baked in (~2GB layer, cached by Docker)
- `ui/Dockerfile` — node:20-alpine multi-stage: builds all 4 surfaces, serves on 3001-3004
- `build.bat` — Windows-native Docker Desktop build script (no WSL required)

## Key env vars
| Var | Default | Notes |
|---|---|---|
| `ALLOW_DEFAULT_SECRETS` | — | Set to `1` in dev; suppresses JWT warning and exposes `dev_otp` in OTP responses |
| `SECURE_COOKIES` | `false` | Set `true` in HTTPS prod |
| `SQLALCHEMY_DATABASE_URL` | `sqlite:///./security_platform.db` | Override for Docker volume path |
| `VLM_API_URL` | — | If set, ARIA calls this OpenAI-compatible endpoint instead of local transformers |
| `VLM_MODEL` | `Qwen/Qwen3.5-0.8B` | Model name for VLM calls |
| `ADMIN_PASSWORD` / `ATTACKER_PASSWORD` | `admin123` / `attack123` | Override in prod |

## Code style
Follows `AGENTS.md` (ponytail / lazy senior dev ruleset): YAGNI, single-line where readable, comments explain WHY not WHAT, no abstractions beyond what the task requires, deletion over addition.
