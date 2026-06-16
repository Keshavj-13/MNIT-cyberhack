# Multimodal Risk Fusion Audit Report
**Agent:** FUSION_AGENT
**Timestamp:** 2026-06-13 14:00:00 (Start) / 2026-06-13 14:15:00 (Finish)

## 1. Fusion Implementation Source
The risk fusion logic is implemented in `src/engine/risk_engine.py`. This engine performs weighted aggregation of scores from multiple specialized risk providers.

## 2. Weighted Fusion Algorithm
The `RiskEngine` class uses a normalized weighted sum of individual provider scores.

### Exact Mathematical Formula
The base weighted score is calculated as:
$$Score_{base} = \sum_{i=1}^{n} (RiskScore_i \cdot w_i)$$
Where:
- $n$ is the number of registered providers.
- $w_i$ is the normalized weight of provider $i$, such that $\sum w_i = 1.0$.

### Dynamic Context Boosting
The engine performs **Contextual Weight Adjustment** based on input attributes:
```python
# Boost Transaction weight if it's a high-value or new-beneficiary action
current_weights = self.weights.copy()
if input_data.get("amount", 0) > 5000 or input_data.get("is_new_beneficiary"):
    if "TransactionRiskProvider" in current_weights:
        current_weights["TransactionRiskProvider"] *= 1.5

# Re-normalize adjusted weights
w_sum = sum(current_weights.values())
if w_sum > 0:
    current_weights = {k: v / w_sum for k, v in current_weights.items()}
```

### Stateful Correlation (Attack Chain Multipliers)
The final score is subject to sequence-based multipliers (SACM - Stateful Attack Context Manager):
- **LURE → HOOK/EXPLOIT Transition:** `score = min(1.0, score * 1.3)`
- **(LURE or HOOK) → MONETIZE Transition:** `score = min(1.0, score * 1.5)`
- **EXPLOIT → MONETIZE Transition:** `score = min(1.0, score * 1.5)`

## 3. Escalation Levels
The platform defines four active escalation levels (1-4) based on the final fused score in `_make_decision`:

| Level | Range | Decision | Action/Recommendation |
|---|---|---|---|
| **1** | Score < 0.2 | **ALLOW** | Continue monitoring. Low risk. |
| **2** | 0.2 ≤ Score < 0.4 | **CHALLENGE** | Request Step-up Authentication (OTP/MFA). |
| **3** | 0.4 ≤ Score < 0.7 | **RESTRICT** | Block high-value transfers, freeze sensitive actions. |
| **4** | Score ≥ 0.7 | **CONTAIN** | Terminate session, lock account, escalate to security team. |

*(Note: Level 5 is currently reserved for manual forensic lock-down in future architecture docs but is not yet implemented in the serving path.)*

## 4. Traceability Example
**Scenario:** High behavioral risk (e.g., Keystroke ML anomaly) with low transaction risk.

**Inputs:**
- `AccountTakeoverProvider` (Behavioral): **0.80**
- `TransactionRiskProvider` (Transaction): **0.10**
- All other providers: **0.00**

**Default Weights (Normalized for 6 providers):**
- `TransactionRiskProvider`: 0.3810
- `SocialEngineeringRiskProvider`: 0.1905
- `PhishingRiskProvider`: 0.1429
- `AccountTakeoverProvider`: 0.1429
- `DeviceTrustProvider`: 0.0952
- `NetworkRiskProvider`: 0.0476

**Calculation:**
$$FinalScore = (0.10 \cdot 0.3810) + (0.80 \cdot 0.1429) + (0 \cdot \dots)$$
$$FinalScore = 0.0381 + 0.1143 = 0.1524$$

**Outcome:**
- **Overall Risk:** 0.1524
- **Escalation Level:** 1
- **Decision:** ALLOW
- **Reason:** Behavioral risk is high, but its weighted impact (14.29%) is insufficient to trigger a challenge without corroborating evidence from higher-weighted providers like Transaction or Device Trust.

---
**Audit Verification:** Literal path `src/engine/risk_engine.py` confirmed. Weighted fusion and SACM logic verified in lines 46-130.
