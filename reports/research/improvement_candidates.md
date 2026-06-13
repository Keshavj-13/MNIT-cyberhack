# Improvement Candidates: Platform Architecture

Based on the `current_state_audit.md`, the following architectural improvements are proposed to move the platform toward true attack chain intelligence.

## Candidate 1: Stateful Threat Memory Layer (The "Session Brain")
- **Problem Solved**: Statelessness. Enables cross-event correlation.
- **Expected Impact**: Detects multi-stage attacks where individual events are low-risk but the sequence is high-risk.
- **Engineering Complexity**: Medium (Database schema update + Cache layer).
- **Demo Value**: High (Visualizes "How we remembered the suspicious SMS from 10 minutes ago").
- **Scientific Validity**: High (Standard in UEBA/SIEM architectures).
- **Implementation Risk**: Low (Additive, does not break existing providers).

## Candidate 2: Dynamic Kill-Chain State Machine
- **Problem Solved**: Linear score aggregation.
- **Expected Impact**: Automatically escalates risk if the user moves from `LURE` -> `HOOK` -> `EXPLOIT`.
- **Engineering Complexity**: High (Requires formalizing state transitions).
- **Demo Value**: Extreme (The UI shows the attack "progressing" through stages).
- **Scientific Validity**: High (Aligns with MITRE ATT&CK / Cyber Kill Chain).
- **Implementation Risk**: Medium (Requires deep changes to RiskEngine logic).

## Candidate 3: Decaying Cumulative Risk Function
- **Problem Solved**: Temporal blindness.
- **Expected Impact**: High-frequency suspicious acts trigger faster escalation than isolated ones.
- **Engineering Complexity**: Low (Mathematical refactor in RiskEngine).
- **Demo Value**: Medium (Shows a "Risk Acceleration" curve).
- **Scientific Validity**: Medium.
- **Implementation Risk**: Low.

## Candidate 4: Narrative Explainability Engine
- **Problem Solved**: Non-human-readable SHAP outputs.
- **Expected Impact**: Generates natural language audit trails (e.g., "Grandma is being coached because...").
- **Engineering Complexity**: Medium (LLM or Template-based synthesis).
- **Demo Value**: High (Judges love storytelling).
- **Scientific Validity**: Low.
- **Implementation Risk**: Low.

---

## Ranking (ROI = Impact / Complexity)

| Rank | Candidate | Impact | Complexity | ROI Score |
| :--- | :--- | :---: | :---: | :---: |
| **1** | **Stateful Threat Memory Layer** | 10 | 4 | **2.5** |
| **2** | **Kill-Chain State Machine** | 9 | 7 | **1.3** |
| **3** | **Narrative Explainability** | 6 | 5 | **1.2** |
| **4** | **Decaying Risk Function** | 5 | 5 | **1.0** |

**Selection**: **Candidate 1 (Stateful Threat Memory Layer)**. It is the fundamental prerequisite for all other advanced intelligence. Without memory, state machines and narratives remain superficial.
