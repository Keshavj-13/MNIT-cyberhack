import joblib
import os
import pandas as pd
import numpy as np
from typing import Dict, Any
from src.providers.base import RiskProvider, RiskResult

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    _TORCH = True
except ImportError:
    _TORCH = False


# Checkpoint uses .conv.weight keys — bare Conv1d would mismatch
class _W(nn.Module):
    def __init__(self, i, o, k, p=0): super().__init__(); self.conv = nn.Conv1d(i, o, k, padding=p, bias=True)
    def forward(self, x): return self.conv(x)

class _IB(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.conv1, self.bn1 = _W(c, c, 3, 1), nn.BatchNorm1d(c)
        self.conv2, self.bn2 = _W(c, c, 3, 1), nn.BatchNorm1d(c)
    def forward(self, x):
        return F.relu(self.bn2(self.conv2(F.relu(self.bn1(self.conv1(x))))) + x)

class _PB(nn.Module):
    # First conv in transition blocks is unwrapped in checkpoint; second is wrapped
    def __init__(self, i, o):
        super().__init__()
        self.conv1, self.bn1 = nn.Conv1d(i, o, 3, padding=1, bias=True), nn.BatchNorm1d(o)
        self.conv2, self.bn2 = _W(o, o, 3, 1), nn.BatchNorm1d(o)
        self.skip = nn.Sequential(nn.Conv1d(i, o, 1, bias=True), nn.BatchNorm1d(o))
    def forward(self, x):
        return F.relu(self.bn2(self.conv2(F.relu(self.bn1(self.conv1(x))))) + self.skip(x))

class _VarCNN(nn.Module):
    # Architecture reverse-engineered from checkpoint key shapes
    def __init__(self):
        super().__init__()
        self.conv1, self.bn1 = nn.Conv1d(1, 64, 7, padding=3, bias=True), nn.BatchNorm1d(64)
        self.stage1 = nn.Sequential(_IB(64), _IB(64))
        self.stage2 = nn.Sequential(_PB(64, 128), _IB(128))
        self.stage3 = nn.Sequential(_PB(128, 256), _IB(256))
        self.stage4 = nn.Sequential(_PB(256, 512), _IB(512))
        self.gap = nn.AdaptiveAvgPool1d(1)
        self.metadata_fc = nn.Sequential(nn.Linear(10, 128, bias=True), nn.BatchNorm1d(128))
        # index 0 is Flatten (not saved), 1=Linear, 2=BN, 3=ReLU, 4=Dropout, 5=Linear
        self.classifier = nn.Sequential(nn.Flatten(), nn.Linear(640, 512), nn.BatchNorm1d(512), nn.ReLU(), nn.Dropout(0.5), nn.Linear(512, 28))

    def forward(self, x, meta=None):
        x = self.stage4(self.stage3(self.stage2(self.stage1(F.relu(self.bn1(self.conv1(x)))))))
        gap = self.gap(x).squeeze(-1)
        if meta is None: meta = torch.zeros(gap.size(0), 10, device=gap.device)
        return self.classifier(torch.cat([gap, F.relu(self.metadata_fc(meta))], dim=1))


def _apply_platt(raw_score: float, a: float, b: float) -> float:
    logit = np.log(min(max(raw_score, 1e-6), 1 - 1e-6) / (1 - min(max(raw_score, 1e-6), 1 - 1e-6)))
    return float(1.0 / (1.0 + np.exp(-(a * logit + b))))

def _load_calibrated_bundle(model_path: str):
    bundle = joblib.load(model_path)
    if isinstance(bundle, dict) and "model" in bundle:
        return bundle["model"], bundle.get("platt_a", 1.0), bundle.get("platt_b", 0.0)
    return bundle, 1.0, 0.0


class TransactionRiskProvider(RiskProvider):
    def __init__(self, model_path="models/artifacts/transaction_risk.joblib",
                 features_path="models/artifacts/transaction_features.joblib",
                 preprocessor_path="models/artifacts/transaction_preprocessor.joblib"):
        self.model = self.encoder = None
        self.platt_a, self.platt_b, self.features, self.cat_cols = 1.0, 0.0, [], []
        self.model_info = {"model_path": model_path, "model_loaded": False, "mode": "fallback",
                           "note": "Official Feedzai BAF model (XGBoost, full 1M-row Base.csv, Platt-calibrated)."}
        if os.path.exists(model_path) and os.path.exists(features_path):
            try:
                self.model, self.platt_a, self.platt_b = _load_calibrated_bundle(model_path)
                self.features = joblib.load(features_path)
                if os.path.exists(preprocessor_path):
                    preproc = joblib.load(preprocessor_path)
                    self.encoder, self.cat_cols = preproc.get("encoder"), preproc.get("cat_cols", [])
                self.model_info.update({"model_loaded": True, "mode": "ml"})
            except Exception as e:
                self.model_info["note"] += f" (Load failed: {e})"

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score, expl = 0.1, ["Official Transaction Risk Model (Feedzai BAF)"]
        if self.model and self.features:
            try:
                X = pd.DataFrame([data]).reindex(columns=self.features, fill_value=0)
                if self.encoder and self.cat_cols:
                    present = [c for c in self.cat_cols if c in X.columns]
                    X[present] = self.encoder.transform(X[present].astype(str))
                for col in X.select_dtypes(include=["object"]).columns:
                    X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)
                raw = float(self.model.predict_proba(X)[0, 1])
                score = _apply_platt(raw, self.platt_a, self.platt_b)
                expl.append(f"ML Score: {score:.4f} (raw={raw:.4f})")
            except Exception as e:
                expl.append(f"ML Inference failed: {e}. Using fallback."); score = 0.5
        if data.get("amount", 0) > 10000:
            score = max(score, 0.9); expl.append("High amount alert (>10k)")
        return RiskResult(provider_name="TransactionRisk (Official)", risk_score=score, confidence=0.95,
                          severity="HIGH" if score > 0.7 else "LOW",
                          event_category="MONETIZE" if score > 0.5 else "NEUTRAL",
                          explanations=expl, raw_features=data)


class SocialEngineeringRiskProvider(RiskProvider):
    def __init__(self, model_path="models/artifacts/intent_risk.joblib"):
        self.model = None
        self.platt_a, self.platt_b = 1.0, 0.0
        self.model_info = {"model_path": model_path, "model_loaded": False, "mode": "fallback",
                           "note": "Official Intent Risk Model (SMS Spam Collection, full 5574 rows, TF-IDF + RandomForest, Platt-calibrated)."}
        if os.path.exists(model_path):
            try:
                self.model, self.platt_a, self.platt_b = _load_calibrated_bundle(model_path)
                self.model_info.update({"model_loaded": True, "mode": "ml"})
            except Exception as e:
                self.model_info["note"] += f" (Load failed: {e})"

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score, expl = 0.05, ["Official Intent Risk Model (SMS-Spam)"]
        sms_text = data.get("sms_text") or data.get("message") or ""
        if self.model and sms_text:
            try:
                raw = float(self.model.predict_proba([sms_text])[0, 1])
                score = _apply_platt(raw, self.platt_a, self.platt_b)
                expl.append(f"ML Intent Score: {score:.4f} (raw={raw:.4f})")
            except Exception as e:
                expl.append(f"ML Inference failed: {e}")
        if "urgent" in sms_text.lower() and "verify" in sms_text.lower():
            score = max(score, 0.85); expl.append("Heuristic: Urgency/Verify keywords detected.")
        return RiskResult(provider_name="SocialEngineering (Official)", risk_score=score, confidence=0.9,
                          severity="HIGH" if score > 0.8 else "LOW",
                          event_category="LURE" if score > 0.5 else "NEUTRAL",
                          explanations=expl, raw_features=data)


class NetworkRiskProvider(RiskProvider):
    def __init__(self, model_path="models/artifacts/environment_risk.joblib",
                 features_path="models/artifacts/environment_features.joblib"):
        self.model = None
        self.platt_a, self.platt_b, self.features = 1.0, 0.0, []
        self.model_info = {"model_path": model_path, "model_loaded": False, "mode": "fallback",
                           "note": "Official Environment Risk Model (SIMARGL2021, part1+part2 sample, 4 traffic classes)."}
        if os.path.exists(model_path) and os.path.exists(features_path):
            try:
                self.model, self.platt_a, self.platt_b = _load_calibrated_bundle(model_path)
                self.features = joblib.load(features_path)
                self.model_info.update({"model_loaded": True, "mode": "ml"})
            except Exception as e:
                self.model_info["note"] += f" (Load failed: {e})"

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score, expl = 0.05, ["Official Environment Risk Model (Simargl-Net)"]
        if self.model and self.features:
            try:
                X = pd.DataFrame([data]).reindex(columns=self.features, fill_value=0)
                raw = float(self.model.predict_proba(X)[0, 1])
                score = _apply_platt(raw, self.platt_a, self.platt_b)
                expl.append(f"ML Network Score: {score:.4f} (raw={raw:.4f})")
            except Exception as e:
                expl.append(f"ML Inference failed: {e}")
        return RiskResult(provider_name="NetworkRisk (Official)", risk_score=score, confidence=0.98,
                          severity="HIGH" if score > 0.7 else "LOW",
                          event_category="EXPLOIT" if score > 0.5 else "NEUTRAL",
                          explanations=expl, raw_features=data)


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
        self.platt_a, self.platt_b = 1.0, 0.0
        self.model_info = {"model_path": model_path, "model_loaded": False, "mode": "fallback",
                           "note": "Official Behavioral Risk Model (CMU Keystroke, full 20400 rows, XGBoost, Platt-calibrated)."}
        if os.path.exists(model_path):
            try:
                self.model, self.platt_a, self.platt_b = _load_calibrated_bundle(model_path)
                self.model_info.update({"model_loaded": True, "mode": "ml"})
            except Exception as e:
                self.model_info["note"] += f" (Load failed: {e})"

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score, expl = 0.05, ["Official Behavioral Risk Model (Keystroke)"]
        if self.model and any(f in data for f in self.BEHAVIOR_FEATURES):
            try:
                X = pd.DataFrame([data]).reindex(columns=self.BEHAVIOR_FEATURES, fill_value=0)
                # Prob of being the authorized user — risk is the inverse
                prob_auth = _apply_platt(float(self.model.predict_proba(X)[0, 1]), self.platt_a, self.platt_b)
                score = 1.0 - prob_auth
                expl.append(f"Identity Verification: {prob_auth*100:.1f}% match. Risk: {score:.4f}")
            except Exception as e:
                expl.append(f"ML Inference failed: {e}")
        if data.get("login_anomaly"):
            score = max(score, 0.95); expl.append("Critical: Login anomaly detected (impossible travel).")
        return RiskResult(provider_name="AccountTakeover (Official)", risk_score=score, confidence=0.96,
                          severity="CRITICAL" if score > 0.9 else "LOW",
                          event_category="EXPLOIT" if score > 0.5 else "NEUTRAL",
                          explanations=expl, raw_features=data)


class DeviceTrustProvider(RiskProvider):
    def __init__(self):
        self.model_info = {"mode": "rules", "note": "Rule-based device fingerprinting."}

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score, expl = 0.05, ["Device Fingerprinting"]
        if data.get("vpn_detected"): score = max(score, 0.45); expl.append("VPN detected.")
        if data.get("rooted"): score = 0.98; expl.append("Device is rooted/jailbroken.")
        return RiskResult(provider_name="DeviceTrust", risk_score=score, confidence=1.0,
                          severity="HIGH" if score > 0.7 else "LOW", event_category="NEUTRAL",
                          explanations=expl, raw_features=data)


class PhishingRiskProvider(SocialEngineeringRiskProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_info["note"] = "Phishing alias for SocialEngineering model."


_META_KEYS = ["mean_dwell_time", "mean_flight_time", "typing_cadence", "backspace_frequency",
              "avg_mouse_velocity", "avg_mouse_acceleration", "mouse_path_straightness",
              "mouse_click_density", "navigation_speed", "interaction_density"]

class BeaconBehavioralProvider(RiskProvider):
    # 0.99 matches the training threshold used by the BEACON model creator
    CONFIDENCE_THRESHOLD = 0.99

    def __init__(self, model_path="models/beacon/best_model_varcnn_60WS_90OL_seq1024_thr0.99.pth"):
        self.net = None
        self.model_info = {"model_path": model_path, "model_loaded": False, "mode": "fallback",
                           "note": "BEACON VarCNN (Singh et al. 2026, arXiv:2605.10867). 60WS/90OL/seq1024/thr0.99."}
        if not _TORCH or not os.path.exists(model_path): return
        try:
            net = _VarCNN()
            net.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True), strict=True)
            net.eval(); self.net = net
            self.model_info.update({"model_loaded": True, "mode": "ml"})
        except Exception as e:
            self.model_info["note"] += f" (Load failed: {e})"

    def _seq(self, data: Dict[str, Any]):
        # inter_event_timings preserves real rhythm; scalar rollup is a last resort
        raw = data.get("inter_event_timings") or [data[k] for k in _META_KEYS if k in data]
        if len(raw) < 10: return None
        arr = np.array(raw, dtype=np.float32)
        arr = (arr - arr.mean()) / (arr.std() + 1e-8)
        padded = np.zeros(1024, dtype=np.float32)
        padded[:min(len(arr), 1024)] = arr[:1024]
        return torch.tensor(padded).unsqueeze(0).unsqueeze(0)

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score, expl = 0.05, ["BEACON VarCNN Behavioral Fingerprint"]
        if self.net:
            seq = self._seq(data)
            if seq is not None:
                try:
                    meta = torch.tensor([[float(data.get(k, 0)) for k in _META_KEYS]])
                    with torch.no_grad():
                        probs = torch.softmax(self.net(seq, meta), dim=-1)
                    top_prob, top_cls = float(probs.max()), int(probs.argmax())
                    if top_prob >= self.CONFIDENCE_THRESHOLD:
                        expl.append(f"Identity confirmed: user-{top_cls:02d} ({top_prob*100:.1f}%)")
                    else:
                        # below threshold the model is ambiguous — scale risk by how far below we are
                        score = min(0.95, (1.0 - top_prob) * 0.8)
                        expl.append(f"Fingerprint mismatch: best user-{top_cls:02d} at {top_prob*100:.1f}% → risk {score:.2f}")
                except Exception as e:
                    expl.append(f"Inference failed: {e}")
            else:
                expl.append("No timing sequence available — skipped.")
        return RiskResult(provider_name="BeaconBehavioral (VarCNN)", risk_score=score,
                          confidence=self.CONFIDENCE_THRESHOLD if score < 0.1 else 1.0 - score,
                          severity="HIGH" if score >= 0.7 else ("MEDIUM" if score >= 0.4 else "LOW"),
                          event_category="EXPLOIT" if score >= 0.5 else "NEUTRAL",
                          explanations=expl, raw_features=data)
