# Behavioral Feature Extraction Audit Report

**Date:** 2026-06-14
**Agent:** FEATURE_AGENT

## 1. Extraction Formulas

The following formulas are implemented in `src/engine/features.py`:

- **Dwell Time (`mean_dwell_time`):**
  $$\mu(\text{dwellTime}) \text{ where } \text{event\_type} = \text{'keystroke'} \text{ and } \text{event} = \text{'dwell'}$$
  Code: `dwell_times = [k['data'].get('dwellTime') for k in keystrokes if k['data'].get('event') == 'dwell']`

- **Flight Time (`mean_flight_time`):**
  $$\mu(\text{flightTime}) \text{ where } \text{event\_type} = \text{'keystroke'} \text{ and } \text{event} = \text{'flight'}$$
  Code: `flight_times = [k['data'].get('flightTime') for k in keystrokes if k['data'].get('event') == 'flight']`

- **Mouse Velocity (`avg_mouse_velocity`):**
  $$\mu(\text{velocity}) \text{ where } \text{event\_type} = \text{'mouse'} \text{ and } \text{event} = \text{'move'}$$
  Code: `velocities = [m['data'].get('velocity') for m in move_events if m['data'].get('velocity') is not None]`

- **Interaction Density (`interaction_density`):**
  $$\frac{\text{Count}(\text{all\_events})}{\text{Duration (minutes)}}$$
  Where $\text{Duration (minutes)} = \frac{\max(\text{timestamps}) - \min(\text{timestamps})}{60000.0}$
  Code: `interaction_density = len(all_events) / ((max(ts) - min(ts)) / 60000.0)`

## 2. Sample Mapping: Raw Event -> Feature Vector

### Raw Events (Input)
```json
[
    {"type": "keystroke", "timestamp": 1000, "data": {"event": "dwell", "dwellTime": 100, "key": "a"}},
    {"type": "keystroke", "timestamp": 1100, "data": {"event": "flight", "flightTime": 50, "key": "b"}},
    {"type": "mouse", "timestamp": 2000, "data": {"event": "move", "x": 10, "y": 10, "velocity": 2.0}},
    {"type": "session", "timestamp": 70000, "data": {"event": "page_load", "url": "home"}}
]
```

### Feature Vector (Output)
```json
{
    "mean_dwell_time": 100.0,
    "mean_flight_time": 50.0,
    "typing_cadence": 0.0,
    "backspace_frequency": 0.0,
    "avg_mouse_velocity": 2.0,
    "avg_mouse_acceleration": 0.0,
    "mouse_path_straightness": 0.0,
    "mouse_click_density": 0.0,
    "navigation_speed": 0.8695652173913043,
    "interaction_density": 3.4782608695652173
}
```
*(Note: navigation_speed calculated as 1 nav event / 1.15 min)*

## 3. Proof of Test Passing

Execution of `python -m tests.test_features`:

```
....
----------------------------------------------------------------------
Ran 4 tests in 0.001s

OK
```

## 4. Implementation Files

- **Logic:** `src/engine/features.py`
- **Tests:** `tests/test_features.py`
