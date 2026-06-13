from typing import Dict, Any
from src.providers.base import RiskProvider, RiskResult

class BehaviorRiskPlaceholderProvider(RiskProvider):
    """
    Placeholder for future BEACON integration.
    """
    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        res = self.score(data)
        return RiskResult(
            provider_name="BehaviorRisk",
            risk_score=res["score"],
            confidence=res["confidence"],
            severity="LOW",
            explanations=res["factors"],
            raw_features=data
        )

    def score(self, data: dict) -> dict:
        return {"score": 0.0, "confidence": 0.0, "factors": ["BEACON not integrated"]}
