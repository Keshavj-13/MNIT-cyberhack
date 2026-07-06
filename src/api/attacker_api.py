import os
from fastapi import FastAPI, Depends, HTTPException, Body, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import uvicorn
import secrets
import uuid

from src.db.models import SessionLocal, init_db, TelemetryData, SecurityEvent
from src.api.internal.session_crypto import verify_jwt_token, create_jwt_token, revoke_token
from src.api.internal.evaluation_runner import run_evaluation

app = FastAPI(title="MNIT Controlled Threat Simulation API", version="1.0.0")

@app.on_event("startup")
def on_startup():
    init_db()

# Strict CORS: Allow only Attacker frontend port 3003
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3003", "http://127.0.0.1:3003"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_attacker(authorization: Optional[str] = Cookie(None, alias="attacker_session"), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Attacker session cookie required")
    return verify_jwt_token(authorization, "attacker", db)

# --- Attacker Auth Routes ---

@app.post("/attacker/auth/login")
def attacker_login(payload: Dict[str, str] = Body(...), response: Response = Response(), db: Session = Depends(get_db)):
    username = payload.get("username")
    password = payload.get("password")
    
    _att_user = os.environ.get("ATTACKER_USERNAME", "attacker")
    _att_pass = os.environ.get("ATTACKER_PASSWORD", "attack123")
    if username != _att_user or password != _att_pass:
        raise HTTPException(status_code=401, detail="Invalid simulator credentials")

    token = create_jwt_token(username, "attacker")
    response.set_cookie(
        key="attacker_session", value=token, httponly=True,
        secure=os.environ.get("SECURE_COOKIES", "false").lower() == "true",
        samesite="strict", path="/attacker"
    )
    return {"status": "success", "username": username}

@app.get("/attacker/users")
def get_users(db: Session = Depends(get_db), attacker = Depends(get_current_attacker)):
    from src.db.models import User
    users = db.query(User).all()
    return [{"id": u.id, "username": u.username} for u in users]

@app.post("/attacker/auth/logout")
def attacker_logout(attacker = Depends(get_current_attacker), response: Response = Response(), db: Session = Depends(get_db)):
    jti = attacker.get("jti")
    if jti:
        revoke_token(jti, db)
    response.delete_cookie(key="attacker_session", path="/attacker")
    return {"status": "success", "message": "Simulation console closed."}

@app.get("/attacker/auth/me")
def attacker_me(attacker = Depends(get_current_attacker)):
    return {"user_id": attacker.get("sub"), "role": "attacker"}

# --- Scripted Scenario definitions ---

PHISHING_URL = "http://secure-bank.phish.ru/verify-identity"

# Each step label describes what AURA is *observing*, not the fictional backstory.
# Step 'anomaly' flag controls telemetry generation — normal steps produce realistic
# typing patterns so ATO doesn't misfire on a zero-feature baseline.
DEMO_SCENARIOS: Dict[str, List[Dict[str, Any]]] = {
    "normal_customer": [
        {"label": "Session established. Behavioral fingerprint collection begins. ATO model establishing keystroke baseline — moderate uncertainty is expected for new sessions before enrollment completes.", "payload": {}, "anomaly": False},
        {"label": "Dashboard navigation. Typing cadence and mouse dynamics consistent across both events. Risk stable as baseline accumulates.", "payload": {}, "anomaly": False},
        {"label": "Transfer ₹500 to a registered beneficiary. No phishing signals. No new payee. Transaction approved — risk held at current level.", "payload": {"amount": 500, "is_new_beneficiary": False}, "anomaly": False},
    ],
    "elderly_victim": [
        {"label": "Session established. Baseline keystroke timing collected. No anomaly signals.", "payload": {}, "anomaly": False},
        {"label": "Page load from an external domain flagged as phishing. Social-engineering risk provider activates.", "payload": {"url": PHISHING_URL}, "anomaly": False},
        {"label": "Paste event detected with digit content. Transfer ₹25,000 to a new unknown payee. Cumulative risk exceeds containment threshold.", "payload": {"amount": 25000, "is_new_beneficiary": True, "url": PHISHING_URL}, "anomaly": True},
    ],
    "phishing_victim": [
        {"label": "Session established. Behavioral baseline within normal range.", "payload": {}, "anomaly": False},
        {"label": "Navigation to a lookalike phishing domain. Social-engineering model scores 89%. Rapid focus-switching detected.", "payload": {"url": PHISHING_URL}, "anomaly": False},
        {"label": "Keystroke cadence collapses — copy-paste substitution for manual entry. BEACON cosine drift below threshold. ATO distance exceeds 3σ.", "payload": {"login_anomaly": True, "new_device": True, "url": PHISHING_URL}, "anomaly": True},
    ],
    "account_takeover": [
        {"label": "Login from an unrecognised device. Behavioral features absent (no keystroke history). Network risk: impossible geolocation.", "payload": {"login_anomaly": True, "failed_attempts": 5}, "anomaly": True},
        {"label": "Session continues on VPN-masked, rooted device. Device trust provider: integrity compromised. BEACON warmup bypassed.", "payload": {"new_device": True, "vpn_detected": True, "rooted": True, "login_anomaly": True}, "anomaly": True},
        {"label": "High-value transfer ₹75,000 to a new external beneficiary. LURE→MONETIZE attack-chain correlation fires. Containment triggered.", "payload": {"amount": 75000, "is_new_beneficiary": True, "login_anomaly": True, "rooted": True}, "anomaly": True},
    ],
    "full_fraud_chain": [
        {"label": "Session established by legitimate user. All six models at baseline. Session key v1 issued.", "payload": {}, "anomaly": False},
        {"label": "Phishing link clicked inside the banking session. Social-engineering score 89%. Page origin flagged as credential-harvesting domain.", "payload": {"url": PHISHING_URL}, "anomaly": False},
        {"label": "Session hijacked: adversarial keystroke cadence replaces legitimate user pattern. BEACON cosine similarity 0.89 — critical drift. ATO model: 94% confidence. Device: rooted, VPN-masked.", "payload": {"login_anomaly": True, "new_device": True, "rooted": True, "vpn_detected": True, "url": PHISHING_URL}, "anomaly": True},
        {"label": "Transfer ₹90,000 attempted to unregistered external account. EXPLOIT→MONETIZE correlation multiplier applied. Risk 100/100. Session revoked, AES key invalidated.", "payload": {"amount": 90000, "is_new_beneficiary": True, "login_anomaly": True, "rooted": True, "url": PHISHING_URL}, "anomaly": True},
    ],
}

@app.get("/attacker/scenarios")
def list_demo_scenarios(attacker = Depends(get_current_attacker)):
    return {name: [step["label"] for step in steps] for name, steps in DEMO_SCENARIOS.items()}

def generate_simulated_telemetry(step_idx: int, is_anomaly: bool, session_id: str, aes_key: str):
    """Generate synthetic telemetry that realistically represents either a genuine user
    or an adversary. Normal events use CMU-Keystroke-aligned dwell/flight distributions
    so the ATO GBM model scores them correctly instead of misfiring on zero features."""
    import random
    import json
    import time
    from src.api.internal.session_crypto import encrypt_aes_gcm

    events = []
    base_time = int(time.time() * 1000) - 200000 + (step_idx * 50000)

    for i in range(120):
        if is_anomaly:
            # Bimodal: machine-speed bursts (auto-clicker) + long pauses (operator hesitation)
            dt = int(random.uniform(1200, 2800)) if i % 6 == 0 else int(random.uniform(8, 35))
        else:
            # Normal human typing: roughly Gaussian centered ~160ms with realistic spread
            dt = max(30, int(random.gauss(160, 35)))
        base_time += dt

        if i % 3 < 2:  # 2 out of 3 events are keystrokes (realistic ratio)
            key_code = f"Key{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"
            if is_anomaly:
                # Adversarial: either very fast (scripted) or very slow (unfamiliar keyboard)
                dwell = int(random.uniform(180, 480)) if i % 4 == 0 else int(random.uniform(5, 25))
                flight = int(random.uniform(200, 600)) if i % 3 == 0 else int(random.uniform(5, 20))
            else:
                # Genuine user: dwell 60-130ms, flight 80-200ms — within CMU Keystroke normal range
                dwell = max(40, int(random.gauss(90, 20)))
                flight = max(50, int(random.gauss(130, 35)))
            events.append({
                "type": "keystroke", "timestamp": base_time,
                "data": {"event": "dwell", "dwellTime": dwell, "key": key_code[-1], "code": key_code}
            })
            events.append({
                "type": "keystroke", "timestamp": base_time + dwell,
                "data": {"event": "flight", "flightTime": flight, "key": key_code[-1], "code": key_code}
            })
        else:
            x = int(random.uniform(100, 1100))
            y = int(random.uniform(80, 700))
            # Normal: smooth human velocity; anomaly: machine-fast or erratic
            vel = random.uniform(0.4, 2.2) if not is_anomaly else random.choice([
                random.uniform(0.05, 0.15),   # robotic/scripted
                random.uniform(8.0, 18.0),    # erratic burst
            ])
            events.append({
                "type": "mouse", "timestamp": base_time,
                "data": {"event": "move", "x": x, "y": y, "velocity": vel}
            })

    plaintext = json.dumps({"events": events})
    encrypted = encrypt_aes_gcm(plaintext, aes_key)
    return {
        "session_id": session_id,
        "ciphertext": encrypted["ciphertext"],
        "nonce": encrypted["nonce"],
        "tag": encrypted["tag"]
    }

@app.post("/attacker/scenarios/{name}/run")
def run_demo_scenario(name: str, db: Session = Depends(get_db), attacker = Depends(get_current_attacker)):
    import time
    from src.db.models import CustomerSession
    from src.api.internal.session_crypto import generate_aes_key
    from src.api.customer_api import telemetry as customer_telemetry, shuffle_session_key
    
    if name not in DEMO_SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {name}")

    # Generate isolated simulation identifiers with prefix "sim_"
    run_id = uuid.uuid4().hex[:8]
    sim_user_id = f"sim_{name}_{run_id}"
    sim_session_id = f"sim_{name}_{run_id}"

    # 1. Initialize dynamic cryptographic session in DB
    aes_key = generate_aes_key()
    cust_session = CustomerSession(
        session_id=sim_session_id,
        user_id=sim_user_id,
        aes_key=aes_key,
        risk_level=1,
        key_version=1,
        is_active=True
    )
    db.add(cust_session)
    db.commit()

    # Silent warmup: run 3 normal evaluations to let the engine build a behavioral baseline
    # before scenario steps start. Without this, every first action scores high on ATO
    # because there's no session history to compare against.
    for w in range(3):
        warmup_tel = generate_simulated_telemetry(w, False, sim_session_id, cust_session.aes_key)
        try:
            customer_telemetry(warmup_tel, db)
        except Exception:
            pass
        run_evaluation({"user_id": sim_user_id, "session_id": sim_session_id}, db)

    steps = []
    for step_idx, step in enumerate(DEMO_SCENARIOS[name]):
        payload = {**step["payload"], "user_id": sim_user_id, "session_id": sim_session_id}

        # Anomaly flag comes from the step definition — keeps labels and telemetry in sync
        is_anomaly = step.get("anomaly", False)

        # Generate and POST encrypted telemetry package to production ingest pipeline
        telemetry_payload = generate_simulated_telemetry(step_idx, is_anomaly, sim_session_id, cust_session.aes_key)
        try:
            customer_telemetry(telemetry_payload, db)
        except HTTPException as e:
            pass # Session was likely contained/revoked in a previous step, ignore telemetry injection failure

        # 4. Inject scenario hooks (phishing, SMS flags)
        if "sms_text" in step["payload"]:
            db.add(TelemetryData(session_id=sim_session_id, type="session", data={"type": "sms_received", "sms_text": step["payload"]["sms_text"]}))
        if "url" in step["payload"]:
            db.add(TelemetryData(session_id=sim_session_id, type="session", data={"type": "link_clicked", "url": step["payload"]["url"]}))
            db.add(TelemetryData(session_id=sim_session_id, type="session", data={"url": step["payload"]["url"]}))
            payload["current_url"] = step["payload"]["url"]
        db.commit()
            
        # 5. Run evaluation (exact production path)
        start_time = time.perf_counter()
        result = run_evaluation(payload, db)
        latency = (time.perf_counter() - start_time) * 1000  # ms
        
        # 6. Apply dynamic key rotation if risk escalated
        key_rotated = False
        new_key = None
        new_version = cust_session.key_version
        if result.escalation_level > cust_session.risk_level:
            new_key, new_version = shuffle_session_key(cust_session, result.escalation_level, db)
            key_rotated = True

        steps.append({
            "label": step["label"],
            "payload": step["payload"],
            "result": {
                "overall_risk": result.overall_risk,
                "decision": result.decision,
                "escalation_level": result.escalation_level,
                "recommendation": result.recommendation,
                "why_decision": result.why_decision,
                "provider_breakdown": {k: v.dict() for k, v in result.provider_breakdown.items()},
                "latency_ms": latency,
                "key_rotated": key_rotated,
                "key_version": new_version
            }
        })

    return {"user_id": sim_user_id, "session_id": sim_session_id, "steps": steps}


@app.post("/attacker/scenarios/{name}/run-live")
def run_live_scenario(name: str, target_user: str = "keshav", db: Session = Depends(get_db), attacker = Depends(get_current_attacker)):
    """Run scenario against the REAL keshav session so all three surfaces synchronize.
    Unlike run, this does NOT use sim_* isolation — events appear in admin Risk Dashboard
    and the customer AURA console reacts (key rotation, trust level change).
    """
    import time
    from src.db.models import CustomerSession
    from src.api.customer_api import telemetry as customer_telemetry, shuffle_session_key

    if name not in DEMO_SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {name}")

    # Target the real user session — no sim_ prefix
    LIVE_USER = target_user
    cust_session = db.query(CustomerSession).filter(
        CustomerSession.user_id == LIVE_USER,
        CustomerSession.is_active == True
    ).order_by(CustomerSession.updated_at.desc()).first()

    if not cust_session:
        raise HTTPException(
            status_code=400,
            detail=f"No active session for '{LIVE_USER}'. Log in to the Customer Portal first, then run the live attack."
        )
    session_id = cust_session.session_id

    steps = []
    for step_idx, step in enumerate(DEMO_SCENARIOS[name]):
        payload = {**step["payload"], "user_id": LIVE_USER, "session_id": session_id}

        is_anomaly = step.get("anomaly", False)

        # inject telemetry into the REAL session
        telemetry_payload = generate_simulated_telemetry(step_idx, is_anomaly, session_id, cust_session.aes_key)
        try:
            customer_telemetry(telemetry_payload, db)
        except HTTPException as e:
            pass

        if "sms_text" in step["payload"]:
            db.add(TelemetryData(session_id=session_id, type="session", data={"type": "sms_received", "sms_text": step["payload"]["sms_text"]}))
        if "url" in step["payload"]:
            db.add(TelemetryData(session_id=session_id, type="session", data={"url": step["payload"]["url"]}))
            payload["current_url"] = step["payload"]["url"]
        db.commit()

        start_time = time.perf_counter()
        result = run_evaluation(payload, db)
        latency = (time.perf_counter() - start_time) * 1000

        key_rotated = False
        new_version = cust_session.key_version
        if result.escalation_level > cust_session.risk_level:
            new_key, new_version = shuffle_session_key(cust_session, result.escalation_level, db)
            key_rotated = True

        steps.append({
            "label": step["label"],
            "payload": step["payload"],
            "result": {
                "overall_risk": result.overall_risk,
                "decision": result.decision,
                "escalation_level": result.escalation_level,
                "recommendation": result.recommendation,
                "why_decision": result.why_decision,
                "provider_breakdown": {k: v.dict() for k, v in result.provider_breakdown.items()},
                "latency_ms": latency,
                "key_rotated": key_rotated,
                "key_version": new_version
            }
        })

        # pause between steps so customer UI (3s poll) can observe each escalation
        time.sleep(3)

    return {"user_id": LIVE_USER, "session_id": session_id, "steps": steps, "live": True}


# --- Raw Simulation & Evaluation Injection ---

@app.post("/attacker/evaluate/raw")
def attacker_evaluate(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db), attacker = Depends(get_current_attacker)):
    # Crucial Isolation Enforcement: user_id and session_id MUST be prefixed with "sim_"
    user_id = payload.get("user_id", "anon")
    if not user_id.startswith("sim_"):
        user_id = f"sim_{user_id}"
        
    session_id = payload.get("session_id", "default")
    if not session_id.startswith("sim_"):
        session_id = f"sim_{session_id}"
        
    enriched_payload = {**payload, "user_id": user_id, "session_id": session_id}
    
    # Run threat evaluation and return full raw EngineResult
    result = run_evaluation(enriched_payload, db)
    return result

@app.post("/attacker/simulate/event")
def inject_simulation_event(
    type: str = Body(..., embed=True),
    data: Dict[str, Any] = Body(..., embed=True),
    session_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    attacker = Depends(get_current_attacker)
):
    if not session_id.startswith("sim_"):
        session_id = f"sim_{session_id}"
        
    telemetry = TelemetryData(
        session_id=session_id,
        type=type,
        data=data
    )
    db.add(telemetry)
    db.commit()
    return {"status": "success", "message": "Simulation telemetry event injected."}

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="127.0.0.1", port=8003)
