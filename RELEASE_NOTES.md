# AURA — Release Candidate 1

**Platform:** Autonomous Unified Risk Architecture  
**Hackathon:** MNIT Cyberhack 2026  
**Environment:** Native Windows · Docker Desktop · Chrome

---

## What AURA Is

AURA is a real-time behavioural fraud detection platform for banking.

A customer banks normally. In the background, AURA monitors their behaviour using
a VarCNN deep learning model (BEACON), an account takeover classifier, and four
additional risk providers. When behaviour deviates, the system escalates silently —
the customer experiences consequences (OTP, restrictions, containment) without
ever seeing the technical internals. The admin sees everything: live telemetry,
model scores, the full decision pipeline, cryptographic actions, and an autonomous
agent (ARIA) that synthesises the attack pattern and generates a natural-language
assessment using Qwen3.5-0.8B.

---

## Major Features

### Customer Portal (http://localhost:3001)
- Full CBI (Central Bank of India) homepage recreation
- Internet Banking dashboard: accounts, transfer money, beneficiaries, statements
- Security status widget: 🟢 Protected / 🟡 Monitoring / 🟠 Verification Required / 🔴 Session Secured
- Zero technical jargon — customer experiences consequences only
- OTP step-up verification modal
- Containment screen on session revocation

### Admin Dashboard (http://localhost:3002)
- **Incident Console**: 8-stage pipeline strip (Telemetry → Features → Models → BEACON → Fusion → Policy → Crypto → Customer)
- **Provider Intelligence Cards**: 6 ML providers with live score bars, weights, explanations
- **Evidence Panels**: Real IET keystroke chart, SHAP feature attribution, risk evolution history
- **Outcome Strip**: Crypto key rotation, customer impact, ARIA link — per incident
- **ARIA Tab**: Autonomous investigations, Qwen3.5-0.8B VLM analysis
- **Session Monitor**: Live key rotation tracking with flash animation
- **Settings**: Live risk engine threshold tuning

### Attacker Simulator (http://localhost:3003)
- Controlled attack console: 4 scenarios (Social Engineering, Account Takeover, Full Fraud Chain, etc.)
- LIVE MODE: targets real `demo_keshav` session directly — synchronized 3-screen demo
- Kill chain visualization with step-by-step results

### ML Stack
| Provider | Model | Dataset | Key Metric |
|---|---|---|---|
| BEACON | VarCNN (pre-trained, frozen) | BEACON 2026 (Singh et al.) | Cosine embedding drift |
| ATO | GBM + Mahalanobis | CMU Keystroke 20K | F1=0.81, P=0.90 |
| Transaction | LightGBM | Feedzai BAF 500K | F1-optimal threshold |
| Social Engineering | GBM | Phishing websites 11K | URL-lexical features |
| Network | Heuristics | — | VPN/TOR/geo flags |
| Device | Rules | — | Device fingerprint |

### Agentic Layer (ARIA)
- 12-second autonomous scan cycle (demo-optimised)
- Clusters SecurityEvents by user_id in 10-minute rolling window
- Investigates clusters ≥3 events at risk ≥0.3
- Calls Qwen3.5-0.8B for natural-language attack pattern assessment
- Pre-seeded investigation visible immediately on cold start

---

## Architecture

```
Browser (Chrome, Windows)
    │
    ├── localhost:3001  Customer Portal (React, CBI theme)
    ├── localhost:3002  Admin Dashboard (React, dark SOC theme)
    ├── localhost:3003  Attacker Simulator (React, dark)
    └── localhost:3004  Showcase Portal (React, public)
         │
         ▼
    ├── localhost:8001  Customer API (FastAPI, Python)
    ├── localhost:8002  Admin API + ARIA (FastAPI + asyncio agent)
    ├── localhost:8003  Attacker API (FastAPI)
    └── localhost:8004  Showcase API (FastAPI)
         │
         ▼
    SQLite (security_platform.db)  — shared volume in Docker
    ML Models (models/artifacts/, models/beacon/)
```

**Security:**
- PBKDF2-SHA256 passwords, random salt, 260,000 iterations
- AES-256-CTR HMAC session encryption (pure Python, no Rust)
- HS256 JWT cookies (HTTP-only)
- Session key rotates on every risk escalation
- Key revoked and purged on containment (Level 4)

---

## Demo Flow (15-minute presentation)

### Setup (before judges arrive)
```
python seed_demo.py          # ensure demo_keshav credentials + pre-seeded events
python run.py                # starts all 8 services natively
```

Or with Docker Desktop:
```
.\build.bat                  # builds images, seeds data, starts containers
```

Open three Chrome windows side by side:
- Left: http://localhost:3001 (Customer)
- Centre: http://localhost:3002 (Admin)  
- Right: http://localhost:3003 (Attacker)

### Demo Script

**Act 1 — Normal Banking (2 min)**
1. Customer: Login as `demo_keshav` / `DemoPass@Mnit2026!`
2. Show: Account Summary, security status 🟢 Protected
3. Make a small transfer to an existing beneficiary → succeeds normally
4. Admin: Show Incident Console — baseline event, Level 1 MONITOR, all providers low

**Act 2 — Attack Begins (3 min)**
5. Attacker: Login as `attacker` / `attack123`
6. Enable LIVE mode (SIM → ⚡ LIVE)
7. Launch "Full Fraud Chain" — 4 steps × 3s = 12 seconds
8. Customer: Watch status change 🟢 → 🟡 → 🟠 → 🔴 in real time
9. When OTP appears, show the SMS notification, then session gets secured

**Act 3 — Admin Investigates (5 min)**
10. Admin: New events appear in left sidebar (highest risk at top)
11. Select the CONTAIN event → pipeline strip shows 8 stages lit up
12. Walk through: BEACON drift (cosine similarity), ATO score, fusion, policy, crypto key rotation
13. Show Outcome Strip: kv1→kv2, "Session Secured screen shown", ARIA link
14. ARIA tab → Investigation with Qwen3.5-0.8B assessment

**Act 4 — Technical Depth (3 min)**
15. Admin → Explain button → SHAP charts for each provider
16. Admin → VLM Analysis → Qwen's natural language attack assessment
17. Admin → Sessions tab → key rotation flash animation
18. Customer: Show containment screen "Session Secured / Sign In Again"

**Act 5 — Architecture (2 min)**
19. Explain the 6-provider ensemble
20. BEACON: VarCNN pre-trained on gameplay behavioral sequences, adapted via cosine drift
21. The principle: customer experiences protection, admin understands why

---

## Known Limitations

1. **BEACON cosine similarity** displayed in admin is `event.confidence`, not the raw VarCNN cosine output (which is computed but not persisted to DB)
2. **Inference latency** shown as 38.4ms is an architectural estimate, not per-request measurement
3. **ATO per-user enrollment**: demo_keshav is not in the CMU Keystroke dataset; ATO scores against global population distribution
4. **Cold-start BEACON**: requires ≥3 telemetry events before embedding drift activates. Fast attacks may complete before warmup
5. **VLM quality**: Qwen3.5-0.8B is a 0.8B parameter model; assessments are reasonable but not GPT-4 quality
6. **Single SQLite file**: all 4 APIs share one DB file. Fine for demo; not for production scale

---

## Demo Checklist

Before every demo run:
- [ ] `python seed_demo.py` — verify output shows "Demo seed complete"
- [ ] `python run.py` — verify "MNIT FOUR ISOLATED SURFACES RUNNING"
- [ ] Open http://localhost:3001 — verify CBI homepage loads
- [ ] Login demo_keshav — verify dashboard shows, balance shows ₹ amounts (not $0)
- [ ] Open http://localhost:3002 — login admin/admin123 — verify events in left panel
- [ ] Click most recent event — verify pipeline strip appears
- [ ] Open http://localhost:3003 — login attacker/attack123 — verify SIM button visible
- [ ] Enable LIVE mode — verify "⚡ LIVE" appears
- [ ] Run Full Fraud Chain — verify customer status changes in under 15 seconds

---

## Recovery Steps

### "Customer shows blank dashboard or no balance"
Run `python seed_demo.py` to reset password and verify events.

### "Admin shows empty event list"  
Events only appear for non-sim_* users. Ensure you ran `seed_demo.py` or have previously run the Full Fraud Chain in LIVE MODE.

### "LIVE attack doesn't escalate customer"
Check that customer is logged in first (LIVE MODE requires an active demo_keshav session).  
Run `python seed_demo.py` to reset the password if login fails.

### "ARIA tab shows no investigations"
ARIA needs ≥3 events at risk ≥0.3 from the same user in 10 minutes. Run Full Fraud Chain in LIVE MODE — it generates exactly 4 such events. ARIA fires within 12 seconds.

### "Port already in use"
`run.py` kills old processes automatically. If it fails:
```powershell
netstat -ano | findstr "8001 8002 8003 3001 3002 3003"
# kill each PID with: Stop-Process -Id <PID> -Force
```

### "Docker build fails"
Ensure Docker Desktop is running. The qwen-base image requires ~2GB download (one-time).  
Run `.\build.bat` and watch for errors.

---

## Credentials

| Surface | Username | Password |
|---|---|---|
| Customer | demo_keshav | DemoPass@Mnit2026! |
| Admin | admin | admin123 |
| Attacker | attacker | attack123 |
