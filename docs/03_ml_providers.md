# 3. ML Providers Deep-Dive

This document provides an in-depth analysis of each risk provider — its dataset, model type, input schema, scoring algorithm, and fallback logic.

All providers implement the `RiskProvider` abstract base class and return a `RiskResult`:

```python
class RiskResult:
    provider_name: str
    risk_score: float          # 0.0–1.0
    confidence: float          # 0.0–1.0
    severity: str              # LOW | MEDIUM | HIGH | CRITICAL
    event_category: str        # LURE | HOOK | EXPLOIT | MONETIZE | NEUTRAL
    explanations: List[str]    # Human-readable reasoning chain
    raw_features: Dict         # Input data echo for audit
```

---

## 3.1 TransactionRiskProvider

**File**: `src/providers/implementations.py`  
**Model Artifact**: `models/artifacts/transaction_risk.joblib`  
**Features Artifact**: `models/artifacts/transaction_features.joblib`

### Dataset
- **Feedzai Bank Account Fraud (BAF)**: ~500K–1M transaction records with binary `fraud_bool` label
- Class-weighted training to fix recall on the minority (fraud) class
- F1-optimal threshold stored in the bundle

### Model
LightGBM gradient boosted classifier, serialised as a joblib bundle:
```python
{
    "model": LGBMClassifier,
    "threshold": 0.XXX,       # F1-optimal decision boundary
    "cat_cols": [...],         # Categorical column names
    "encoders": {...},         # LabelEncoder per categorical column
}
```

### Input
31 numeric/categorical features from the Feedzai BAF schema. At inference, the provider:
1. Creates a DataFrame from the input payload
2. Reindexes to the stored feature list (missing features → 0)
3. Encodes categorical columns using stored `LabelEncoder` instances
4. Converts any remaining object columns to numeric

### Scoring Algorithm
```python
score = model.predict_proba(X)[0, 1]    # P(fraud)
```
Additional heuristic: if `amount > 10000`, score is floored at 0.9.

### Event Category Logic
- `score > threshold` → `MONETIZE` (fraudulent transaction)
- Otherwise → `NEUTRAL`

### Fallback
If the model file is missing or loading fails, returns a static score of 0.1 ("fallback mode").

---

## 3.2 SocialEngineeringRiskProvider (URL Phishing)

**File**: `src/providers/implementations.py`  
**Model Artifact**: `models/artifacts/phishing_url_risk.joblib`

### Dataset
- **Phishing Websites (ARFF)**: ~11K URLs with binary phishing/legitimate label
- AUC = 0.956 on test set

### Model
GBM classifier in a joblib bundle with threshold.

### Input: 8 URL-Lexical Features
Computed by the `_url_features(url)` helper function from any URL string, with no DNS or API calls:

| Feature | Logic | Value |
|---------|-------|-------|
| `having_IP_Address` | URL domain contains IP pattern `\d{1,3}(\.\d{1,3}){3}` | -1 (yes) / 1 (no) |
| `URL_Length` | `len(url)` | -1 (>75) / 0 (54–75) / 1 (<54) |
| `having_At_Symbol` | `@` present in URL | -1 / 1 |
| `double_slash_redirecting` | `//` in URL path | -1 / 1 |
| `Prefix_Suffix` | `-` in domain | -1 / 1 |
| `having_Sub_Domain` | Count of `.` separators minus 2 | -1 (>1) / 0 (1) / 1 (0) |
| `SSLfinal_State` | URL starts with `https` | 1 (yes) / -1 (no) |
| `HTTPS_token` | `https` appears in domain string | -1 (yes) / 1 (no) |

### Scoring Algorithm
```python
score = model.predict_proba(X)[0, 1]    # P(phishing)
```

### Paste Heuristic Boost
If `paste_rate > 0` and `paste_digit_ratio > 0.5` (user is pasting digit-heavy content, a social engineering indicator):
```python
boost = min(0.35, paste_rate * 0.15 + paste_digit_ratio * 0.20)
score = min(1.0, score + boost * (1.0 - score))
```

### Event Category
- `score > threshold` → `LURE` (social engineering entry point)
- Otherwise → `NEUTRAL`

### Fallback
No URL in payload → score = 0.05, explanation "No URL in payload — skipped."

---

## 3.3 AccountTakeoverProvider (Keystroke Biometrics)

**File**: `src/providers/implementations.py`  
**Model Artifact**: `models/artifacts/behavioral_risk.joblib`

### Dataset
- **CMU Keystroke Dynamics**: ~20K keystroke timing samples across multiple subjects
- Retrained on aggregated features matching the live FeatureExtractor output schema

### Model
GBM classifier + RobustScaler, supporting two inference modes:

1. **Mahalanobis Mode**: Computes the Mahalanobis distance from a per-user enrolled baseline
2. **Classification Mode**: Binary classifier predicting `P(authorized_user)`

The mode is determined by the `mode` field in the joblib bundle.

### Input: 15 Keystroke Features
```
dwell_mean, dwell_std, dwell_range
flight_mean, flight_std, flight_range
lat_mean, lat_std, lat_range
rhythm
dwell_cv, flight_dispersion, lat_cv, rhythm_abs, dwell_flight_ratio
```

### Scoring Algorithm

#### Cold-Start Guard
Requires at least 3 non-zero features before scoring. Zero-filled defaults from FeatureExtractor (no real keystrokes yet) would score incorrectly high against the enrolled baseline.

#### Mahalanobis Mode
```python
from scipy.spatial.distance import mahalanobis
d = mahalanobis(x_scaled, mean_vec, cov_inv)
risk = clip(d / adaptive_threshold, 0, 1)
```
Where `adaptive_threshold = mean + 3σ` of the enrolled user's own distance scores.

#### Classification Mode
```python
prob_authorized = model.predict_proba(X_scaled)[0, 1]
risk = 1.0 - prob_authorized    # lower match → higher risk
```

### Additional Heuristic
If `login_anomaly` flag is set (impossible travel), risk is floored at 0.95.

### Event Category
- `score > threshold` → `EXPLOIT` (account takeover signal)
- Otherwise → `NEUTRAL`

---

## 3.4 NetworkRiskProvider (Heuristic)

**File**: `src/providers/implementations.py`

### Model
No ML model. Pure rule-based heuristics on HTTP session metadata.

### Input Flags
| Flag | Score Floor | Severity |
|------|:---:|---|
| `vpn_detected` or `proxy_detected` | 0.40 | Moderate |
| `tor_detected` | 0.75 | High |
| `impossible_geo` | 0.80 | High |
| `blacklisted_ip` | 0.90 | Critical |

### Scoring
Score is the maximum of the base (0.05) and all triggered flag scores. Confidence is fixed at 0.85.

### Event Category
- `score > 0.5` → `EXPLOIT`
- Otherwise → `NEUTRAL`

### Design Decision
The original SIMARGL2021 packet-level network model was removed because packet-level features (flow duration, fwd/bwd packet lengths, flow bytes/s) are not available from browser-based banking session telemetry. Only HTTP connection metadata (VPN, proxy, geo) is available at the API boundary.

---

## 3.5 DeviceTrustProvider (Rule-Based)

**File**: `src/providers/implementations.py`

### Input Flags
| Flag | Score |
|------|:---:|
| `vpn_detected` | 0.45 |
| `rooted` (jailbroken) | 0.98 |

### Scoring
Max of base (0.05) and triggered flags. Confidence = 1.0 (deterministic rules).

### Event Category
Always `NEUTRAL` (device risk is a supporting signal, not a kill-chain stage).

---

## 3.6 BeaconBehavioralProvider (VarCNN Deep Learning)

**File**: `src/providers/implementations.py`  
**Model Artifact**: `models/beacon/best_model_varcnn_60WS_90OL_seq1024_thr0.99.pth`

### Research Origin
BEACON: Singh et al. 2026, arXiv:2605.10867. Pre-trained VarCNN on gameplay behavioral sequences. **Not retrained** for banking — used in embedding-drift mode.

### Architecture: `_VarCNN`
Reverse-engineered from checkpoint key shapes:

```
Input: (batch, 1, 1024) — 1024-point timing sequence
  │
  ├── Stem: Conv1d(1, 64, kernel=7, padding=3) → BN → ReLU
  │
  ├── Stage 1: 2× IdentityBlock(64)          → (batch, 64, 1024)
  ├── Stage 2: ProjectionBlock(64→128) + IdentityBlock(128)
  ├── Stage 3: ProjectionBlock(128→256) + IdentityBlock(256)
  ├── Stage 4: ProjectionBlock(256→512) + IdentityBlock(512)
  │
  ├── GAP: AdaptiveAvgPool1d(1) → (batch, 512)  ← EMBEDDING USED
  │
  ├── Metadata MLP: Linear(10→128) → BN       (10 mouse features)
  │
  └── Classifier: [Flatten, Linear(640→512), BN, ReLU, Dropout(0.5), Linear(512→28)]
                   ↑ NOT USED — class predictions collapse to user-02 due to distribution shift
```

**Key Insight**: The 28-class softmax is NOT used at inference. Only the **512-d GAP embedding** is extracted, which retains discriminative behavioral information even under distribution shift from gaming to banking data.

### Input Preparation (`_seq()`)
1. Extract `inter_event_timings` from data (raw ms deltas)
2. Require ≥64 points (below this, embeddings from padded sparse sequences are misleading)
3. Replace non-finite values with 0
4. **Min-max normalize** (NOT z-score — z-score collapses all distributions to N(0,1), destroying the rhythm VarCNN needs)
5. Zero-pad to 1024 points
6. Reshape to `(1, 1, 1024)` tensor

### Metadata Vector
10 scalar mouse features fed to the metadata MLP branch:
```
avg_mouse_velocity, avg_mouse_acceleration, mouse_path_straightness,
mouse_click_density, mouse_jerk_mean, mouse_jerk_std,
mouse_direction_entropy, mouse_imi_mean, mouse_speed_std, mouse_speed_p90
```

### Scoring Algorithm: Embedding Drift

#### Warmup Phase (first 3 events per session)
1. Extract 512-d embedding from GAP layer
2. Normalize to unit vector
3. Collect in warmup buffer
4. After 3 events: compute mean baseline, normalize, lock as session baseline
5. Set stat baseline (mean IET, CV of IET) for secondary check

#### Drift Detection (post-warmup)
1. Extract new embedding, normalize
2. Compute cosine similarity with locked baseline
3. If `cosine < 0.98` (DRIFT_THRESHOLD):
   - `embed_score = min(0.9, 1.0 - cosine)`
4. If cosine ≥ 0.98 (consistent):
   - Exponential moving average update: `baseline = 0.95 × baseline + 0.05 × new_embedding`
   - Score = stat_score (from secondary check)

#### Secondary Statistical Check
Catches gradual drift that the embedding might miss:
```python
mean_z = |current_mean_iet - baseline_mean_iet| / (baseline_mean * 0.5 + ε)
cv_z   = |current_cv - baseline_cv| / (baseline_cv + 0.1)
stat_score = min(0.8, (mean_z + cv_z) / 2)
```

#### Ensemble with ATO
The final score blends BEACON (95%) with the legacy `AccountTakeoverProvider` (5%):
```python
final_score = beacon_score * 0.95 + ato_score * 0.05
```

### Event Category
- `final_score ≥ 0.5` → `EXPLOIT`
- Otherwise → `NEUTRAL`

### Torch Guard
All PyTorch-dependent classes (`_VarCNN`, `_W`, `_IB`, `_PB`) are inside an `if _TORCH:` guard. Customer/Attacker/Showcase containers run without torch, falling back to the ATO-only provider.

---

## 3.7 Legacy Providers (Unused)

The `src/providers/` directory contains additional provider files from earlier development:

| File | Class | Status |
|------|-------|--------|
| `context.py` | `ContextRiskProvider` | **Unused** — fused SMS scam + phishing URL + rules. Replaced by `SocialEngineeringRiskProvider` in `implementations.py` |
| `device.py` | `DeviceTrustProvider` | **Unused** — superseded by the version in `implementations.py` |
| `network.py` | `NetworkRiskProvider` | **Unused** — SIMARGL packet-level model. Replaced by heuristic version in `implementations.py` |
| `transaction.py` | `TransactionRiskProvider` | **Unused** — earlier version. Replaced by Feedzai BAF version in `implementations.py` |

All active providers are defined in `src/providers/implementations.py` and registered in `evaluation_runner.py`.

---

## 3.8 Model Artifacts Summary

| Artifact File | Size | Contents |
|---|---:|---|
| `transaction_risk.joblib` | 1.7 MB | LightGBM model + threshold + categorical encoders |
| `transaction_features.joblib` | 620 B | Ordered list of 31 feature names |
| `phishing_url_risk.joblib` | 494 KB | GBM model + threshold |
| `behavioral_risk.joblib` | 3.1 KB | GBM/Mahalanobis model + RobustScaler + mean_vec + cov_inv |
| `behavioral_features.joblib` | 213 B | Ordered list of 15 feature names |
| `best_model_varcnn_*.pth` | 16.9 MB | PyTorch VarCNN state_dict |

### Platt Scaling
A `_apply_platt(raw_score, a, b)` utility exists for post-hoc probability calibration:
```python
logit = log(clip(score) / (1 - clip(score)))
calibrated = 1 / (1 + exp(-(a × logit + b)))
```
Used by `_load_calibrated_bundle()` which looks for `platt_a` and `platt_b` in joblib bundles. Defaults to identity (a=1, b=0) if not present.
