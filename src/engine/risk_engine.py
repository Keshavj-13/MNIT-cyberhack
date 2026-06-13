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

    def evaluate_all(self, input_data: Dict[str, Any]) -> EngineResult:
        results = {}
        total_score = 0.0
        total_weight = 0.0
        weighted_conf = 0.0
        
        for provider in self.providers:
            res = provider.evaluate(input_data)
            name = provider.__class__.__name__
            results[name] = res
            
            weight = self.weights.get(name, 0.05) # Default small weight if not found
            total_score += res.risk_score * weight
            total_weight += weight
            weighted_conf += res.confidence * weight
            
        final_score = total_score / total_weight if total_weight > 0 else 0.0
        avg_conf = weighted_conf / total_weight if total_weight > 0 else 0.0
        
        return self._make_decision(final_score, avg_conf, results)

    def _make_decision(self, score: float, conf: float, breakdown: Dict[str, RiskResult]) -> EngineResult:
        # 4 Levels: MONITOR, CHALLENGE, RESTRICT, CONTAINMENT
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
            
        return EngineResult(
            overall_risk=round(score, 4),
            decision=decision,
            escalation_level=level,
            confidence=round(conf, 4),
            provider_breakdown=breakdown,
            recommendation=rec,
            why_decision=why
        )
