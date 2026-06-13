# Attack Chain Architecture Audit & Design

## 1. Current Architectural State
The platform currently utilizes a **Modular Provider Pattern** with a central **Weighted Risk Engine**.

### Current Logic:
1.  **Request Ingestion**: A single JSON payload is received containing multiple potential signals (text, URL, flags, amount).
2.  **Parallel Evaluation**: Registered `RiskProvider` instances evaluate the same payload independently.
3.  **Static Aggregation**: The `RiskEngine` performs a weighted arithmetic mean of scores.
4.  **Threshold-based Escalation**: Final scores trigger discrete security levels (Monitor -> Challenge -> Restrict -> Contain).

---

## 2. Identified Weaknesses
1.  **Statelessness**: The platform treats every request as an isolated event. It does not remember that a "Normal" transaction occurring 5 minutes after a "High Risk" Smishing event is suspicious.
2.  **No Evidence Propagation**: Providers do not share context. The `TransactionRiskProvider` is unaware that the `PhishingRiskProvider` just flagged a critical threat on the same session.
3.  **Snapshot-Only Risk**: Risk does not "accumulate" over time; it is calculated per request. A user receiving 10 low-risk phishing links over an hour should have a higher aggregate risk than a user receiving one.
4.  **Flat Modeling**: Attack progression is modeled as a list of independent flags rather than a stateful "kill chain."

---

## 3. Advanced Design: Graph-Based Attack Progression
To move from *score aggregation* to *intelligence*, the platform should model the attack as a directed acyclic graph (DAG) or a state machine.

### Attack States:
*   **RECON**: Neutral behavior, standard logins.
*   **LURE**: Suspected SMS/Email received.
*   **HOOK**: User interacts with suspected malicious artifact (URL click).
*   **EXPLOIT**: Login anomaly, MFA bypass attempt, device change.
*   **MONETIZE**: Fraudulent transaction, beneficiary change.

### Design Proposal:
Implement a **Stateful Attack Context Manager (SACM)** that sits between the Providers and the Engine.

1.  **Session Persistence**: Every event is tied to a `SessionID`.
2.  **Event Correlation**: The SACM looks for "State Transitions."
    *   Transition: `LURE` -> `HOOK` increases risk multiplier by 1.5x.
    *   Transition: `HOOK` -> `EXPLOIT` triggers immediate **RESTRICT** regardless of individual scores.
3.  **Evidence Memory**:
    *   If `PhishingDetector` flags a URL, that URL is stored in the session evidence.
    *   Subsequent `TransactionRisk` checks scan the evidence for `HOOK` state to apply a "Coercion Penalty."

---

## 4. Timeline-Based Risk Accumulation
Risk should be modeled as a **decaying cumulative function**.

*   **Formula**: `TotalRisk(t) = CurrentScore + Sum(HistoricalScores * e^(-decay * delta_t))`
*   **Impact**: Recent threats maintain high risk levels, while older, un-exploited lures slowly fade into the background.

---

## 5. Explainability Strategy: The Narrative Chain
Instead of just SHAP values for one model, the platform will produce a **Narrative Audit**:

> "Risk increased to 0.85 because a **Smishing Lure** (High Confidence) was followed by a **Phishing Hook** (Medium Confidence) within 12 minutes, followed by an **Anomalous Transaction** attempt."

---

## 6. Comparison Table: Intelligence Levels

| Feature | Current Platform | Advanced Attack Chain | Impact |
| :--- | :--- | :--- | :--- |
| **Logic** | Static Weighting | Dynamic State Machine | Detects multi-stage scams |
| **Memory** | Stateless | Session-Aware | Prevents "Death by a thousand cuts" |
| **Context** | Provider-Isolated | Evidence-Sharing | Correlates unrelated events |
| **Risk** | Threshold-based | Trend & Acceleration based| Proactive escalation |

---

## 7. Next Steps for Implementation
1.  **Update Database Schema**: Add `session_id` and `event_chain` tables.
2.  **Implement SACM**: A middleware that maintains state and updates the cumulative risk function.
3.  **Refactor Providers**: Allow providers to query the `SACM` for session history (e.g., "Has this user clicked a link in the last 30 minutes?").
4.  **UI Timeline View**: Update the frontend to visualize the "State Transition" through the kill chain.
