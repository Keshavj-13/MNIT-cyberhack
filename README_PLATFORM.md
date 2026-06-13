# MNIT Security Platform

A production-style banking threat detection platform featuring multi-provider risk analysis, real-world attack chain modeling, and a 4-level automated escalation system.

## Core Features

- **Provider-Based Architecture**: Modular system allowing for seamless integration of new risk models.
- **Attack Chain Timeline**: Accumulative risk visualization across the kill chain (Phishing -> ATO -> Fraud).
- **Escalation Engine**: Automated movement between MONITOR, CHALLENGE, RESTRICT, and CONTAINMENT levels.
- **Security Playground**: Live simulation of attack vectors (SMS, URLs, Device, Logins).
- **Auditability**: SQLite persistence of all events with SHAP-based risk explanations.

## Quick Start

1. **Activate Environment**:
   ```bash
   conda activate bank_threat
   ```

2. **Launch Platform**:
   ```bash
   python run.py
   ```

3. **Access UI**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy, SQLite, Pydantic.
- **Frontend**: React, TypeScript, Vite, Tailwind CSS, Lucide Icons.
- **Models**: LightGBM, XGBoost, CatBoost, TF-IDF (Scam/Phishing).
