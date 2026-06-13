# Current State Audit: Banking Threat Detection Platform

## 1. System Components Audit

| Component | Logic Type | Implementation Status | Weakness |
| :--- | :--- | :--- | :--- |
| **Risk Engine** | Weighted Average | Stateless / Static | Treats 10 small risks as 1 small risk; ignores timing. |
| **Providers** | GBDT / Rules | Fixed / Decoupled | No cross-talk; cannot query session history. |
| **Persistence** | SQLite (Event Log) | Basic Storage | Lacks an 'Attack Graph' or 'Session' abstraction. |
| **API Layer** | FastAPI / REST | Functional | Synchronous; purely reactive to current payload. |
| **Frontend** | React / Dashboard | Visual | Shows snapshots; lacks a 'Narrative' of attack progression. |
| **Attack Chain** | Simulated | Heuristic | Logic is hardcoded in specific Providers instead of the Engine. |

## 2. Identified Architectural Weaknesses

1.  **Temporal Blindness**: The system has no concept of "velocity of suspicion." A login from a new device (Medium Risk) should be weighted differently if it follows a Smishing SMS (High Risk) vs. occurring in isolation.
2.  **Stateless Inference**: `evaluate_all` takes `input_data` and returns a result. It does not ingest the *User Session History*. This prevents the detection of "Slow and Low" attacks.
3.  **Broken Abstractions**: The `PhishingRiskProvider` currently looks for `url` in the payload. If the URL was sent in a previous SMS (Smishing event), and the current payload is a `Login` event, the Phishing provider returns 0 risk, losing the "Hook" context.
4.  **Flat Persistence**: `security_events` table is a flat list. There is no linkage between Event A (SMS) and Event B (Login) for the same user.

## 3. Opportunities for Attack Chain Intelligence

- **The Memory Gap**: Introducing a `SessionMemory` store that persists state between API calls.
- **Correlation Engine**: A layer that identifies the transition from `LURE` (Social Engineering) to `HOOK` (Phishing/Navigation) to `EXPLOIT` (ATO).
- **Cumulative Decay**: Implementing a risk score that increases with frequency but decays with time.

## 4. Evidence of Current Logic
`src/engine/risk_engine.py`:
```python
for provider in self.providers:
    res = provider.evaluate(input_data)
    # ...
    total_score += res.risk_score * weight
```
The above code proves the **Independence Assumption** - each provider only sees the *current* data, making multi-stage correlation impossible.
