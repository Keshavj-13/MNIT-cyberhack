import joblib
import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from src.providers.base import RiskProvider, RiskResult

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False


if _TORCH_AVAILABLE:
    class _ConvWrapper(nn.Module):
        """Thin wrapper so weight key is `.conv.weight` to match checkpoint."""
        def __init__(self, in_ch, out_ch, kernel, padding=0):
            super().__init__()
            self.conv = nn.Conv1d(in_ch, out_ch, kernel, padding=padding, bias=True)

        def forward(self, x):
            return self.conv(x)

    class _IdentityBlock(nn.Module):
        def __init__(self, ch, kernel=3):
            super().__init__()
            pad = kernel // 2
            self.conv1 = _ConvWrapper(ch, ch, kernel, padding=pad)
            self.bn1 = nn.BatchNorm1d(ch)
            self.conv2 = _ConvWrapper(ch, ch, kernel, padding=pad)
            self.bn2 = nn.BatchNorm1d(ch)

        def forward(self, x):
            out = F.relu(self.bn1(self.conv1(x)))
            out = self.bn2(self.conv2(out))
            return F.relu(out + x)

    class _ProjectionBlock(nn.Module):
        """First block of a stage that changes channel width.

        conv1 is a bare Conv1d (no wrapper), conv2 is wrapped — matches checkpoint.
        """
        def __init__(self, in_ch, out_ch, kernel=3):
            super().__init__()
            pad = kernel // 2
            self.conv1 = nn.Conv1d(in_ch, out_ch, kernel, padding=pad, bias=True)
            self.bn1 = nn.BatchNorm1d(out_ch)
            self.conv2 = _ConvWrapper(out_ch, out_ch, kernel, padding=pad)
            self.bn2 = nn.BatchNorm1d(out_ch)
            self.skip = nn.Sequential(
                nn.Conv1d(in_ch, out_ch, 1, bias=True),
                nn.BatchNorm1d(out_ch),
            )

        def forward(self, x):
            shortcut = self.skip(x)
            out = F.relu(self.bn1(self.conv1(x)))
            out = self.bn2(self.conv2(out))
            return F.relu(out + shortcut)

    class _VarCNN(nn.Module):
        """VarCNN from BEACON (Singh et al. 2026).

        Dual-stream: 1-D temporal sequence + 10-dim metadata.
        Outputs logits over n_classes identities (28 for the BEACON dataset).

        Architecture recovered from checkpoint keys:
          stem → stage1 (2× identity, ch=64)
               → stage2 (projection 64→128, identity)
               → stage3 (projection 128→256, identity)
               → stage4 (projection 256→512, identity)
          GAP(512) ++ metadata_fc(10→128) → classifier(640→512→n_classes)
        """
        N_METADATA = 10

        def __init__(self, n_classes: int = 28):
            super().__init__()
            self.conv1 = nn.Conv1d(1, 64, kernel_size=7, padding=3, bias=True)
            self.bn1 = nn.BatchNorm1d(64)

            self.stage1 = nn.Sequential(_IdentityBlock(64), _IdentityBlock(64))
            self.stage2 = nn.Sequential(_ProjectionBlock(64, 128), _IdentityBlock(128))
            self.stage3 = nn.Sequential(_ProjectionBlock(128, 256), _IdentityBlock(256))
            self.stage4 = nn.Sequential(_ProjectionBlock(256, 512), _IdentityBlock(512))

            self.gap = nn.AdaptiveAvgPool1d(1)

            self.metadata_fc = nn.Sequential(
                nn.Linear(self.N_METADATA, 128, bias=True),
                nn.BatchNorm1d(128),
            )

            self.classifier = nn.Sequential(
                nn.Flatten(),                    # [0] — not in checkpoint
                nn.Linear(640, 512, bias=True),  # [1]
                nn.BatchNorm1d(512),             # [2]
                nn.ReLU(),                       # [3]
                nn.Dropout(0.5),                 # [4]
                nn.Linear(512, n_classes),       # [5]
            )

        def forward(self, x, meta=None):
            out = F.relu(self.bn1(self.conv1(x)))
            out = self.stage1(out)
            out = self.stage2(out)
            out = self.stage3(out)
            out = self.stage4(out)
            out = self.gap(out).squeeze(-1)  # (B, 512)

            if meta is None:
                meta = torch.zeros(out.size(0), self.N_METADATA, device=out.device)
            meta_feat = F.relu(self.metadata_fc(meta))  # (B, 128)

            combined = torch.cat([out, meta_feat], dim=1)  # (B, 640)
            return self.classifier(combined)
else:
    _VarCNN = None


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


class BeaconBehavioralProvider(RiskProvider):
    """Behavioral fingerprinting via BEACON VarCNN (Singh et al. 2026).

    Uses the pre-trained model from the BEACON dataset creator:
      window_size=60, overlap=90%, seq_len=1024, confidence_threshold=0.99

    Input: raw inter-event timing sequences extracted from session telemetry.
    A risk score > 0 means the behavioral pattern does NOT match the enrolled
    user's fingerprint (i.e., a potential account takeover / impostor signal).
    """
    SEQ_LEN = 1024
    WINDOW_SIZE = 60
    CONFIDENCE_THRESHOLD = 0.99
    MODEL_PATH = "models/beacon/best_model_varcnn_60WS_90OL_seq1024_thr0.99.pth"

    def __init__(self, model_path: str = MODEL_PATH):
        self.net = None
        self.device = "cpu"
        self.model_info = {
            "model_path": model_path,
            "model_loaded": False,
            "mode": "fallback",
            "note": (
                "BEACON VarCNN behavioral fingerprint model "
                "(Singh et al. 2026, arXiv:2605.10867). "
                "60WS / 90OL / seq1024 / thr0.99."
            )
        }
        if not _TORCH_AVAILABLE or _VarCNN is None:
            self.model_info["note"] += " (PyTorch not installed — fallback active)"
            return
        if not os.path.exists(model_path):
            self.model_info["note"] += f" (Model file not found at {model_path})"
            return
        try:
            net = _VarCNN(n_classes=28)
            state = torch.load(model_path, map_location="cpu", weights_only=True)
            net.load_state_dict(state, strict=True)
            net.eval()
            self.net = net
            self.model_info["model_loaded"] = True
            self.model_info["mode"] = "ml"
        except Exception as e:
            self.model_info["note"] += f" (Load failed: {e})"

    def _build_sequence(self, data: Dict[str, Any]) -> Optional["torch.Tensor"]:
        """Extract a 1×SEQ_LEN timing sequence from telemetry or payload."""
        seq: List[float] = []

        # Prefer an explicit sequence if the caller passed one
        if "beacon_sequence" in data:
            seq = [float(v) for v in data["beacon_sequence"]]
        else:
            # Reconstruct from keystroke dwell/flight times already extracted
            for key in (
                "mean_dwell_time", "mean_flight_time", "typing_cadence",
                "avg_mouse_velocity", "avg_mouse_acceleration",
                "mouse_path_straightness", "mouse_click_density",
                "navigation_speed", "interaction_density",
            ):
                if key in data:
                    seq.append(float(data[key]))

        if not seq:
            return None

        # Tile or truncate to SEQ_LEN
        if len(seq) < self.SEQ_LEN:
            repeats = (self.SEQ_LEN // len(seq)) + 1
            seq = (seq * repeats)[: self.SEQ_LEN]
        else:
            seq = seq[: self.SEQ_LEN]

        # Normalise to [0, 1]
        arr = np.array(seq, dtype=np.float32)
        rng = arr.max() - arr.min()
        if rng > 0:
            arr = (arr - arr.min()) / rng

        tensor = torch.tensor(arr).unsqueeze(0).unsqueeze(0)  # (1, 1, SEQ_LEN)
        return tensor

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score = 0.05
        confidence = 0.5
        expl = ["BEACON VarCNN Behavioral Fingerprinting"]

        if self.net is not None:
            tensor = self._build_sequence(data)
            if tensor is not None:
                try:
                    # Build metadata vector from telemetry scalar features
                    meta_keys = [
                        "mean_dwell_time", "mean_flight_time", "typing_cadence",
                        "backspace_frequency", "avg_mouse_velocity",
                        "avg_mouse_acceleration", "mouse_path_straightness",
                        "mouse_click_density", "navigation_speed", "interaction_density",
                    ]
                    meta = np.array(
                        [float(data.get(k, 0.0)) for k in meta_keys], dtype=np.float32
                    )
                    meta_tensor = torch.tensor(meta).unsqueeze(0)  # (1, 10)

                    with torch.no_grad():
                        logits = self.net(tensor, meta_tensor)    # (1, 28)
                        probs = torch.softmax(logits, dim=-1)
                        top_prob = float(probs.max())             # best-matching identity
                        top_class = int(probs.argmax())

                    # Model identifies a known user with ≥99% confidence → low risk.
                    # Below threshold → behaviour doesn't confidently match any enrolled
                    # user → elevated impostor risk.
                    if top_prob >= self.CONFIDENCE_THRESHOLD:
                        score = 0.05
                        confidence = top_prob
                        expl.append(
                            f"Behavioral identity confirmed: user-{top_class:02d} "
                            f"({top_prob*100:.1f}% ≥ {self.CONFIDENCE_THRESHOLD*100:.0f}% threshold)"
                        )
                    else:
                        # Risk scales inversely with best-match confidence
                        score = min(0.95, (1.0 - top_prob) * 0.8)
                        confidence = 1.0 - top_prob
                        expl.append(
                            f"Behavioral fingerprint mismatch: best match user-{top_class:02d} "
                            f"at only {top_prob*100:.1f}% (threshold={self.CONFIDENCE_THRESHOLD*100:.0f}%). "
                            f"Impostor risk: {score:.2f}"
                        )
                except Exception as e:
                    expl.append(f"VarCNN inference failed: {e}")
            else:
                expl.append("No behavioral sequence data available — skipped.")
        else:
            expl.append(f"Model unavailable ({self.model_info.get('mode')}). Using heuristic fallback.")
            # Light heuristic: high interaction density at odd hours may signal bot
            if data.get("interaction_density", 0) > 200:
                score = 0.4
                expl.append("High interaction density heuristic triggered.")

        return RiskResult(
            provider_name="BeaconBehavioral (VarCNN)",
            risk_score=score,
            confidence=confidence,
            severity="HIGH" if score >= 0.7 else ("MEDIUM" if score >= 0.4 else "LOW"),
            event_category="EXPLOIT" if score >= 0.5 else "NEUTRAL",
            explanations=expl,
            raw_features=data
        )
