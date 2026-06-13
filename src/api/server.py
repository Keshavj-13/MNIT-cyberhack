from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import uvicorn
import os
import uuid

from src.db.models import SessionLocal, init_db, SecurityEvent, AuditLog
from src.engine.risk_engine import RiskEngine, EngineResult
from src.engine.registry import ProviderRegistry
from src.providers.implementations import (
    TransactionRiskProvider, PhishingRiskProvider, 
    SocialEngineeringRiskProvider, AccountTakeoverProvider, 
    DeviceTrustProvider, NetworkRiskProvider
)
from src.providers.placeholders import (
    BehavioralBiometricsProvider, 
    AuthenticationRiskProvider
)

app = FastAPI(title="mnit(cyberhack) Security Platform API")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Engine and Registry
def bootstrap_platform():
    init_db()
    registry = ProviderRegistry()
    registry.clear_registry()
    
    # Register Core Providers
    registry.register_provider(TransactionRiskProvider())
    registry.register_provider(PhishingRiskProvider())
    registry.register_provider(SocialEngineeringRiskProvider())
    registry.register_provider(AccountTakeoverProvider())
    registry.register_provider(DeviceTrustProvider())
    
    # Register Placeholders
    registry.register_provider(BehavioralBiometricsProvider())
    registry.register_provider(NetworkRiskProvider())
    registry.register_provider(AuthenticationRiskProvider())
    
    print(f"[BOOTSTRAP] {len(registry.get_providers())} providers registered.")

bootstrap_platform()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health():
    providers = ProviderRegistry.get_providers()
    return {
        "status": "healthy",
        "providers": [p.__class__.__name__ for p in providers],
        "model_status": {
            p.__class__.__name__: getattr(
                p, "model_info",
                {"model_path": None, "model_loaded": False, "model_class": None,
                 "mode": "placeholder", "note": "Zero-score stub, not yet implemented."}
            )
            for p in providers
        }
    }

from src.engine.session_models import SessionEvent

def _category_scores(breakdown: Dict[str, Any]) -> Dict[str, float]:
    # Max per-category provider sub-score for this event, e.g.
    # {"LURE": 0.94, "MONETIZE": 0.96}. Lets correlation logic check
    # category-specific evidence instead of the aggregate overall_risk.
    scores: Dict[str, float] = {}
    for res in (breakdown or {}).values():
        cat = res.get("event_category", "NEUTRAL")
        score = res.get("risk_score", 0.0)
        if score > scores.get(cat, 0.0):
            scores[cat] = score
    return scores

def _run_evaluation(payload: Dict[str, Any], db: Session) -> EngineResult:
    user_id = payload.get("user_id", "ANONYMOUS")
    session_id = payload.get("session_id", "DEFAULT")

    # 1. Fetch History (scoped to this user/session, so concurrent demo
    # sessions and Judge Mode runs don't pollute each other's attack chain)
    past_events_db = db.query(SecurityEvent).filter(
        SecurityEvent.user_id == user_id
    ).order_by(SecurityEvent.timestamp.desc(), SecurityEvent.id.desc()).limit(10).all()

    history = [
        SessionEvent(
            user_id=e.user_id,
            session_id=e.session_id,
            event_category=e.event_category,
            timestamp=e.timestamp,
            risk_score=e.overall_risk,
            confidence=e.confidence,
            explanations=[e.why_decision],
            input_payload=e.input_payload,
            category_scores=_category_scores(e.breakdown)
        ) for e in past_events_db
    ][::-1]  # Chronological

    # 2. Evaluate
    registry = ProviderRegistry()
    engine = RiskEngine(registry.get_providers())
    result = engine.evaluate_all(payload, history)

    # 3. Determine Dominant Category for this event
    # Find the provider with the highest score that isn't neutral
    dominant_cat = "NEUTRAL"
    max_sub_score = 0.5
    for res in result.provider_breakdown.values():
        if res.risk_score > max_sub_score:
            max_sub_score = res.risk_score
            dominant_cat = res.event_category

    # 4. Persist
    db_event = SecurityEvent(
        user_id=user_id,
        session_id=session_id,
        event_category=dominant_cat,
        input_payload=payload,
        overall_risk=result.overall_risk,
        decision=result.decision,
        escalation_level=result.escalation_level,
        confidence=result.confidence,
        breakdown={k: v.dict() for k, v in result.provider_breakdown.items()},
        recommendation=result.recommendation,
        why_decision=result.why_decision
    )
    db.add(db_event)
    db.commit()
    return result

@app.post("/evaluate", response_model=EngineResult)
def evaluate(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    return _run_evaluation(payload, db)

@app.get("/timeline", response_model=List[Dict[str, Any]])
def get_timeline(limit: int = 20, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(SecurityEvent)
    if user_id:
        query = query.filter(SecurityEvent.user_id == user_id)
    events = query.order_by(SecurityEvent.timestamp.desc(), SecurityEvent.id.desc()).limit(limit).all()
    return [{
        "id": e.id,
        "timestamp": e.timestamp.isoformat(),
        "overall_risk": e.overall_risk,
        "decision": e.decision,
        "level": e.escalation_level,
        "event_category": e.event_category,
        "recommendation": e.recommendation,
        "why_decision": e.why_decision,
    } for e in events]

@app.get("/scenarios")
def get_scenarios():
    return {
        "normal": {"amount": 50, "url": "bank.com", "sms_text": "Your statement is ready."},
        "suspicious_tx": {"amount": 6000, "is_new_beneficiary": True},
        "smishing": {"sms_text": "URGENT: Your account is BLOCKED. Visit bank-verify.com now."},
        "ato_attempt": {"login_anomaly": True, "failed_attempts": 4},
        "full_attack": {
            "sms_text": "URGENT: Verify identity at secure-bank.com",
            "url": "secure-bank.com",
            "login_anomaly": True,
            "new_device": True,
            "amount": 10000,
            "is_new_beneficiary": True
        }
    }

# --- Judge Mode: server-side scripted attack-chain sequences -------------
# Each scenario is a list of (label, payload) steps. Steps are evaluated and
# persisted in order under a fresh user_id/session_id so a judge can replay a
# full attack-chain narrative with one click, without polluting other runs.
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

@app.get("/demo/scenarios")
def list_demo_scenarios():
    return {name: [step["label"] for step in steps] for name, steps in DEMO_SCENARIOS.items()}

@app.post("/demo/scenarios/{name}/run")
def run_demo_scenario(name: str, db: Session = Depends(get_db)):
    if name not in DEMO_SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {name}")

    run_id = uuid.uuid4().hex[:8]
    user_id = f"judge_{name}_{run_id}"

    steps = []
    for step in DEMO_SCENARIOS[name]:
        payload = {**step["payload"], "user_id": user_id, "session_id": user_id}
        result = _run_evaluation(payload, db)
        steps.append({"label": step["label"], "payload": step["payload"], "result": result})

    return {"user_id": user_id, "session_id": user_id, "steps": steps}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
