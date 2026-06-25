import os
from fastapi import FastAPI, Depends, HTTPException, Body, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import uvicorn
import secrets

from src.db.models import SessionLocal, init_db, SecurityEvent, AriaInvestigation
from src.engine.registry import ProviderRegistry
from src.api.internal.session_crypto import verify_jwt_token, create_jwt_token, revoke_token
from src.explainability.explain import contributions_for_provider, make_chart, auto_summary
from src.api.internal.evaluation_runner import _registry

app = FastAPI(title="MNIT Admin Security Board API", version="1.0.0")

@app.on_event("startup")
async def on_startup():
    init_db()
    import asyncio
    from src.agents import aria
    asyncio.create_task(aria.run())

# Strict CORS: Allow only Admin frontend port 3002
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3002", "http://127.0.0.1:3002"],
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

def get_current_admin(authorization: Optional[str] = Cookie(None, alias="admin_session"), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Admin authorization cookie required")
    return verify_jwt_token(authorization, "admin", db)

# --- Admin Auth Routes ---

@app.post("/admin/auth/login")
def admin_login(payload: Dict[str, str] = Body(...), response: Response = Response(), db: Session = Depends(get_db)):
    username = payload.get("username")
    password = payload.get("password")
    
    # In a real app we'd verify admin credentials. For demo, we enforce a nominal password.
    _admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    _admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
    if username != _admin_user or password != _admin_pass:
        raise HTTPException(status_code=401, detail="Invalid administrator credentials")

    token = create_jwt_token(username, "admin", expires_in_minutes=15)
    response.set_cookie(
        key="admin_session", value=token, httponly=True,
        secure=os.environ.get("SECURE_COOKIES", "false").lower() == "true",
        samesite="strict", path="/admin"
    )
    return {"status": "success", "username": username}

@app.post("/admin/auth/logout")
def admin_logout(admin = Depends(get_current_admin), response: Response = Response(), db: Session = Depends(get_db)):
    jti = admin.get("jti")
    if jti:
        revoke_token(jti, db)
    response.delete_cookie(key="admin_session", path="/admin")
    return {"status": "success", "message": "Admin session closed."}

@app.get("/admin/auth/me")
def admin_me(admin = Depends(get_current_admin)):
    return {"user_id": admin.get("sub"), "role": "admin"}

# --- Monitoring & Risk Intelligence Feed ---

@app.get("/admin/events", response_model=List[Dict[str, Any]])
def list_events(limit: int = 50, user_id: Optional[str] = None, db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    query = db.query(SecurityEvent)
    # Hide simulation events from the core admin dashboard by default to avoid clutter
    query = query.filter(~SecurityEvent.user_id.like("sim_%"))
    if user_id:
        query = query.filter(SecurityEvent.user_id == user_id)
        
    events = query.order_by(SecurityEvent.timestamp.desc(), SecurityEvent.id.desc()).limit(limit).all()
    return [{
        "id": e.id,
        "user_id": e.user_id,
        "session_id": e.session_id,
        "timestamp": e.timestamp.isoformat(),
        "overall_risk": e.overall_risk,
        "decision": e.decision,
        "level": e.escalation_level,
        "event_category": e.event_category,
        "breakdown": e.breakdown,
        "recommendation": e.recommendation,
        "why_decision": e.why_decision,
    } for e in events]

@app.get("/admin/events/{event_id}", response_model=Dict[str, Any])
def get_event_detail(event_id: int, db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return {
        "id": event.id,
        "user_id": event.user_id,
        "session_id": event.session_id,
        "timestamp": event.timestamp.isoformat(),
        "event_category": event.event_category,
        "overall_risk": event.overall_risk,
        "confidence": event.confidence,
        "decision": event.decision,
        "level": event.escalation_level,
        "recommendation": event.recommendation,
        "why_decision": event.why_decision,
        "input_payload": event.input_payload,
        "breakdown": event.breakdown
    }

@app.get("/admin/timeline")
def admin_timeline(limit: int = 30, db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    # The complete chronological timeline feed including simulation events for audit tracking
    events = db.query(SecurityEvent).order_by(SecurityEvent.timestamp.desc(), SecurityEvent.id.desc()).limit(limit).all()
    return [{
        "id": e.id,
        "user_id": e.user_id,
        "session_id": e.session_id,
        "timestamp": e.timestamp.isoformat(),
        "overall_risk": e.overall_risk,
        "decision": e.decision,
        "level": e.escalation_level,
        "event_category": e.event_category,
        "why_decision": e.why_decision
    } for e in events]

@app.get("/admin/alerts")
def admin_alerts(db: Session = Depends(get_db), admin = Depends(get_current_admin)):
    # Returns critical high-level alerts (escalation >= 2)
    alerts = db.query(SecurityEvent).filter(SecurityEvent.escalation_level >= 2).order_by(SecurityEvent.timestamp.desc()).limit(20).all()
    return [{
        "id": a.id,
        "user_id": a.user_id,
        "level": a.escalation_level,
        "decision": a.decision,
        "overall_risk": a.overall_risk,
        "why_decision": a.why_decision,
        "timestamp": a.timestamp.isoformat()
    } for a in alerts]

@app.get("/admin/providers")
def get_providers(admin = Depends(get_current_admin)):
    # Live registry of model providers and their health statuses
    registry = ProviderRegistry()
    providers = registry.get_providers()
    return {
        "status": "active",
        "count": len(providers),
        "providers": [
            {
                "name": p.__class__.__name__,
                "category": getattr(p, "event_category", "NEUTRAL"),
                "model_loaded": getattr(p, "model_info", {}).get("model_loaded", False),
                "model_type": getattr(p, "model_info", {}).get("mode", "rules"),
                "model_path": getattr(p, "model_info", {}).get("model_path", None)
            }
            for p in providers
        ]
    }

@app.get("/admin/health")
def health(admin = Depends(get_current_admin)):
    return {"status": "healthy", "service": "admin_board"}

# ── Explainability ────────────────────────────────────────────────────────────

@app.get("/admin/events/{event_id}/explain")
def explain_event(event_id: int, admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if not event: raise HTTPException(404, "Event not found")
    payload = event.input_payload or {}
    result = {}
    for p in _registry.get_providers():
        name = p.__class__.__name__
        contribs = contributions_for_provider(p, payload)
        if not contribs: continue
        score = (event.breakdown or {}).get(name, {}).get("risk_score", event.overall_risk)
        result[name] = {
            "score": score,
            "contributions": contribs,
            "chart_png_b64": make_chart(contribs, name, score, event.decision),
            "summary": auto_summary(contribs, score),
        }
    return result


# ── ARIA investigations ───────────────────────────────────────────────────────

@app.get("/admin/aria/investigations")
def list_investigations(status: Optional[str] = None, limit: int = 20,
                         admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    q = db.query(AriaInvestigation)
    if status: q = q.filter(AriaInvestigation.status == status)
    invs = q.order_by(AriaInvestigation.created_at.desc()).limit(limit).all()
    return [{"id": i.id, "created_at": i.created_at.isoformat(), "cluster_key": i.cluster_key,
             "hypothesis": i.hypothesis, "classification": i.classification,
             "confidence": i.confidence, "status": i.status, "cycle": i.cycle,
             "event_count": len(i.cluster_event_ids or []),
             "vlm_assessment": i.vlm_assessment, "evidence_summary": i.evidence_summary}
            for i in invs]


@app.get("/admin/aria/investigations/{inv_id}")
def get_investigation(inv_id: int, admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    inv = db.query(AriaInvestigation).filter(AriaInvestigation.id == inv_id).first()
    if not inv: raise HTTPException(404, "Investigation not found")
    # regenerate charts for all cluster events on demand
    from src.explainability.explain import make_grid_chart
    events = db.query(SecurityEvent).filter(SecurityEvent.id.in_(inv.cluster_event_ids or [])).all()
    best = max(events, key=lambda e: e.overall_risk) if events else None
    charts = {}
    if best:
        for p in _registry.get_providers():
            name = p.__class__.__name__
            contribs = contributions_for_provider(p, best.input_payload or {})
            if contribs:
                score = (best.breakdown or {}).get(name, {}).get("risk_score", best.overall_risk)
                charts[name] = make_chart(contribs, name, score, best.decision)
    return {"id": inv.id, "cluster_key": inv.cluster_key, "hypothesis": inv.hypothesis,
            "classification": inv.classification, "confidence": inv.confidence,
            "status": inv.status, "cycle": inv.cycle,
            "cluster_event_ids": inv.cluster_event_ids,
            "vlm_assessment": inv.vlm_assessment, "evidence_summary": inv.evidence_summary,
            "charts": charts, "created_at": inv.created_at.isoformat()}


@app.patch("/admin/aria/investigations/{inv_id}/status")
def update_investigation_status(inv_id: int, payload: Dict[str, str] = Body(...),
                                 admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    inv = db.query(AriaInvestigation).filter(AriaInvestigation.id == inv_id).first()
    if not inv: raise HTTPException(404, "Investigation not found")
    status = payload.get("status", "")
    if status not in ("open", "resolved", "fp_confirmed"):
        raise HTTPException(400, "status must be open|resolved|fp_confirmed")
    inv.status = status; db.commit()
    return {"id": inv_id, "status": status}


if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="127.0.0.1", port=8002)
