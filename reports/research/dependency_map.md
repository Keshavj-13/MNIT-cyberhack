# Component Dependency Map: Stateful Threat Memory Layer

The introduction of the `SessionEvent` abstraction and stateful memory affects the following platform components:

## 1. Database (`src/db/models.py`)
- **Impact**: HIGH.
- **Changes**: 
    - Update `SecurityEvent` to include `session_id` and `user_id`.
    - Add `event_category` (LURE, HOOK, EXPLOIT, etc.) to the schema.
    - Add indices on `session_id` and `timestamp` for fast history retrieval.

## 2. Risk Engine (`src/engine/risk_engine.py`)
- **Impact**: HIGH.
- **Changes**:
    - Modify `evaluate_all` to accept `history: List[SessionEvent]`.
    - Implement `CorrelationEngine` logic to detect state transitions (e.g., LURE followed by TRANSACTION).
    - Move from static weighting to **Context-Adjusted Weighting**.

## 3. Providers (`src/providers/`)
- **Impact**: MEDIUM.
- **Changes**:
    - Providers now return an `EventCategory` in their `RiskResult`.
    - `PhishingRiskProvider` and `SocialEngineeringRiskProvider` explicitly tag results as `HOOK` and `LURE` respectively.

## 4. API (`src/api/server.py`)
- **Impact**: MEDIUM.
- **Changes**:
    - Endpoints must now support `user_id` and optional `session_id` in request bodies.
    - Evaluation logic must fetch history from the DB before calling the engine.

## 5. Frontend (`ui/src/`)
- **Impact**: LOW/MEDIUM.
- **Changes**:
    - Dashboard must visualize the "Memory" or "Timeline" of why a current risk is high.
    - Playground needs a `user_id` field to demonstrate cross-event persistence.

---

# Sequence Diagram: Stateful Evaluation

1. **API** receives request with `user_id`.
2. **API** queries **DB** for previous `SecurityEvent` records for that `user_id`.
3. **API** maps DB records to `SessionEvent` objects.
4. **RiskEngine** receives `current_payload` + `List[SessionEvent]`.
5. **RiskEngine** computes base risk from Providers.
6. **RiskEngine** applies **Sequence Logic** (e.g., if any past event was a verified `LURE` within 30 mins).
7. **API** returns results and persists the new event.
