# Design Review: Stateful Threat Memory Layer

## 1. Current Architecture (Stateless)
- **API**: `/evaluate` -> `RiskEngine.evaluate_all(input_data)` -> `Result`.
- **Memory**: None. Every call is a "blank slate."
- **Data Flow**: `Payload` -> `Providers` (parallel) -> `Weights` -> `Decision`.

## 2. Proposed Architecture (Stateful)
- **API**: `/evaluate` -> `SessionStore.get_history(user_id)` -> `RiskEngine.evaluate_all(input_data, history)`.
- **Memory**: `SessionStore` (backed by `security_events` table).
- **Data Flow**: 
    1.  `Payload` arrives.
    2.  `System` retrieves last 5 events for that `user_id`.
    3.  `RiskEngine` calculates a **Coercion Bonus** if current event follows a high-risk lure.
    4.  `Providers` can optionally check history (e.g., `DeviceTrust` looks for IP shifts over time).
    5.  `Payload` + `Result` is saved to `SessionStore`.

## 3. Sequence Diagram (Conceptual)
1. **Client** -> `POST /evaluate {user_id: "G-123", amount: 100}`
2. **Backend** -> `DB.query("SELECT * FROM security_events WHERE user_id='G-123'")`
3. **Engine** -> `evaluate_all(current_data, past_events)`
4. **Logic**: 
    - `IF past_events contains SMISHING_LURE (risk > 0.8)`
    - `AND current_data contains TRANSACTION`
    - `THEN score = score + 0.3 (Coercion Multiplier)`
5. **Backend** -> `Client {decision: BLOCK, reason: "Memory of previous scam SMS"}`

## 4. Failure Modes & Rollback
- **Failure**: DB lookup latency slows down API.
- **Mitigation**: Index `user_id` and `timestamp`. Limit history to last 10 events.
- **Rollback**: Set `config.stateful_mode = false` to skip history lookup.

## 5. Expected Demo Impact
- **Scenario**: 
    - Send SMS: "URGENT: Blocked" -> System: MONITOR.
    - Transaction: "$100" -> System: **RESTRICT** (instead of ALLOW). 
    - Reason shown: "Correlated with suspicious SMS from 2 minutes ago."

## 6. Metric Impact
- **Recall**: Expected to increase for multi-stage fraud.
- **False Positives**: May increase slightly; handled via high decay rates.
- **Latency**: Estimated +5ms to +15ms (DB overhead).

## 7. Approval Request
I am ready to implement the `SessionStore` logic and refactor the `RiskEngine` to support historical context.
