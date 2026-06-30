# AURA Platform — Technical Documentation Index

> **AURA** (Autonomous Risk Intelligence Architecture) is a banking threat detection platform built for the MNIT Cyberhack context. It combines real-time behavioral biometrics, ML-driven risk scoring, and cryptographic session management across four isolated product surfaces.

## Documentation Structure

| # | Document | Description |
|---|----------|-------------|
| 1 | [Architecture Overview](01_architecture_overview.md) | Four-surface isolation model, deployment topology, entry points, and end-to-end data flow. |
| 2 | [Risk Engine & Feature Extraction](02_risk_engine.md) | Core scoring pipeline — telemetry ingestion, feature vectorization, weighted provider fusion, escalation thresholds, and attack-chain correlation. |
| 3 | [ML Providers Deep-Dive](03_ml_providers.md) | Per-provider analysis: datasets, model types, input schemas, scoring algorithms, and fallback logic for all six risk providers. |
| 4 | [ARIA & Explainability](04_aria_explainability.md) | Autonomous investigation agent loop, VLM integration, feature contribution charts, and kill-chain classification. |
| 5 | [Database & Security](05_database_security.md) | SQLite schema, session crypto (HMAC-CTR AEAD, JWT), password hashing, recovery card, ghost recipients, and migrations. |
| 6 | [API Surfaces](06_api_surfaces.md) | Endpoint-by-endpoint documentation for all four FastAPI backends (Customer, Admin, Attacker, Showcase). |
| 7 | [Research & Training Pipelines](07_research_pipelines.md) | Offline dataset acquisition, standardization, model training, hyperparameter optimization, and validation scripts. |
| 8 | [UI Surfaces](08_ui_surfaces.md) | Frontend architecture — Vite/React setup, per-surface components, telemetry collection, and encrypted communication. |

## Quick Reference

- **Launcher**: `python run.py` — starts 4 APIs (ports 8001-8004) + 4 Vite dev servers (ports 3001-3004)
- **Demo Seeder**: `python seed_demo.py` — creates demo user, beneficiaries, events, and ARIA investigation
- **Tests**: `python -m pytest tests/`
- **Docker**: `build.bat` (Windows) or `build.sh` (Linux)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy, SQLite |
| ML | LightGBM, XGBoost, scikit-learn, PyTorch (BEACON VarCNN) |
| Frontend | TypeScript, React 18, Vite |
| Crypto | Pure-Python HMAC-SHA256-CTR AEAD, HS256 JWT |
| AI Agent | ARIA + Qwen3.5-0.8B VLM |
