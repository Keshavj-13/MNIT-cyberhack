from src.config_handler import load_config
from src.providers import (
    TransactionRiskProvider, 
    NetworkRiskProvider, 
    DeviceTrustProvider, 
    ContextRiskProvider
)

class EnsembleEngine:
    def __init__(self):
        self.config = load_config()
        self.providers = {
            "transaction": TransactionRiskProvider(),
            "network": NetworkRiskProvider(),
            "device": DeviceTrustProvider(),
            "context": ContextRiskProvider()
        }

    def evaluate(self, data: dict) -> dict:
        weights = self.config["ensemble_weights"]
        rules = self.config["decision_rules"]
        
        results = {}
        all_factors = []
        
        final_score = 0.0
        weighted_confidence = 0.0
        
        for name, provider in self.providers.items():
            res = provider.score(data)
            results[name] = res
            
            w = weights.get(name, 0.0)
            final_score += res["score"] * w
            weighted_confidence += res["confidence"] * w
            all_factors.extend(res["factors"])
            
        # Decision Logic
        if final_score < rules["allow_threshold"]:
            decision = "ALLOW"
            recommended_action = "No action required"
        elif final_score < rules["block_threshold"]:
            decision = "CHALLENGE"
            recommended_action = "Request biometric verification"
        else:
            decision = "BLOCK"
            recommended_action = "Transaction blocked. Contact security."
            
        return {
            "final_risk_score": round(final_score, 2),
            "decision": decision,
            "confidence": round(weighted_confidence, 2),
            "top_factors": list(set(all_factors))[:5],
            "recommended_action": recommended_action,
            "component_scores": results
        }
