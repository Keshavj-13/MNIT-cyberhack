from typing import Dict, Any
from src.providers.base import RiskProvider, RiskResult

class DeviceTrustProvider(RiskProvider):
    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        res = self.score(data)
        return RiskResult(
            provider_name="DeviceTrust",
            risk_score=res["score"],
            confidence=res["confidence"],
            severity="HIGH" if res["score"] > 0.7 else "LOW",
            explanations=res["factors"],
            raw_features=data
        )

    def score(self, data: dict) -> dict:
        """
        Rule based device trust scoring.
        Inputs: new_device, country_changed, vpn_detected, rooted_device, new_ip
        """
        score = 0.0
        factors = []
        
        if data.get("vpn_detected"):
            score += 0.4
            factors.append("VPN detected")
        if data.get("rooted_device"):
            score += 0.6
            factors.append("Rooted/Jailbroken device")
        if data.get("new_device"):
            score += 0.2
            factors.append("New device")
        if data.get("country_changed"):
            score += 0.3
            factors.append("Country changed")
        if data.get("new_ip"):
            score += 0.1
            factors.append("New IP address")
            
        score = min(1.0, score)
        # High confidence for rule-based systems
        confidence = 0.95
        
        return {"score": score, "confidence": confidence, "factors": factors}
