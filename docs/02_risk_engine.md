# 2. Risk Engine & Feature Extraction

This document covers the core scoring pipeline — the mechanism by which raw user behavior is converted into a risk score and an escalation decision.

---

## 2.1 Feature Extraction (`src/engine/features.py`)

### Purpose
The `FeatureExtractor` class converts raw telemetry events (keystroke timings, mouse movements, session navigation) into a flat dictionary of scalar features that ML providers can consume.

### Input Format
A list of event dictionaries, each with:
```json
{
  "type": "keystroke" | "mouse" | "session",
  "timestamp": 1719000000000,
  "data": { ... event-specific fields ... }
}
```

### Output
A dictionary with ~30 scalar features plus two special fields:
- `inter_event_timings` — raw millisecond deltas between consecutive events (fed to BEACON VarCNN)
- `current_url` — last `page_load` URL (fed to phishing URL model)

### Feature Groups

#### 2.1.1 Behavioral (Keystroke) Features

| Feature | Computation | Purpose |
|---------|------------|---------|
| `mean_dwell_time` | `mean(dwellTime)` for all `dwell` events | Average key hold duration |
| `mean_flight_time` | `mean(flightTime)` for all `flight` events | Average inter-key gap |
| `typing_cadence` | `std(flightTime)` | Typing rhythm consistency |
| `backspace_frequency` | `count(Backspace) / total_keystrokes` | Error correction rate |
| `dwell_mean/std/range` | Basic stats on dwell times | ATO model features |
| `flight_mean/std/range` | Basic stats on flight times | ATO model features |
| `lat_mean/std/range` | Stats on latency (`dwell + flight` per key pair) | Combined keystroke timing |
| `rhythm` | `flight_std / (flight_mean + ε)` | Coefficient of variation of flight times |
| `dwell_cv` | `dwell_std / (dwell_mean + ε)` | Normalised dwell variance |
| `flight_dispersion` | `flight_std × flight_range` | Flight timing spread |
| `lat_cv` | `lat_range / (lat_mean + ε)` | Normalised latency variance |
| `rhythm_abs` | `abs(rhythm) × 10` | Amplified rhythm signal |
| `dwell_flight_ratio` | `dwell_std / (flight_range + ε)` | Cross-modality timing ratio |

#### 2.1.2 Mouse Features

| Feature | Computation | Purpose |
|---------|------------|---------|
| `avg_mouse_velocity` | `mean(velocity)` for move events | Movement speed |
| `avg_mouse_acceleration` | `mean(Δv / Δt)` between consecutive moves | Movement acceleration |
| `mouse_path_straightness` | `displacement / total_path_length` | 1.0 = perfect line, 0.0 = erratic |
| `mouse_click_density` | `clicks / duration_minutes` | Click frequency |
| `mouse_jerk_mean/std/max` | Rate of change of acceleration | Movement smoothness (BEACON) |
| `mouse_direction_entropy` | Shannon entropy of 8-bin angle histogram | Direction randomness (BEACON) |
| `mouse_imi_mean/std` | Inter-movement interval stats | Movement rhythm (BEACON) |
| `mouse_speed_std/p90` | Speed distribution stats | Speed profile |

**Mouse Path Straightness Algorithm**:
```
displacement = sqrt((end_x - start_x)² + (end_y - start_y)²)
total_path = Σ sqrt((x[i] - x[i-1])² + (y[i] - y[i-1])²)
straightness = displacement / total_path    # 0.0–1.0
```

**Direction Entropy Algorithm**:
```
angles = arctan2(Δy, Δx) mod 360    # for consecutive points
bins = histogram(angles, 8 bins, range=[0,360])
p = bins / sum(bins)
entropy = -Σ p × log(p + ε)         # Shannon entropy
```

#### 2.1.3 Session Features

| Feature | Computation | Purpose |
|---------|------------|---------|
| `navigation_speed` | `page_load + tab_change events / duration_min` | Browsing speed |
| `interaction_density` | `total_events / duration_min` | Overall activity rate |
| `paste_rate` | `paste events / duration_min` | Paste frequency (social engineering signal) |
| `paste_digit_ratio` | `digit_pastes / total_pastes` | Digit content in pastes (MitM indicator) |
| `focus_switch_rate` | `blur events / duration_min` | Window switching rate (reference checking) |

#### 2.1.4 Special Fields

- **`inter_event_timings`**: Raw ms deltas between consecutive event timestamps. Fed directly to BEACON VarCNN as a 1024-point sequence. These are NOT aggregated — the raw rhythm is essential for the CNN.
- **`current_url`**: Last URL from `page_load` session events. Fed to the phishing URL classifier.

---

## 2.2 Risk Engine (`src/engine/risk_engine.py`)

### Purpose
The `RiskEngine` fuses outputs from all registered ML providers into a single risk score and decision. It implements weighted ensemble scoring, contextual weight adjustment, session risk accumulation, and attack-chain correlation.

### Class: `EngineResult`
The output of every evaluation:
```python
class EngineResult:
    overall_risk: float       # 0.0–1.0 final fused score
    decision: str             # ALLOW | CHALLENGE | RESTRICT | CONTAIN
    escalation_level: int     # 1–4
    confidence: float         # 0.0–1.0 weighted confidence
    provider_breakdown: Dict  # per-provider RiskResult objects
    recommendation: str       # human-readable action
    why_decision: str         # explanation string
```

### Algorithm: `evaluate_all(input_data, history)`

#### Step 1: Load Provider Weights
Weights loaded from `config/risk_settings.json`. Default:
```
TransactionRiskProvider:        0.40
SocialEngineeringRiskProvider:  0.20
AccountTakeoverProvider:        0.15
BeaconBehavioralProvider:       0.05
NetworkRiskProvider:            0.10
DeviceTrustProvider:            0.10
```
Weights are normalised to sum to 1.0 across all registered providers. Unknown providers default to 0.05.

#### Step 2: Contextual Weight Adjustment
If `amount > max_transfer_limit` (default 5000) OR `is_new_beneficiary == True`:
```
TransactionRiskProvider weight *= 1.5
Re-normalize all weights to sum to 1.0
```

#### Step 3: Provider Evaluation
Each provider's `evaluate(data)` is called, producing a `RiskResult` with:
- `risk_score` (0.0–1.0)
- `confidence` (0.0–1.0)
- `event_category` (LURE / HOOK / EXPLOIT / MONETIZE / NEUTRAL)
- `explanations` (list of human-readable strings)

#### Step 4: Weighted Fusion
```
weighted_score = Σ (provider_risk_score × provider_weight)
weighted_conf  = Σ (provider_confidence × provider_weight)
```

#### Step 5: Confidence Penalty
If the primary risk driver has low confidence but high risk:
```python
if primary_conf < 0.5 and primary_risk > 0.5:
    weighted_conf *= (1.0 - primary_risk * 0.5)
```

#### Step 6: Session Prior Blending
If the session is already at an elevated risk level (L2+), a prior risk baseline is injected:
```
prior = (risk_level - 1) × 0.25    # L2→0.25, L3→0.50, L4→0.75
score = min(1.0, score + prior × (1.0 - score))
```
This ensures risk accumulates within a session — a single clean event doesn't immediately drop a flagged session.

#### Step 7: Attack-Chain Correlation Multipliers
The engine examines the last 5 historical events for attack progression patterns:

| Pattern | Multiplier | Trigger |
|---------|:---:|---|
| **LURE → HOOK/EXPLOIT** | ×1.3 | Recent phishing (LURE score > 0.5) followed by current HOOK or EXPLOIT |
| **LURE/HOOK → MONETIZE** | ×1.5 | Social engineering precursor followed by monetary transfer |
| **EXPLOIT → MONETIZE** | ×1.5 | Account takeover followed by transfer attempt |

Category detection uses per-provider `category_scores` (max risk_score per category from the provider breakdown), NOT the aggregate overall_risk. This prevents the weight dilution problem where a single provider's contribution to overall_risk is capped by its weight and could never exceed threshold.

#### Step 8: Decision Thresholds

| Score Range | Level | Decision | Action |
|---|:---:|---|---|
| `< 0.20` | L1 | ALLOW | Continue monitoring |
| `0.20 – 0.40` | L2 | CHALLENGE | Request OTP/MFA step-up |
| `0.40 – 0.70` | L3 | RESTRICT | Block high-value transfers, freeze sensitive actions |
| `≥ 0.70` | L4 | CONTAIN | Terminate session, lock account, escalate to SOC |

Thresholds are configurable via `config/risk_settings.json`.

---

## 2.3 Evaluation Runner (`src/api/internal/evaluation_runner.py`)

### Purpose
The evaluation runner is the orchestration layer that connects the API endpoints to the Risk Engine. It handles:
1. Telemetry fetching and feature extraction
2. Session history retrieval
3. Session prior risk injection
4. Risk Engine invocation
5. SecurityEvent persistence

### Algorithm: `run_evaluation(payload, db)`

1. **Fetch Telemetry**: Query all `TelemetryData` rows for this `session_id`, convert timestamps to epoch ms.
2. **Extract Features**: Run `FeatureExtractor.extract_features()` on the telemetry events.
3. **Enrich Payload**: Merge extracted features into the API request payload (API fields take precedence via dict merge order).
4. **Fetch History**: Last 10 `SecurityEvent` rows for this `user_id`, chronologically ordered.
5. **Build Session History**: Convert DB events to `SessionEvent` models with `category_scores` derived from the breakdown JSON.
6. **Inject Prior Risk**: If the session's `CustomerSession.risk_level > 1`, add `session_prior_risk = (level - 1) * 0.25`.
7. **Evaluate**: `RiskEngine(providers).evaluate_all(enriched_payload, history)`.
8. **Determine Category**: Find the dominant event category from the provider with the highest risk score above 0.5.
9. **Persist**: Create a `SecurityEvent` record with the full result, including crypto-rotation annotations in `why_decision` if the escalation level changed.

### Provider Registration
Providers are registered at import time in `evaluation_runner.py`:
```python
_registry.register_provider(TransactionRiskProvider())
_registry.register_provider(SocialEngineeringRiskProvider())
_registry.register_provider(NetworkRiskProvider())
_registry.register_provider(DeviceTrustProvider())
_registry.register_provider(BeaconBehavioralProvider())  # includes AccountTakeoverProvider as ensemble member
```

Note: `AccountTakeoverProvider` is NOT registered separately — it is instantiated inside `BeaconBehavioralProvider` and used as a 5% ensemble member.

---

## 2.4 Provider Registry (`src/engine/registry.py`)

A singleton that holds the list of active `RiskProvider` instances. Prevents duplicate registration via class-name check.

```python
class ProviderRegistry:
    _instance = None          # Singleton
    _providers: List = []     # All registered providers

    register_provider(p)      # No-op if class already registered
    get_providers() → List    # Returns all providers
    clear_registry()          # Empties the list
```

## 2.5 Session Models (`src/engine/session_models.py`)

`SessionEvent` is the Pydantic model used to pass historical event data to the correlation engine:

```python
class SessionEvent:
    user_id: str
    session_id: str
    event_category: str           # LURE, HOOK, EXPLOIT, MONETIZE, NEUTRAL
    timestamp: datetime
    risk_score: float
    confidence: float
    explanations: List[str]
    input_payload: Dict
    category_scores: Dict[str, float]  # {LURE: 0.8, EXPLOIT: 0.6, ...}
```

The `category_scores` field is computed in `evaluation_runner.py::_category_scores()` by taking the max `risk_score` per `event_category` across all providers in the breakdown.
