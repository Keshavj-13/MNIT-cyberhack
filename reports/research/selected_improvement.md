# Selected Improvement: Stateful Threat Memory Layer

## Justification
The **Stateful Threat Memory Layer** has been selected as the highest ROI improvement for Cycle 1. 

### Why it won:
1.  **Fundamental Prerequisite**: Every advanced feature requested (Attack Progression Graphs, Narrative Explainability, Accumulative Risk) depends on the system's ability to recall previous events.
2.  **Scientific Validity**: Moving from stateless to stateful modeling is the single most significant step in maturing a security risk engine. It transforms the system from a "Static Filter" to a "Behavioral Analyst."
3.  **Hackathon Impact**: It allows the "Grandma" narrative to be actually implemented. We can show that even if her transaction *looks* normal, we block it because we *remember* the Smishing SMS she received 10 minutes ago.
4.  **Feasibility**: It can be implemented by adding a `SessionStore` and modifying the `RiskEngine` to ingest `SessionHistory`.

### Ratio Calculation:
- **Impact (10)**: Enables multi-stage detection.
- **Scientific Validity (10)**: UEBA industry standard.
- **Feasibility (8)**: No new infrastructure required (SQLite can handle this).
- **Complexity (4)**: Additive logic, no retraining.
- **Risk (3)**: Low risk of breaking classifiers.

**Score**: `(10 + 10 + 8) / (4 + 3) = 28 / 7 = 4.0`. (Significantly higher than other candidates).
