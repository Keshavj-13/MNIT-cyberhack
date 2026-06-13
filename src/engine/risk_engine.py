from typing import List, Dict, Any
import yaml
import os
from src.providers.base import RiskProvider, RiskResult
from pydantic import BaseModel

class EngineResult(BaseModel):
    overall_risk: float
    decision: str
    escalation_level: int
    confidence: float
    provider_breakdown: Dict[str, RiskResult]
    recommendation: str
    why_decision: str

from src.engine.session_models import SessionEvent

class RiskEngine:
    def __init__(self, providers: List[RiskProvider], config_path: str = "config/risk_weights.yaml"):
        self.providers = providers
        self.weights = self._load_weights(config_path)
        
    def _load_weights(self, path: str) -> Dict[str, float]:
        if os.path.exists(path):
            with open(path, "r") as f:
                return yaml.safe_load(f).get("weights", {})
        # Default weights
        return {
            "TransactionRiskProvider": 0.4,
            "SocialEngineeringRiskProvider": 0.2,
            "PhishingRiskProvider": 0.15,
            "AccountTakeoverProvider": 0.15,
            "DeviceTrustProvider": 0.1
        }

    def evaluate_all(self, input_data: Dict[str, Any], history: List[SessionEvent] = []) -> EngineResult:
        results = {}
        total_score = 0.0
        total_weight = 0.0
        weighted_conf = 0.0
        
        for provider in self.providers:
            res = provider.evaluate(input_data)
            name = provider.__class__.__name__
            results[name] = res
            
            weight = self.weights.get(name, 0.05)
            total_score += res.risk_score * weight
            total_weight += weight
            weighted_conf += res.confidence * weight
            
        base_score = total_score / total_weight if total_weight > 0 else 0.0
        avg_conf = weighted_conf / total_weight if total_weight > 0 else 0.0
        
        # Stateful Correlation Logic
        final_score, correlation_expl = self._apply_correlation(base_score, results, history)
        
        return self._make_decision(final_score, avg_conf, results, correlation_expl)

    def _apply_correlation(self, base_score: float, current_results: Dict[str, RiskResult], history: List[SessionEvent]) -> tuple:
        score = base_score
        expl = ""
        
        # 1. Detection of LURE -> HOOK / EXPLOIT transition
        has_recent_lure = any(e.event_category == "LURE" and e.risk_score > 0.7 for e in history[-5:])
        has_recent_hook = any(e.event_category == "HOOK" and e.risk_score > 0.7 for e in history[-5:])
        
        current_cats = [r.event_category for r in current_results.values() if r.risk_score > 0.5]
        
        if has_recent_lure and ("HOOK" in current_cats or "EXPLOIT" in current_cats):
            score = min(1.0, score * 1.3)
            expl = "Risk elevated due to sequence: Previous SMISHING LURE followed by interaction."
            
        if (has_recent_lure or has_recent_hook) and "MONETIZE" in current_cats:
            score = min(1.0, score * 1.5)
            expl = "CRITICAL: Transaction attempt following confirmed Attack Chain (Lure/Hook)."

        return score, expl

    def _make_decision(self, score: float, conf: float, breakdown: Dict[str, RiskResult], correlation_expl: str) -> EngineResult:
        # ... (decision logic) ...
        if score < 0.2:
            level = 1
            decision = "ALLOW"
            rec = "Continue monitoring."
            why = "Low overall risk score."
        elif score < 0.4:
            level = 2
            decision = "CHALLENGE"
            rec = "Request Step-up Authentication (OTP/MFA)."
            why = "Moderate risk detected. Verification required."
        elif score < 0.7:
            level = 3
            decision = "RESTRICT"
            rec = "Block high-value transfers, freeze sensitive actions."
            why = "High suspicion. Restricting account capabilities."
        else:
            level = 4
            decision = "CONTAIN"
            rec = "Terminate session, lock account, escalate to security team."
            why = "Critical risk. Immediate containment required."
            
        if correlation_expl:
            why = f"{correlation_expl} {why}"
            
        return EngineResult(
            overall_risk=round(score, 4),
            decision=decision,
            escalation_level=level,
            confidence=round(conf, 4),
            provider_breakdown=breakdown,
            recommendation=rec,
            why_decision=why
        )
