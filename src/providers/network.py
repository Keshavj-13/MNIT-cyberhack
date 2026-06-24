import joblib
import pandas as pd
from typing import Dict, Any
from src.providers.base import RiskProvider, RiskResult

class NetworkRiskProvider(RiskProvider):
    def __init__(self, model_path="models/network_model.joblib", importance_path="models/network_importance.joblib"):
        try:
            self.model = joblib.load(model_path)
            self.importance = joblib.load(importance_path)
        except Exception:
            self.model = None
            self.importance = {}

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        res = self.score(data)
        return RiskResult(
            provider_name="NetworkRisk",
            risk_score=res["score"],
            confidence=res["confidence"],
            severity="HIGH" if res["score"] > 0.7 else "LOW",
            explanations=res["factors"],
            raw_features=data
        )

    def score(self, data: dict) -> dict:
        if self.model is None:
            return {"score": 0.5, "confidence": 0.0, "factors": ["Model not loaded"]}
        
        features = [
            'Destination Port', 'Flow Duration', 'Total Fwd Packets', 
            'Total Backward Packets', 'Fwd Packet Length Max', 
            'Bwd Packet Length Max', 'Flow Bytes/s', 'Flow Packets/s'
        ]
        
        df = pd.DataFrame([data])
        for col in features:
            if col not in df.columns:
                df[col] = 0
        
        X = df[features]
        score = float(self.model.predict_proba(X)[0, 1])
        confidence = min(1.0, abs(score - 0.5) * 2)
        
        top_factors = sorted(self.importance.items(), key=lambda x: x[1], reverse=True)[:3]
        factors = [f"{k}" for k, v in top_factors if data.get(k, 0) > 0]
        
        return {"score": score, "confidence": confidence, "factors": factors}
