from src.providers.base import RiskProvider, RiskResult
from typing import Dict, Any

class BehavioralBiometricsProvider(RiskProvider):
    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        return RiskResult(
            provider_name="BehavioralBiometrics (Placeholder)",
            risk_score=0.0,
            confidence=0.0,
            severity="LOW",
            explanations=["Behavioral analysis module pending integration."],
            raw_features=data
        )

class NetworkRiskProvider(RiskProvider):
    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        return RiskResult(
            provider_name="NetworkRisk (Placeholder)",
            risk_score=0.0,
            confidence=0.0,
            severity="LOW",
            explanations=["Network telemetry module pending integration."],
            raw_features=data
        )

class AuthenticationRiskProvider(RiskProvider):
    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        return RiskResult(
            provider_name="AuthenticationRisk (Placeholder)",
            risk_score=0.0,
            confidence=0.0,
            severity="LOW",
            explanations=["Advanced MFA risk module pending integration."],
            raw_features=data
        )
