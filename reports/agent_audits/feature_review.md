# Feature Extraction implementation Audit Report

**Date:** 2026-06-14
**Status:** CRITICAL ISSUES IDENTIFIED

## 1. Mathematical Errors & Logic Flaws

### 1.1. Backspace Frequency Inconsistency
**Issue:** The implementation calculates `backspace_frequency` as `backspace_count / total_keys`, where `total_keys` is the count of all keystroke *events* (including both 'dwell' and 'flight' types).
**Impact:** If one keystroke produces two events ('dwell' and 'flight') and another produces only one, the frequency is biased by the sensor's event emission rate rather than the user's actual behavior. 
**Example:** 
- User types "a", "b", "Backspace".
- If "a" has 1 event and "b"/"Backspace" have 2, `backspace_frequency` = 2/5 (0.4).
- If all have 1 event, `backspace_frequency` = 1/3 (0.33).
**Recommendation:** Calculate frequency based on unique timestamps or filter by a specific event type (e.g., only 'dwell' events).

### 1.2. Interaction Density Artifacts
**Issue:** `interaction_density = len(all_events) / ((max(ts) - min(ts)) / 60000.0)`.
**Impact:** For very short sessions (e.g., 2 events separated by 10ms), the density explodes to 12,000 interactions/minute. These extreme outliers will likely break linear models and require heavy normalization/clipping.
**Recommendation:** Implement a minimum duration floor (e.g., 1 second) or use a "heartbeat" based duration calculation.

### 1.3. Mouse Acceleration Scalar Approximation
**Issue:** `accelerations.append((v2 - v1) / dt)`.
**Impact:** This ignores the vector nature of acceleration. A user changing direction at constant speed has high acceleration, but this formula would report 0. Additionally, it is extremely sensitive to timestamp jitter in `dt`.
**Recommendation:** Use coordinate-based acceleration calculation: $a = \frac{\Delta v}{\Delta t}$ where $v$ is the velocity vector.

### 1.4. Semantic Misalignment: Typing Cadence
**Issue:** `typing_cadence` is implemented as `np.std(flight_times)`.
**Impact:** Standard deviation measures *rhythm consistency*, not *cadence* (which is a rate, e.g., keys per minute). This naming will confuse data scientists tuning the model.
**Recommendation:** Rename to `typing_rhythm_std` and add a true `typing_cadence` (keys per minute).

## 2. Production Readiness & Edge Cases

### 2.1. Single-Event Session Blindness
**Issue:** If a session has only one event, `max(ts) - min(ts)` is 0, and all rate-based features (`interaction_density`, `click_density`, `navigation_speed`) default to 0.0.
**Impact:** Short but high-intensity sessions are indistinguishable from idle sessions.
**Recommendation:** Handle $N=1$ cases by assuming a minimum session window or reporting "N/A" (or a specific sentinel value) instead of 0.0.

### 2.2. Mouse Velocity Data Dependency
**Issue:** `avg_mouse_velocity` relies on the sensor providing a `velocity` field. 
**Impact:** If the sensor only provides `x, y`, the implementation returns 0.0 for velocity but still tries to calculate `straightness`.
**Recommendation:** Implement a fallback to calculate velocity from `x, y, t` if the `velocity` field is missing.

## 3. Summary of Critical Risks
| Risk | Severity | Description |
| :--- | :--- | :--- |
| **Data Bias** | High | `backspace_frequency` is coupled to sensor sampling rate. |
| **Outliers** | High | `interaction_density` produces unphysically high values for short bursts. |
| **Feature Quality** | Medium | `mouse_acceleration` is mathematically incomplete (scalar vs vector). |
| **Edge Cases** | Low | Single-event sessions are not effectively characterized. |

## 4. Final Conclusion
The current implementation is **NOT production-ready**. While it handles empty lists safely, the core feature logic is susceptible to significant noise and mathematical artifacts that will degrade model performance. A refactor of the rate-based and behavioral frequency logic is required.
