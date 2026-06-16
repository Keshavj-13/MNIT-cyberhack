import joblib
import os
import pandas as pd
import numpy as np
from typing import Dict, Any
from src.providers.base import RiskProvider, RiskResult


def _apply_platt(raw_score: float, a: float, b: float) -> float:
    """Apply a fitted Platt (sigmoid) calibration to a raw model probability."""
    clipped = min(max(raw_score, 1e-6), 1 - 1e-6)
    logit = np.log(clipped / (1 - clipped))
    return float(1.0 / (1.0 + np.exp(-(a * logit + b))))


def _load_calibrated_bundle(model_path: str):
    """Load a joblib artifact that may be either a bare estimator or a
    {"model": ..., "platt_a": ..., "platt_b": ...} calibration bundle."""
    bundle = joblib.load(model_path)
    if isinstance(bundle, dict) and "model" in bundle:
        return bundle["model"], bundle.get("platt_a", 1.0), bundle.get("platt_b", 0.0)
    return bundle, 1.0, 0.0

class TransactionRiskProvider(RiskProvider):
    def __init__(self, model_path="models/artifacts/transaction_risk.joblib",
                 features_path="models/artifacts/transaction_features.joblib",
                 preprocessor_path="models/artifacts/transaction_preprocessor.joblib"):
        self.model = None
        self.platt_a = 1.0
        self.platt_b = 0.0
        self.features = []
        self.encoder = None
        self.cat_cols = []
        self.model_info = {
            "model_path": model_path,
            "model_loaded": False,
            "mode": "fallback",
            "note": "Official Feedzai BAF model (XGBoost, full 1M-row Base.csv, Platt-calibrated)."
        }
        if os.path.exists(model_path) and os.path.exists(features_path):
            try:
                self.model, self.platt_a, self.platt_b = _load_calibrated_bundle(model_path)
                self.features = joblib.load(features_path)
                if os.path.exists(preprocessor_path):
                    preproc = joblib.load(preprocessor_path)
                    self.encoder = preproc.get("encoder")
                    self.cat_cols = preproc.get("cat_cols", [])
                self.model_info["model_loaded"] = True
                self.model_info["mode"] = "ml"
            except Exception as e:
                self.model_info["note"] += f" (Load failed: {e})"

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score = 0.1
        expl = ["Official Transaction Risk Model (Feedzai BAF)"]

        if self.model and self.features:
            try:
                # Prepare input DataFrame
                input_df = pd.DataFrame([data])
                # Ensure all features exist
                for col in self.features:
                    if col not in input_df.columns:
                        input_df[col] = 0

                X = input_df[self.features].copy()

                # Apply the same OrdinalEncoder used at training time so
                # categorical inference matches the trained model exactly.
                if self.encoder is not None and self.cat_cols:
                    present_cat_cols = [c for c in self.cat_cols if c in X.columns]
                    X[present_cat_cols] = self.encoder.transform(X[present_cat_cols].astype(str))

                # Coerce any remaining non-numeric columns
                for col in X.select_dtypes(include=['object']).columns:
                    X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)

                raw_score = float(self.model.predict_proba(X)[0, 1])
                score = _apply_platt(raw_score, self.platt_a, self.platt_b)
                expl.append(f"ML Score: {score:.4f} (raw={raw_score:.4f})")
            except Exception as e:
                expl.append(f"ML Inference failed: {e}. Using fallback.")
                score = 0.5 # Neutral fallback
        
        # Rule-based overrides
        if data.get("amount", 0) > 10000:
            score = max(score, 0.9)
            expl.append("High amount alert (>10k)")

        return RiskResult(
            provider_name="TransactionRisk (Official)",
            risk_score=score,
            confidence=0.95,
            severity="HIGH" if score > 0.7 else "LOW",
            event_category="MONETIZE" if score > 0.5 else "NEUTRAL",
            explanations=expl,
            raw_features=data
        )

class SocialEngineeringRiskProvider(RiskProvider):
    def __init__(self, model_path="models/artifacts/intent_risk.joblib"):
        self.model = None
        self.platt_a = 1.0
        self.platt_b = 0.0
        self.model_info = {
            "model_path": model_path,
            "model_loaded": False,
            "mode": "fallback",
            "note": "Official Intent Risk Model (SMS Spam Collection, full 5574 rows, TF-IDF + RandomForest, Platt-calibrated)."
        }
        if os.path.exists(model_path):
            try:
                self.model, self.platt_a, self.platt_b = _load_calibrated_bundle(model_path)
                self.model_info["model_loaded"] = True
                self.model_info["mode"] = "ml"
            except Exception as e:
                self.model_info["note"] += f" (Load failed: {e})"

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score = 0.05
        expl = ["Official Intent Risk Model (SMS-Spam)"]
        sms_text = data.get("sms_text") or data.get("message") or ""

        if self.model and sms_text:
            try:
                raw_score = float(self.model.predict_proba([sms_text])[0, 1])
                score = _apply_platt(raw_score, self.platt_a, self.platt_b)
                expl.append(f"ML Intent Score: {score:.4f} (raw={raw_score:.4f})")
            except Exception as e:
                expl.append(f"ML Inference failed: {e}")
        
        if "urgent" in sms_text.lower() and "verify" in sms_text.lower():
            score = max(score, 0.85)
            expl.append("Heuristic: Urgency/Verify keywords detected.")

        return RiskResult(
            provider_name="SocialEngineering (Official)",
            risk_score=score,
            confidence=0.9,
            severity="HIGH" if score > 0.8 else "LOW",
            event_category="LURE" if score > 0.5 else "NEUTRAL",
            explanations=expl,
            raw_features=data
        )

class NetworkRiskProvider(RiskProvider):
    def __init__(self, model_path="models/artifacts/environment_risk.joblib",
                 features_path="models/artifacts/environment_features.joblib"):
        self.model = None
        self.platt_a = 1.0
        self.platt_b = 0.0
        self.features = []
        self.model_info = {
            "model_path": model_path,
            "model_loaded": False,
            "mode": "fallback",
            "note": "Official Environment Risk Model (SIMARGL2021, part1+part2 sample, 4 traffic classes)."
        }
        if os.path.exists(model_path) and os.path.exists(features_path):
            try:
                self.model, self.platt_a, self.platt_b = _load_calibrated_bundle(model_path)
                self.features = joblib.load(features_path)
                self.model_info["model_loaded"] = True
                self.model_info["mode"] = "ml"
            except Exception as e:
                self.model_info["note"] += f" (Load failed: {e})"

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score = 0.05
        expl = ["Official Environment Risk Model (Simargl-Net)"]

        if self.model and self.features:
            try:
                input_df = pd.DataFrame([data])
                for col in self.features:
                    if col not in input_df.columns:
                        input_df[col] = 0
                X = input_df[self.features]
                raw_score = float(self.model.predict_proba(X)[0, 1])
                score = _apply_platt(raw_score, self.platt_a, self.platt_b)
                expl.append(f"ML Network Score: {score:.4f} (raw={raw_score:.4f})")
            except Exception as e:
                expl.append(f"ML Inference failed: {e}")

        return RiskResult(
            provider_name="NetworkRisk (Official)",
            risk_score=score,
            confidence=0.98,
            severity="HIGH" if score > 0.7 else "LOW",
            event_category="EXPLOIT" if score > 0.5 else "NEUTRAL",
            explanations=expl,
            raw_features=data
        )

class AccountTakeoverProvider(RiskProvider):
    BEHAVIOR_FEATURES = [
        'H.period', 'DD.period.t', 'UD.period.t', 'H.t', 'DD.t.i', 'UD.t.i', 'H.i', 
        'DD.i.e', 'UD.i.e', 'H.e', 'DD.e.five', 'UD.e.five', 'H.five', 'DD.five.Shift.r', 
        'UD.five.Shift.r', 'H.Shift.r', 'DD.Shift.r.o', 'UD.Shift.r.o', 'H.o', 'DD.o.a', 
        'UD.o.a', 'H.a', 'DD.a.n', 'UD.a.n', 'H.n', 'DD.n.l', 'UD.n.l', 'H.l', 
        'DD.l.Return', 'UD.l.Return', 'H.Return'
    ]

    def __init__(self, model_path="models/artifacts/behavioral_risk.joblib"):
        self.model = None
        self.platt_a = 1.0
        self.platt_b = 0.0
        self.model_info = {
            "model_path": model_path,
            "model_loaded": False,
            "mode": "fallback",
            "note": "Official Behavioral Risk Model (CMU Keystroke, full 20400 rows, XGBoost, Platt-calibrated)."
        }
        if os.path.exists(model_path):
            try:
                self.model, self.platt_a, self.platt_b = _load_calibrated_bundle(model_path)
                self.model_info["model_loaded"] = True
                self.model_info["mode"] = "ml"
            except Exception as e:
                self.model_info["note"] += f" (Load failed: {e})"

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score = 0.05
        expl = ["Official Behavioral Risk Model (Keystroke)"]

        # Check if we have keystroke data
        if self.model and any(f in data for f in self.BEHAVIOR_FEATURES):
            try:
                input_df = pd.DataFrame([data])
                for col in self.BEHAVIOR_FEATURES:
                    if col not in input_df.columns:
                        input_df[col] = 0
                X = input_df[self.BEHAVIOR_FEATURES]
                # Prob of being authorized user (s002), Platt-calibrated
                raw_prob_auth = float(self.model.predict_proba(X)[0, 1])
                prob_auth = _apply_platt(raw_prob_auth, self.platt_a, self.platt_b)
                # Risk is 1 - prob_auth
                score = 1.0 - prob_auth
                expl.append(f"Identity Verification: {prob_auth*100:.1f}% match. Risk: {score:.4f}")
            except Exception as e:
                expl.append(f"ML Inference failed: {e}")
        
        if data.get("login_anomaly"):
            score = max(score, 0.95)
            expl.append("Critical: Login anomaly detected (impossible travel).")

        return RiskResult(
            provider_name="AccountTakeover (Official)",
            risk_score=score,
            confidence=0.96,
            severity="CRITICAL" if score > 0.9 else "LOW",
            event_category="EXPLOIT" if score > 0.5 else "NEUTRAL",
            explanations=expl,
            raw_features=data
        )

class DeviceTrustProvider(RiskProvider):
    def __init__(self):
        self.model_info = {
            "mode": "rules",
            "note": "Rule-based device fingerprinting."
        }

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score = 0.05
        expl = ["Device Fingerprinting"]
        if data.get("vpn_detected"):
            score = max(score, 0.45)
            expl.append("VPN detected.")
        if data.get("rooted"):
            score = 0.98
            expl.append("Device is rooted/jailbroken.")
        
        return RiskResult(
            provider_name="DeviceTrust",
            risk_score=score,
            confidence=1.0,
            severity="HIGH" if score > 0.7 else "LOW",
            event_category="NEUTRAL",
            explanations=expl,
            raw_features=data
        )

# For backward compatibility if any code expects PhishingRiskProvider
class PhishingRiskProvider(SocialEngineeringRiskProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_info["note"] = "Phishing alias for SocialEngineering model."
