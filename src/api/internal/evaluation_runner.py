import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from src.db.models import SecurityEvent, TelemetryData
from src.engine.risk_engine import RiskEngine, EngineResult
from src.engine.registry import ProviderRegistry
from src.engine.session_models import SessionEvent
from src.engine.features import FeatureExtractor
from src.providers.implementations import (
    TransactionRiskProvider, SocialEngineeringRiskProvider,
    AccountTakeoverProvider, DeviceTrustProvider,
    NetworkRiskProvider, BeaconBehavioralProvider
)

_registry = ProviderRegistry()
_registry.clear_registry()
_registry.register_provider(TransactionRiskProvider())
_registry.register_provider(SocialEngineeringRiskProvider())
_registry.register_provider(AccountTakeoverProvider())
_registry.register_provider(NetworkRiskProvider())
_registry.register_provider(DeviceTrustProvider())
_registry.register_provider(BeaconBehavioralProvider())

def _category_scores(breakdown: Dict[str, Any]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for res in (breakdown or {}).values():
        cat = res.get("event_category", "NEUTRAL")
        score = res.get("risk_score", 0.0)
        if score > scores.get(cat, 0.0):
            scores[cat] = score
    return scores

def run_evaluation(payload: Dict[str, Any], db: Session) -> EngineResult:
    user_id = payload.get("user_id", "ANONYMOUS")
    session_id = payload.get("session_id", "DEFAULT")

    # 1. Fetch live telemetry for this session to extract behavioral features
    telemetry_events = db.query(TelemetryData).filter(
        TelemetryData.session_id == session_id
    ).all()
    
    events_list = []
    for e in telemetry_events:
        ts_val = e.id
        if e.timestamp:
            try:
                ts_val = int(e.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
            except Exception:
                pass
        events_list.append({"type": e.type, "data": e.data, "timestamp": ts_val})
    
    extractor = FeatureExtractor()
    extracted_features = extractor.extract_features(events_list)
    
    # Merge extracted telemetry features into the model input payload
    enriched_payload = {**payload, **extracted_features}

    # 2. Fetch History (scoped to this user/session)
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

    # 3. Evaluate using the enriched payload, carrying forward session risk as a prior
    from src.db.models import CustomerSession
    current_session = db.query(CustomerSession).filter(CustomerSession.session_id == session_id).first()
    if current_session and current_session.risk_level > 1:
        # Blend current session risk level into the payload so the engine sees an elevated baseline
        enriched_payload["session_prior_risk"] = (current_session.risk_level - 1) * 0.25  # L2→+0.25, L3→+0.50
        enriched_payload["session_risk_level"] = current_session.risk_level

    engine = RiskEngine(_registry.get_providers())
    result = engine.evaluate_all(enriched_payload, history)

    # 4. Determine Dominant Category for this event
    dominant_cat = "NEUTRAL"
    max_sub_score = 0.5
    for res in result.provider_breakdown.values():
        if res.risk_score > max_sub_score:
            max_sub_score = res.risk_score
            dominant_cat = res.event_category

    # 5. Persist
    from src.db.models import CustomerSession
    sess = db.query(CustomerSession).filter(CustomerSession.session_id == session_id).first()
    prev_level = sess.risk_level if sess else 1
    prev_version = sess.key_version if sess else 1
    
    why_desc = result.why_decision
    if result.escalation_level > prev_level:
        why_desc = f"[CRYPTO ALERT] Session keys rotated (v{prev_version} -> v{prev_version + 1}), Cryptographic Tier escalated to Level {result.escalation_level} due to: {why_desc}"
    elif result.escalation_level < prev_level:
        why_desc = f"[CRYPTO INFO] Cryptographic Tier reduced to Level {result.escalation_level} (Authority restored) due to: {why_desc}"

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
        why_decision=why_desc
    )
    db.add(db_event)
    db.commit()
    return result
