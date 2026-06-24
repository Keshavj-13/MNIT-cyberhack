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

SMISHING_SMS = "URGENT: Verify your identity at secure-bank.com immediately or your account will be suspended."
PHISHING_URL = "secure-bank.com"

DEMO_SCENARIOS: Dict[str, List[Dict[str, Any]]] = {
    "normal_customer": [
        {"label": "Customer logs in from their usual device.", "payload": {}},
        {"label": "Customer views the account dashboard.", "payload": {}},
        {"label": "Customer transfers $50 to a saved beneficiary.", "payload": {"amount": 50, "is_new_beneficiary": False}},
    ],
    "elderly_victim": [
        {"label": "Customer logs in normally.", "payload": {}},
        {"label": f"SMS arrives: \"{SMISHING_SMS}\"", "payload": {"sms_text": SMISHING_SMS}},
        {"label": "Customer taps the link and 'verifies' on the cloned page.", "payload": {"url": PHISHING_URL}},
        {"label": "Customer authorizes a 'verification transfer' of $250 to a new payee.", "payload": {"amount": 250, "is_new_beneficiary": True}},
    ],
    "smishing_victim": [
        {"label": "Customer logs in normally.", "payload": {}},
        {"label": f"SMS arrives: \"{SMISHING_SMS}\"", "payload": {"sms_text": SMISHING_SMS}},
        {"label": "Customer clicks the link and submits credentials on the cloned site.", "payload": {"url": PHISHING_URL}},
        {"label": "Harvested credentials are used to log in from a new device.", "payload": {"login_anomaly": True, "new_device": True}},
    ],
    "account_takeover": [
        {"label": "Login from an impossible-travel location with repeated failures.", "payload": {"login_anomaly": True, "failed_attempts": 5}},
        {"label": "Session continues on a VPN-masked, rooted device.", "payload": {"new_device": True, "vpn_detected": True, "rooted": True, "login_anomaly": True}},
        {"label": "Attacker attempts a large transfer to a newly added beneficiary.", "payload": {"amount": 15000, "is_new_beneficiary": True, "login_anomaly": True, "rooted": True}},
    ],
    "full_fraud_chain": [
        {"label": "Customer logs in normally.", "payload": {}},
        {"label": f"Smishing SMS arrives: \"{SMISHING_SMS}\"", "payload": {"sms_text": SMISHING_SMS}},
        {"label": "Customer clicks the link and submits credentials on the cloned site.", "payload": {"url": PHISHING_URL}},
        {"label": "Attacker logs in from a new, rooted, VPN-masked device using stolen credentials.", "payload": {"login_anomaly": True, "new_device": True, "rooted": True, "vpn_detected": True}},
        {"label": "Attacker drains funds to a new external account.", "payload": {"amount": 25000, "is_new_beneficiary": True, "login_anomaly": True, "rooted": True}},
    ],
}

@app.get("/attacker/scenarios")
def list_demo_scenarios(attacker = Depends(get_current_attacker)):
    return {name: [step["label"] for step in steps] for name, steps in DEMO_SCENARIOS.items()}

@app.post("/attacker/scenarios/{name}/run")
def run_demo_scenario(name: str, db: Session = Depends(get_db), attacker = Depends(get_current_attacker)):
    if name not in DEMO_SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {name}")

    # Generate isolated simulation identifiers with prefix "sim_"
    run_id = uuid.uuid4().hex[:8]
    sim_user_id = f"sim_{name}_{run_id}"
    sim_session_id = f"sim_{name}_{run_id}"

    steps = []
    for step in DEMO_SCENARIOS[name]:
        payload = {**step["payload"], "user_id": sim_user_id, "session_id": sim_session_id}
        # Injects direct telemetry if simulating lure hooks
        if "sms_text" in step["payload"]:
            db.add(TelemetryData(session_id=sim_session_id, type="session", data={"type": "sms_received", "sms_text": step["payload"]["sms_text"]}))
        if "url" in step["payload"]:
            db.add(TelemetryData(session_id=sim_session_id, type="session", data={"type": "link_clicked", "url": step["payload"]["url"]}))
        db.commit()
            
        result = run_evaluation(payload, db)
        steps.append({
            "label": step["label"],
            "payload": step["payload"],
            "result": {
                "overall_risk": result.overall_risk,
                "decision": result.decision,
                "escalation_level": result.escalation_level,
                "recommendation": result.recommendation,
                "why_decision": result.why_decision,
                "provider_breakdown": {k: v.dict() for k, v in result.provider_breakdown.items()}
            }
        })

    return {"user_id": sim_user_id, "session_id": sim_session_id, "steps": steps}

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
