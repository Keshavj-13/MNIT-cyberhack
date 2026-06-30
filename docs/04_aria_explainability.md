# 4. ARIA & Explainability

---

## 4.1 ARIA — Autonomous Risk Intelligence Agent (`src/agents/aria.py`)

### Purpose
ARIA is a fully autonomous background agent that continuously scans for suspicious activity clusters, classifies attack patterns, generates explainability charts, and calls a Vision Language Model (VLM) to produce natural-language threat assessments. Nobody calls it — it decides when to act.

### Lifecycle
ARIA is started as an asyncio background task when the Admin API boots:
```python
# admin_api.py startup
asyncio.create_task(aria.run())
```

### Configuration Constants
| Constant | Value | Purpose |
|----------|:---:|---|
| `CYCLE_SECS` | 12 | Scan interval (short so ARIA fires during a 15-second demo) |
| `WINDOW_MINS` | 10 | Rolling time window for event clustering |
| `MIN_CLUSTER` | 3 | Minimum events before ARIA investigates a cluster |
| `MIN_RISK` | 0.3 | Ignore events below this risk threshold |

### Main Loop Algorithm (`run()`)

```
while True:
    await sleep(12 seconds)
    await asyncio.to_thread(_scan_and_investigate)    # blocking DB/VLM in thread
```

### Scan & Investigate Algorithm (`_scan_and_investigate()`)

1. **Query Recent Events**: All `SecurityEvent` rows from the last 10 minutes with `overall_risk ≥ 0.3`.

2. **Cluster by User**: Group events by `user_id` into per-user clusters.

3. **Filter**: Skip clusters with fewer than 3 events.

4. **Check Existing**: If an `AriaInvestigation` already exists for this `cluster_key` (user_id) with status `open`:
   - Merge new event IDs into `cluster_event_ids`
   - Increment `cycle` counter
   - Skip full re-investigation

5. **Classify Attack Pattern** (`_classify()`):

   | Condition | Classification | Hypothesis |
   |-----------|---------------|------------|
   | LURE + MONETIZE in categories | `social_engineering_chain` | LURE→MONETIZE attack chain |
   | EXPLOIT + MONETIZE | `ato_fraud` | Account takeover + fraudulent transaction |
   | ≥3 events with score > 0.6 | `coordinated_attack` | Coordinated attack suspected |
   | Default | `elevated_cluster` | Manual review recommended |

6. **Build Explainability Charts**: For the highest-risk event in the cluster:
   - Call `contributions_for_provider(provider, payload)` for each registered provider
   - Generate individual bar charts via `make_chart()`
   - Stitch into a multi-panel grid via `make_grid_chart()`

7. **Generate Event Summary**: Chronological one-line summaries with timestamps, decisions, risk scores, top providers, and action context (transfer amounts, beneficiary names).

8. **VLM Assessment**: Call Qwen3.5-0.8B with the grid chart image and event summary:
   - **Remote**: If `VLM_API_URL` env var is set, call OpenAI-compatible endpoint
   - **Local**: Load transformers pipeline on first call, use `image-text-to-text` task
   - **Fallback**: If VLM fails, generate a grounded text-only timeline from actual event data

9. **Compute Confidence** (`_confidence()`):
   ```python
   base = min(1.0, mean(scores) × 1.5)
   if LURE and MONETIZE both present: base += 0.2
   ```

10. **Persist**: Create `AriaInvestigation` record in DB.

### Grounded Fallback (`_generate_grounded_fallback()`)
When VLM is unavailable, generates a structured text report from actual event data:
- Chronological timeline with timestamps, decisions, risk percentages
- Kill chain detection: checks for LURE → HOOK → EXPLOIT → MONETIZE stages
- Cryptographic response summary (key rotation, session deactivation)

### VLM Prompt Template
```
You are a fraud analyst reviewing a security cluster.
ARIA's hypothesis: {hypothesis}.
Event risk scores and categories: {event_summaries}.
The image shows feature importance bar charts from multiple ML providers.
Red bars push risk up, green push risk down.
In 3-4 sentences: Does the visual evidence support or contradict the hypothesis?
Which provider shows the most suspicious pattern? Any signs of false positives?
```

### Helper Functions

| Function | Purpose |
|----------|---------|
| `_short_provider(name)` | Strips "RiskProvider"/"BehavioralProvider"/"Provider" suffixes for display |
| `_top_provider(event)` | Returns (name, score) of highest-risk provider in breakdown |
| `_payload_context(event)` | Extracts human-readable action context (transfer amount, beneficiary name, paste detection) |

---

## 4.2 Explainability Module (`src/explainability/explain.py`)

### Purpose
Generates per-provider feature contribution charts for both ARIA investigations and on-demand admin analysis.

### Core Algorithm: `_top5_contributions(model, feature_names, X)`

For GBM/tree-based models that expose `feature_importances_`:

1. Normalize importances to [0, 1]: `imp_norm = imp / max(imp)`
2. Get feature values from the input sample
3. If any non-zero features exist:
   ```python
   contributions = imp_norm × (values / max_abs_value)
   ```
   This gives signed contributions: positive = risk-increasing, negative = risk-decreasing
4. If all features are zero (sparse payload):
   ```python
   contributions = imp_norm    # show top features by global importance
   ```
5. Return top 5 by absolute contribution magnitude

### Provider-Specific Contribution Logic (`contributions_for_provider()`)

| Provider | Feature Preparation |
|----------|-------------------|
| `TransactionRiskProvider` | Reindex to stored features, encode categoricals, handle unknown categories |
| `AccountTakeoverProvider` | Reindex to 15 behavior features, apply RobustScaler |
| `SocialEngineeringRiskProvider` | Extract 8 URL-lexical features from `current_url` |

### Chart Rendering

#### Individual Chart (`make_chart()`)
- Horizontal bar chart using matplotlib
- Red bars = risk-increasing contributions
- Green bars = risk-decreasing contributions
- Vertical dashed line at x=0
- Title includes provider name, score, and decision
- Output: base64-encoded PNG string

#### Grid Chart (`make_grid_chart()`)
- Stitches multiple provider charts into a 2-column grid
- Title overlay at top
- Used as input image for VLM analysis
- Output: base64-encoded PNG string

### Auto Summary (`auto_summary()`)
Generates a one-line text summary:
```
"Score 0.847 driven by: flight_mean=234, dwell_std=45, rhythm=1.2."
```
If no risk drivers found:
```
"Score 0.123: no strong risk drivers — possible false positive."
```

---

## 4.3 Admin API Integration

### On-Demand Explainability (`GET /admin/events/{id}/explain`)
Returns per-provider contributions + chart PNGs + text summaries for a specific event.

### On-Demand VLM Analysis (`POST /admin/events/{id}/analyze`)
Builds a grid chart for the event's provider breakdown and calls the VLM for a single-event assessment.

### ARIA Investigation Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/admin/aria/investigations` | GET | List investigations, filterable by status |
| `/admin/aria/investigations/{id}` | GET | Full detail including regenerated charts |
| `/admin/aria/investigations/{id}/status` | PATCH | Update status: `open` / `resolved` / `fp_confirmed` |

### Biometric Visuals (`generate_biometric_visuals()`)
Generated for the Admin event detail view:

1. **Timing Sequence**: Last 24 inter-event timings from real telemetry
2. **Temporal Risk/Confidence History**: Per-event risk and confidence across all events for this user
3. **SHAP Attribution**: Top 5 feature contributions across all providers (using `contributions_for_provider()`)
4. **Model Internals**: Sequence length, cold-start status, embedding similarity, crypto tier
