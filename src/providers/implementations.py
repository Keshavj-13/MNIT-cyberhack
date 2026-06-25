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
                 features_path="models/artifacts/transaction_features.joblib"):
        self.model, self.threshold, self.features, self.cat_cols, self.encoders = None, 0.5, [], [], {}
        self.model_info = {"model_path": model_path, "model_loaded": False, "mode": "fallback",
                           "note": "Feedzai BAF GBM (1M rows, class-weighted to fix recall, F1-optimal threshold)."}
        if os.path.exists(model_path):
            try:
                bundle = joblib.load(model_path)
                if isinstance(bundle, dict):
                    self.model = bundle["model"]; self.threshold = bundle.get("threshold", 0.5)
                    self.cat_cols = bundle.get("cat_cols", []); self.encoders = bundle.get("encoders", {})
                else:
                    self.model = bundle
                if os.path.exists(features_path): self.features = joblib.load(features_path)
                self.model_info.update({"model_loaded": True, "mode": "ml"})
            except Exception as e:
                self.model_info["note"] += f" (Load failed: {e})"

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score, expl = 0.1, ["Transaction Fraud Model (Feedzai BAF, class-weighted)"]
        if self.model and self.features:
            try:
                X = pd.DataFrame([data]).reindex(columns=self.features, fill_value=0)
                for c in self.cat_cols:
                    if c in X.columns and c in self.encoders:
                        X[c] = self.encoders[c].transform(X[c].astype(str))
                for col in X.select_dtypes(include=["object"]).columns:
                    X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0)
                score = float(self.model.predict_proba(X)[0, 1])
                expl.append(f"ML Score: {score:.4f} (threshold={self.threshold:.3f})")
            except Exception as e:
                expl.append(f"ML Inference failed: {e}. Using fallback."); score = 0.1
        if data.get("amount", 0) > 10000:
            score = max(score, 0.9); expl.append("High amount alert (>10k)")
        return RiskResult(provider_name="TransactionRisk", risk_score=score, confidence=0.95,
                          severity="HIGH" if score > self.threshold else "LOW",
                          event_category="MONETIZE" if score > self.threshold else "NEUTRAL",
                          explanations=expl, raw_features=data)


import re as _re

def _url_features(url: str) -> Dict[str, int]:
    # extracted from URL string alone — no DNS/API calls needed at inference
    url = url or ""
    try: from urllib.parse import urlparse; p = urlparse(url)
    except Exception: p = None
    domain = (p.netloc if p else "").lower()
    path = (p.path if p else "")
    ip_pat = _re.compile(r'\d{1,3}(\.\d{1,3}){3}')
    sub_count = len(domain.split('.')) - 2 if domain else 0
    return {
        'having_IP_Address': -1 if ip_pat.search(domain) else 1,
        'URL_Length': -1 if len(url) > 75 else (0 if len(url) > 54 else 1),
        'having_At_Symbol': -1 if '@' in url else 1,
        'double_slash_redirecting': -1 if '//' in (path or "") else 1,
        'Prefix_Suffix': -1 if '-' in domain else 1,
        'having_Sub_Domain': -1 if sub_count > 1 else (0 if sub_count == 1 else 1),
        'SSLfinal_State': 1 if url.startswith('https') else -1,
        'HTTPS_token': -1 if 'https' in domain else 1,
    }

class SocialEngineeringRiskProvider(RiskProvider):
    # UI no longer sends message text — replaced by URL phishing using page_load events
    URL_FEATS = ['having_IP_Address','URL_Length','having_At_Symbol','double_slash_redirecting',
                 'Prefix_Suffix','having_Sub_Domain','SSLfinal_State','HTTPS_token']

    def __init__(self, model_path="models/artifacts/phishing_url_risk.joblib"):
        self.model, self.threshold = None, 0.5
        self.model_info = {"model_path": model_path, "model_loaded": False, "mode": "fallback",
                           "note": "URL phishing model (phishing_websites ARFF, 11K URLs, GBM, AUC=0.956)."}
        if os.path.exists(model_path):
            try:
                bundle = joblib.load(model_path)
                self.model = bundle["model"]; self.threshold = bundle.get("threshold", 0.5)
                self.model_info.update({"model_loaded": True, "mode": "ml"})
            except Exception as e:
                self.model_info["note"] += f" (Load failed: {e})"

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score, expl = 0.05, ["URL Phishing Model (page_load events)"]
        url = data.get("current_url") or data.get("page_url") or data.get("url") or ""
        if self.model and url:
            try:
                feats = _url_features(url)
                X = pd.DataFrame([feats]).reindex(columns=self.URL_FEATS, fill_value=0)
                score = float(self.model.predict_proba(X)[0, 1])
                expl.append(f"Phishing score: {score:.4f} for {url[:60]}")
            except Exception as e:
                expl.append(f"ML Inference failed: {e}")
        elif not url:
            expl.append("No URL in payload — skipped.")
        return RiskResult(provider_name="URLPhishing", risk_score=score, confidence=0.9,
                          severity="HIGH" if score > self.threshold else "LOW",
                          event_category="LURE" if score > self.threshold else "NEUTRAL",
                          explanations=expl, raw_features=data)


class NetworkRiskProvider(RiskProvider):
    # ponytail: SIMARGL packet-level model never fires (no packet features at inference)
    # replaced with heuristics on HTTP session metadata that ARE available at runtime
    def __init__(self, *_, **__):
        self.model_info = {"mode": "heuristic", "model_loaded": False,
                           "note": "HTTP session heuristics (VPN, proxy, TOR, impossible geo)."}

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score, expl = 0.05, ["Network heuristics (session metadata)"]
        def _flag(k): return str(data.get(k, "")).lower() in ("1", "true", "yes") or bool(data.get(k))
        if _flag("vpn_detected") or _flag("proxy_detected"):
            score = max(score, 0.4); expl.append("VPN/proxy detected.")
        if _flag("tor_detected"):
            score = max(score, 0.75); expl.append("TOR exit node detected.")
        if _flag("impossible_geo"):
            score = max(score, 0.8); expl.append("Impossible geo-velocity (location jump).")
        if _flag("blacklisted_ip"):
            score = max(score, 0.9); expl.append("IP on threat intelligence blocklist.")
        return RiskResult(provider_name="NetworkRisk", risk_score=score, confidence=0.85,
                          severity="HIGH" if score > 0.7 else "LOW",
                          event_category="EXPLOIT" if score > 0.5 else "NEUTRAL",
                          explanations=expl, raw_features=data)


class AccountTakeoverProvider(RiskProvider):
    BEHAVIOR_FEATURES = ["dwell_mean","dwell_std","dwell_range","flight_mean","flight_std",
                         "flight_range","lat_mean","lat_std","lat_range","rhythm"]

    def __init__(self, model_path="models/artifacts/behavioral_risk.joblib"):
        self.model = self.scaler = None; self.threshold = 0.41
        self.model_info = {"model_path": model_path, "model_loaded": False, "mode": "fallback",
                           "note": "Keystroke ATO (CMU 20K, GBM, 10 dwell/flight/latency features, AUC=0.89)."}
        if os.path.exists(model_path):
            try:
                bundle = joblib.load(model_path)
                if isinstance(bundle, dict):
                    self.model = bundle["model"]; self.scaler = bundle.get("scaler")
                    self.threshold = bundle.get("threshold", 0.41)
                    self.BEHAVIOR_FEATURES = bundle.get("features", self.BEHAVIOR_FEATURES)
                else:
                    self.model = bundle
                self.model_info.update({"model_loaded": True, "mode": "ml"})
            except Exception as e:
                self.model_info["note"] += f" (Load failed: {e})"

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score, expl = 0.05, ["Keystroke ATO (CMU 10-feature GBM)"]
        if self.model and any(f in data for f in self.BEHAVIOR_FEATURES):
            try:
                X = pd.DataFrame([data]).reindex(columns=self.BEHAVIOR_FEATURES, fill_value=0)
                if self.scaler: X = pd.DataFrame(self.scaler.transform(X), columns=self.BEHAVIOR_FEATURES)
                prob_auth = float(self.model.predict_proba(X)[0, 1])
                score = 1.0 - prob_auth  # risk is inverse of auth probability
                expl.append(f"Identity match: {prob_auth*100:.1f}% → risk {score:.4f}")
            except Exception as e:
                expl.append(f"ML Inference failed: {e}")
        if data.get("login_anomaly"):
            score = max(score, 0.95); expl.append("Login anomaly detected (impossible travel).")
        return RiskResult(provider_name="AccountTakeover", risk_score=score, confidence=0.89,
                          severity="CRITICAL" if score > 0.9 else "LOW",
                          event_category="EXPLOIT" if score > self.threshold else "NEUTRAL",
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


# PhishingRiskProvider removed — SocialEngineeringRiskProvider is now the URL phishing model


_META_KEYS = ["mean_dwell_time", "mean_flight_time", "typing_cadence", "backspace_frequency",
              "avg_mouse_velocity", "avg_mouse_acceleration", "mouse_path_straightness",
              "mouse_click_density", "navigation_speed", "interaction_density"]

class BeaconBehavioralProvider(RiskProvider):
    # 0.99 matches the training threshold used by the BEACON model creator
    CONFIDENCE_THRESHOLD = 0.99

    # Cosine similarity threshold for within-session embedding drift
    # ponytail: class predictions collapse to user-02 on banking data (distribution shift);
    # embeddings from the GAP layer retain more discriminative signal than softmax outputs
    DRIFT_THRESHOLD = 0.92

    # require this many consistent events before baseline is trusted
    _WARMUP = 3

    def __init__(self, model_path="models/beacon/best_model_varcnn_60WS_90OL_seq1024_thr0.99.pth"):
        self.net = None
        self._embed_cache: Dict[str, np.ndarray] = {}
        # warmup buffers: collect first N embeddings before locking baseline
        self._warmup_buf: Dict[str, list] = {}
        # stat baselines: (mean_iet, cv_iet) per session for gradual-drift detection
        self._stat_cache: Dict[str, tuple] = {}
        self.model_info = {"model_path": model_path, "model_loaded": False, "mode": "fallback",
                           "note": "BEACON VarCNN (Singh et al. 2026, arXiv:2605.10867). Embedding-drift mode."}
        if not _TORCH or not os.path.exists(model_path): return
        try:
            net = _VarCNN()
            net.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True), strict=True)
            net.eval(); self.net = net
            self.model_info.update({"model_loaded": True, "mode": "ml"})
        except Exception as e:
            self.model_info["note"] += f" (Load failed: {e})"

    def _seq(self, data: Dict[str, Any]):
        raw = data.get("inter_event_timings")
        # explicit None check — `or` on numpy arrays raises ambiguity error
        if raw is None:
            raw = [data[k] for k in _META_KEYS if k in data]
        # generators/iterables: materialise before len()
        if not isinstance(raw, (list, tuple, np.ndarray)): raw = list(raw)
        # require 64+ points — <64 (e.g. 10 META scalars) produces misleading embeddings
        # when padded to 1024 and compared against a full-sequence baseline
        if len(raw) < 64: return None
        arr = np.array(raw, dtype=np.float32)
        if not np.isfinite(arr).all():
            arr = np.nan_to_num(arr, nan=0.0, posinf=1e6, neginf=0.0)
        rng = arr.max() - arr.min()
        if rng > 0: arr = (arr - arr.min()) / rng
        padded = np.zeros(1024, dtype=np.float32)
        padded[:min(len(arr), 1024)] = arr[:1024]
        return torch.tensor(padded).unsqueeze(0).unsqueeze(0)

    def _embed(self, seq, meta):
        with torch.no_grad():
            x = F.relu(self.net.bn1(self.net.conv1(seq)))
            x = self.net.stage4(self.net.stage3(self.net.stage2(self.net.stage1(x))))
            return self.net.gap(x).squeeze(-1).squeeze(0).cpu().numpy()

    def evaluate(self, data: Dict[str, Any]) -> RiskResult:
        score, expl = 0.05, ["BEACON VarCNN behavioral fingerprint (embedding drift)"]
        if self.net:
            seq = self._seq(data)
            if seq is not None:
                try:
                    meta = torch.tensor([[float(data.get(k, 0)) for k in _META_KEYS]])
                    emb = self._embed(seq, meta)
                    norm = np.linalg.norm(emb)
                    sid = str(data.get("session_id", "")) if data.get("session_id") is not None else ""

                    # secondary stat check — catches gradual drift the VarCNN embedding misses
                    # stat baseline only set AFTER embed baseline locked (prevents warmup poisoning)
                    raw = data.get("inter_event_timings", [])
                    stat_score = 0.0
                    if len(raw) >= 10:
                        arr_raw = np.array(raw, dtype=np.float32)
                        arr_raw = arr_raw[np.isfinite(arr_raw)]
                        if len(arr_raw) >= 10:
                            m, s_ = float(arr_raw.mean()), float(arr_raw.std())
                            cv = s_ / (m + 1e-9)
                            if sid and sid in self._stat_cache:
                                bm, bcv = self._stat_cache[sid]
                                mean_z = abs(m - bm) / (bm * 0.5 + 1e-9)
                                cv_z   = abs(cv - bcv) / (bcv + 0.1)
                                stat_score = min(0.8, (mean_z + cv_z) / 2)
                                if stat_score > 0.3:
                                    expl.append(f"Stat drift: mean {bm:.0f}->{m:.0f}ms, CV {bcv:.2f}->{cv:.2f}")
                            # stat baseline is set below, only after embed baseline is locked

                    if norm < 1e-6:
                        score = max(0.4, stat_score)
                        expl.append("Degenerate embedding — constant/invalid input sequence.")
                    else:
                        emb_unit = emb / norm
                        if sid and sid in self._embed_cache:
                            baseline = self._embed_cache[sid]
                            cosine = float(np.dot(emb_unit, baseline))
                            if not np.isfinite(cosine):
                                score = max(0.4, stat_score)
                                expl.append("Non-finite cosine — suspect input.")
                            elif cosine < self.DRIFT_THRESHOLD:
                                embed_score = min(0.9, 1.0 - cosine)
                                score = max(embed_score, stat_score)
                                expl.append(f"Behavioral drift: cosine={cosine:.3f} -> risk {score:.2f}")
                            else:
                                score = stat_score
                                if score < 0.1:
                                    expl.append(f"Behavior consistent: cosine={cosine:.3f}")
                                self._embed_cache[sid] = 0.95 * baseline + 0.05 * emb_unit
                                # stat baseline on first consistent post-lock call — not during warmup
                                if sid and sid not in self._stat_cache and len(raw) >= 10:
                                    if len(self._stat_cache) >= 1000: self._stat_cache.pop(next(iter(self._stat_cache)))
                                    self._stat_cache[sid] = (m, cv)
                        elif sid:
                            # warmup: collect _WARMUP embeddings before locking baseline
                            # prevents single-event poisoning
                            if len(self._warmup_buf) >= 1000: self._warmup_buf.pop(next(iter(self._warmup_buf)))
                            buf = self._warmup_buf.setdefault(sid, [])
                            buf.append(emb_unit)
                            if len(buf) >= self._WARMUP:
                                baseline = np.mean(buf, axis=0)
                                baseline /= (np.linalg.norm(baseline) + 1e-9)
                                if len(self._embed_cache) >= 1000: self._embed_cache.pop(next(iter(self._embed_cache)))
                                self._embed_cache[sid] = baseline
                                del self._warmup_buf[sid]
                                # seed stat baseline from warmup timing so first-call poisoning can't set it
                                if sid not in self._stat_cache and len(raw) >= 10:
                                    if len(self._stat_cache) >= 1000: self._stat_cache.pop(next(iter(self._stat_cache)))
                                    self._stat_cache[sid] = (m, cv)
                                expl.append(f"Baseline locked after {self._WARMUP} events.")
                            else:
                                expl.append(f"Warming up ({len(buf)}/{self._WARMUP}).")
                        else:
                            score = stat_score
                            expl.append("No session ID — stateless." if score < 0.1 else f"Stat anomaly (no session): risk {score:.2f}")
                except Exception as e:
                    expl.append(f"Inference failed: {e}")
            else:
                expl.append("No timing sequence — skipped.")
        return RiskResult(provider_name="BeaconBehavioral (VarCNN)", risk_score=score,
                          confidence=1.0 - score,
                          severity="HIGH" if score >= 0.7 else ("MEDIUM" if score >= 0.4 else "LOW"),
                          event_category="EXPLOIT" if score >= 0.5 else "NEUTRAL",
                          explanations=expl, raw_features=data)
