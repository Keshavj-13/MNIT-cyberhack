from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import uvicorn
import os

from src.db.models import SessionLocal, init_db, SecurityEvent, AuditLog
from src.engine.risk_engine import RiskEngine, EngineResult
from src.engine.registry import ProviderRegistry
from src.providers.implementations import (
    TransactionRiskProvider, PhishingRiskProvider, 
    SocialEngineeringRiskProvider, AccountTakeoverProvider, 
    DeviceTrustProvider
)
from src.providers.placeholders import (
    BehavioralBiometricsProvider, NetworkRiskProvider, 
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
    return {"status": "healthy", "providers": [p.__class__.__name__ for p in ProviderRegistry.get_providers()]}

@app.post("/evaluate", response_model=EngineResult)
def evaluate(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    registry = ProviderRegistry()
    engine = RiskEngine(registry.get_providers())
    
    result = engine.evaluate_all(payload)
    
    # Persist Event
    db_event = SecurityEvent(
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
    
    # Audit log
    log = AuditLog(action="EVALUATION", details=f"Decision: {result.decision}, Risk: {result.overall_risk}")
    db.add(log)
    
    db.commit()
    return result

@app.get("/timeline", response_model=List[Dict[str, Any]])
def get_timeline(limit: int = 20, db: Session = Depends(get_db)):
    events = db.query(SecurityEvent).order_by(SecurityEvent.timestamp.desc()).limit(limit).all()
    return [{
        "id": e.id,
        "timestamp": e.timestamp.isoformat(),
        "overall_risk": e.overall_risk,
        "decision": e.decision,
        "level": e.escalation_level,
        "recommendation": e.recommendation
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
