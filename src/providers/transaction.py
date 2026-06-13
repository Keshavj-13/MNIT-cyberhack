import joblib
import pandas as pd
from typing import Dict, Any
from src.providers.base import RiskProvider, RiskResult

class TransactionRiskProvider(RiskProvider):
    def __init__(self, model_path="models/transaction_model.joblib", importance_path="models/transaction_importance.joblib"):
        try:
            self.model = joblib.load(model_path)
            self.importance = joblib.load(importance_path)
        except:
            self.model = None
            self.importance = {}

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        res = self.score(data)
        return RiskResult(
            provider_name="TransactionRisk",
            risk_score=res["score"],
            confidence=res["confidence"],
            severity="HIGH" if res["score"] > 0.7 else "LOW",
            explanations=res["factors"],
            raw_features=data
        )

    def score(self, data: dict) -> dict:
        if self.model is None:
            return {"score": 0.5, "confidence": 0.0, "factors": ["Model not loaded"]}
        
        # Mapping input data to features
        features = [
            'amount', 'currency', 'transaction_type', 'merchant_category', 
            'account_age_days', 'tx_velocity_24h', 'amount_deviation', 
            'is_new_beneficiary', 'time_risk', 'country'
        ]
        
        # Prepare input df
        df = pd.DataFrame([data])
        for col in features:
            if col not in df.columns:
                df[col] = 0 # Default fallback
        
        X = df[features]
        score = float(self.model.predict_proba(X)[0, 1])
        
        # Simple confidence: higher if score is far from 0.5 (more certain)
        confidence = min(1.0, abs(score - 0.5) * 2)
        
        # Get top factors from importance
        top_factors = sorted(self.importance.items(), key=lambda x: x[1], reverse=True)[:3]
        factors = [f"{k}" for k, v in top_factors if data.get(k, 0) > 0]
        
        return {"score": score, "confidence": confidence, "factors": factors}
