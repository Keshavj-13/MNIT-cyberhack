import joblib
import pandas as pd
import numpy as np
import os
from typing import Dict, Any
from .base import RiskProvider, RiskResult

class ContextRiskProvider(RiskProvider):
    def __init__(self):
        try:
            self.sms_model = joblib.load("models/sms_scam_model.joblib")
        except Exception:
            self.sms_model = None
            
        try:
            self.phish_model = joblib.load("models/phishing_url_model.joblib")
        except Exception:
            self.phish_model = None

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        res = self.score(data)
        return RiskResult(
            provider_name="ContextRisk",
            risk_score=res["score"],
            confidence=res["confidence"],
            severity="HIGH" if res["score"] > 0.7 else "LOW",
            explanations=res["factors"],
            raw_features=data
        )

    def score(self, data: dict) -> dict:
        """
        Fuses SMS Risk, Phishing Risk, and basic behavioral rules.
        """
        score = 0.0
        factors = []
        confidences = []
        
        # 1. SMS Scam Detection
        sms_text = data.get("recent_sms", "")
        if sms_text and self.sms_model:
            try:
                sms_prob = float(self.sms_model.predict_proba([sms_text])[0, 1])
                score += sms_prob * 0.4  # Weight
                confidences.append(abs(sms_prob - 0.5) * 2)
                if sms_prob > 0.6:
                    factors.append("Recent suspicious SMS detected")
            except Exception:
                pass
                
        # 2. Phishing URL Detection
        phish_features = data.get("phishing_features", None)
        if phish_features and self.phish_model:
            try:
                df_p = pd.DataFrame([phish_features])
                phish_prob = float(self.phish_model.predict_proba(df_p)[0, 1])
                score += phish_prob * 0.3
                confidences.append(abs(phish_prob - 0.5) * 2)
                if phish_prob > 0.6:
                    factors.append("Navigation from malicious URL")
            except Exception:
                pass

        # 3. Basic Contextual Rules
        if data.get("tx_velocity_24h", 0) > 10:
            score += 0.15
            factors.append("High transaction velocity")
            confidences.append(0.9)
            
        if data.get("amount_deviation", 1.0) > 5.0:
            score += 0.15
            factors.append("Unusual transfer amount")
            confidences.append(0.8)
            
        score = min(1.0, score)
        
        final_conf = float(np.mean(confidences)) if confidences else 0.5
        
        return {"score": score, "confidence": final_conf, "factors": factors}
