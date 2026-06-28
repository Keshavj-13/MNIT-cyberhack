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

    token = create_jwt_token(username, "attacker", expires_in_minutes=60)
    response.set_cookie(
        key="attacker_session", value=token, httponly=True,
        secure=os.environ.get("SECURE_COOKIES", "false").lower() == "true",
        samesite="strict", path="/attacker"
    )
    return {"status": "success", "username": username}

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

DEMO_SCENARIOS: Dict[str, List[Dict[str, Any]]] = {
    "normal_customer": [
        {"label": "Customer logs in from their usual device.", "payload": {}},
        {"label": "Customer views the account dashboard.", "payload": {}},
        {"label": "Customer transfers $50 to a saved beneficiary.", "payload": {"amount": 50, "is_new_beneficiary": False}},
    ],
    "elderly_victim": [
        {"label": "Customer logs in normally.", "payload": {}},
        {"label": "Customer clicks a suspicious link received via message.", "payload": {"url": PHISHING_URL}},
        {"label": "Customer authorizes a 'verification transfer' of $250 to a new payee.", "payload": {"amount": 250, "is_new_beneficiary": True, "url": PHISHING_URL}},
    ],
    "smishing_victim": [
        {"label": "Customer logs in normally.", "payload": {}},
        {"label": "Customer clicks a phishing link in a spoofed bank alert.", "payload": {"url": PHISHING_URL}},
        {"label": "Stolen credentials are used to log in from a new device.", "payload": {"login_anomaly": True, "new_device": True, "url": PHISHING_URL}},
    ],
    "account_takeover": [
        {"label": "Login from an impossible-travel location with repeated failures.", "payload": {"login_anomaly": True, "failed_attempts": 5}},
        {"label": "Session continues on a VPN-masked, rooted device.", "payload": {"new_device": True, "vpn_detected": True, "rooted": True, "login_anomaly": True}},
        {"label": "Attacker attempts a large transfer to a newly added beneficiary.", "payload": {"amount": 15000, "is_new_beneficiary": True, "login_anomaly": True, "rooted": True}},
    ],
    "full_fraud_chain": [
        {"label": "Customer logs in normally.", "payload": {}},
        {"label": "Customer clicks a phishing link in a spoofed bank alert.", "payload": {"url": PHISHING_URL}},
        {"label": "Attacker logs in from a new, rooted, VPN-masked device using stolen credentials.", "payload": {"login_anomaly": True, "new_device": True, "rooted": True, "vpn_detected": True, "url": PHISHING_URL}},
        {"label": "Attacker drains funds to a new external account.", "payload": {"amount": 25000, "is_new_beneficiary": True, "login_anomaly": True, "rooted": True, "url": PHISHING_URL}},
    ],
}

@app.get("/attacker/scenarios")
def list_demo_scenarios(attacker = Depends(get_current_attacker)):
    return {name: [step["label"] for step in steps] for name, steps in DEMO_SCENARIOS.items()}

def generate_simulated_telemetry(step_idx: int, is_anomaly: bool, session_id: str, aes_key: str):
    import random
    import json
    import time
    from src.api.internal.session_crypto import encrypt_aes_gcm
    
    events = []
    # Generate 100 events to ensure we pass the 64-event cold-start check
    # Start timestamp in the past and increment
    base_time = int(time.time() * 1000) - 200000 + (step_idx * 50000)
    
    for i in range(100):
        if is_anomaly:
            # Highly skewed bimodal distribution (burst auto-clicks + heavy lagging delays)
            dt = int(random.uniform(1500, 3000)) if i % 5 == 0 else int(random.uniform(10, 40))
        else:
            # Consistent normal typing
            dt = int(random.gauss(150, 20))
        dt = max(10, dt)
        base_time += dt
        
        if i % 2 == 0:
            key_code = f"Key{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"
            dwell = int(random.uniform(50, 120)) if not is_anomaly else int(random.uniform(200, 500))
            flight = dt - dwell
            events.append({
                "type": "keystroke",
                "timestamp": base_time,
                "data": {"event": "dwell", "dwellTime": dwell, "key": key_code[-1], "code": key_code}
            })
            events.append({
                "type": "keystroke",
                "timestamp": base_time + dwell,
                "data": {"event": "flight", "flightTime": flight, "key": key_code[-1], "code": key_code}
            })
        else:
            x = int(random.uniform(100, 800))
            y = int(random.uniform(100, 600))
            vel = random.uniform(0.5, 2.5) if not is_anomaly else random.uniform(5.0, 15.0)
            events.append({
                "type": "mouse",
                "timestamp": base_time,
                "data": {"event": "move", "x": x, "y": y, "velocity": vel}
            })
            
    # Encrypt package using production AES-CTR (labeled AES-GCM)
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

    steps = []
    for step_idx, step in enumerate(DEMO_SCENARIOS[name]):
        payload = {**step["payload"], "user_id": sim_user_id, "session_id": sim_session_id}
        
        # 2. Determine anomaly status based on scenario timeline
        is_anomaly = False
        if name == "elderly_victim" and step_idx == 2:
            is_anomaly = True
        elif name == "smishing_victim" and step_idx >= 2:
            is_anomaly = True
        elif name == "account_takeover":
            is_anomaly = True
        elif name == "full_fraud_chain" and step_idx >= 2:
            is_anomaly = True

        # 3. Generate and POST encrypted telemetry package to production ingest pipeline
        telemetry_payload = generate_simulated_telemetry(step_idx, is_anomaly, sim_session_id, cust_session.aes_key)
        customer_telemetry(telemetry_payload, db)

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
def run_live_scenario(name: str, db: Session = Depends(get_db), attacker = Depends(get_current_attacker)):
    """Run scenario against the REAL demo_keshav session so all three surfaces synchronize.
    Unlike run, this does NOT use sim_* isolation — events appear in admin Risk Dashboard
    and the customer AURA console reacts (key rotation, trust level change).
    """
    import time
    from src.db.models import CustomerSession
    from src.api.customer_api import telemetry as customer_telemetry, shuffle_session_key

    if name not in DEMO_SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {name}")

    # Target the real demo_keshav session — no sim_ prefix
    LIVE_USER = "demo_keshav"
    cust_session = db.query(CustomerSession).filter(
        CustomerSession.user_id == LIVE_USER,
        CustomerSession.is_active == True
    ).order_by(CustomerSession.updated_at.desc()).first()

    if not cust_session:
        raise HTTPException(status_code=404, detail="demo_keshav session not found. Customer must be logged in first.")

    session_id = cust_session.session_id

    steps = []
    for step_idx, step in enumerate(DEMO_SCENARIOS[name]):
        payload = {**step["payload"], "user_id": LIVE_USER, "session_id": session_id}

        is_anomaly = (name == "full_fraud_chain" and step_idx >= 2) or \
                     (name == "account_takeover") or \
                     (name == "smishing_victim" and step_idx >= 2) or \
                     (name == "elderly_victim" and step_idx == 2)

        # inject telemetry into the REAL session
        telemetry_payload = generate_simulated_telemetry(step_idx, is_anomaly, session_id, cust_session.aes_key)
        customer_telemetry(telemetry_payload, db)

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
