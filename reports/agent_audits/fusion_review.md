# Risk Fusion Engine Audit Report
**Agent:** FUSION_REVIEW_AGENT
**Status:** CRITICAL REVIEW COMPLETED
**Timestamp:** 2026-06-14 15:15:00

## 1. Executive Summary
The Risk Fusion Engine (`src/engine/risk_engine.py`) employs a "Weighted Linear Combination" (WLC) model which, while easy to implement, suffers from severe **Risk Dilution**. High-severity, high-confidence signals from specialized providers are systematically suppressed by the presence of low-scoring peers, leading to false negatives in critical compromise scenarios.

## 2. Logic Flaws in Weighted Aggregation

### 2.1. The "Dilution" Vulnerability
The current normalization logic (`_normalize_weights`) forces the sum of all provider weights to 1.0. 
- **Effect:** A 1.0 (CRITICAL) score from `DeviceTrustProvider` (weight ~0.1) only contributes **0.1** to the final score.
- **Consequence:** If no other provider flags the event, a confirmed rooted/compromised device results in an **ALLOW** decision (threshold < 0.2), which is a catastrophic security failure.
- **Flaw:** The engine treats risk as an average rather than a "weakest link" or "max signal" problem.

### 2.2. Negative Scaling via Registration
The engine assigns a default weight of **0.05** to any unknown provider.
- **Effect:** Registering new sensors (even if they are silent) reduces the relative importance of existing core sensors (Transaction, Phishing).
- **Flaw:** Accuracy degrades as the platform "scales" with more providers.

### 2.3. Contextual Boosting Rigidity
The `TransactionRiskProvider` boost is hardcoded at **1.5x**.
- **Inflexibility:** It applies the same boost to a $5,001 transfer as a $1,000,000 transfer.
- **Normalization Side-Effect:** Boosting one provider automatically scales down the weights of all others due to re-normalization, potentially muting critical "HOOK" signals (Phishing) during the very moment they are most needed (High-Value Transfer).

## 3. Hardcoded Scores & "Pseudo-Precision"

### 3.1. Magic Numbers in SACM (Stateful Attack Context Manager)
The correlation logic (`_apply_correlation`) uses arbitrary multipliers:
- `score * 1.3` for LURE -> HOOK/EXPLOIT.
- `score * 1.5` for MONETIZE transitions.
These are **static constants** with no probabilistic basis. They act as "finger on the scale" adjustments that are hard to tune or justify under audit.

### 3.2. Disguised Hardcoding
- **Precision Illusion:** Rounding `overall_risk` and `confidence` to **4 decimal places** suggests a level of mathematical rigor that the underlying "magic number" multipliers do not support.
- **Fixed Thresholds:** The decision logic (`_make_decision`) uses hardcoded boundaries (0.2, 0.4, 0.7). These are not retrieved from configuration and cannot be adjusted per user-segment or tenant without code modification.
- **Categorization Bias:** In `server.py`, the `dominant_cat` logic ignores any signal below **0.5**. This results in events being labeled "NEUTRAL" even when multiple providers show moderate suspicion (e.g., 0.45), effectively blinding the stateful correlation logic for subsequent events.

## 4. Confidence Logic Flaws
The `weighted_conf` calculation follows the same dilution pattern as risk.
- **Problem:** If a low-weight provider has 100% confidence in a CRITICAL risk, but the high-weight Transaction provider is "Uncertain" (0.2 confidence) because the data is sparse, the overall confidence is dragged down significantly.
- **Result:** The engine "doubts" a certain compromise because a secondary, unrelated sensor is unsure.

## 5. Recommended Remediation
1.  **Implement Non-Linear Fusion:** Replace simple WLC with a `max(weighted_sum, highest_severity_signal)` approach for critical providers.
2.  **Move Magic Numbers to Config:** All multipliers (1.3, 1.5) and thresholds (0.7, 0.5) must be moved to `risk_weights.yaml`.
3.  **Adaptive Thresholding:** Decision levels should be based on standard deviations or percentiles rather than hardcoded 0.2/0.4/0.7 constants.
4.  **Fix Category Capture:** `server.py` should record the `max()` category for *any* risk > 0.1, not just those > 0.5, to ensure the Attack Chain memory isn't "leaky."
