# Feature Extraction Schema

The `FeatureExtractor` in `src/engine/features.py` converts raw telemetry events into a vectorized feature dictionary suitable for risk inference.

## Input Telemetry Format

The extractor expects a list of event dictionaries, where each event has:
- `type`: One of `keystroke`, `mouse`, `session`.
- `timestamp`: Epoch time in milliseconds.
- `data`: A dictionary containing event-specific data.

### Keystroke Data
- `event`: `dwell` (key pressed to released) or `flight` (key released to next key pressed).
- `key`: The key character (e.g., 'a', 'Backspace').
- `dwellTime`: Duration in ms (only for `dwell` events).
- `flightTime`: Duration in ms (only for `flight` events).

### Mouse Data
- `event`: `move` or `click`.
- `x`, `y`: Coordinates.
- `velocity`: Pixels per millisecond (for `move` events).

### Session Data
- `event`: `page_load`, `tab_change`, `visibility`, `idle`.

## Extracted Features

The output is a dictionary with the following vectorized features:

### Behavioral (Keystroke)
| Feature | Description |
|---------|-------------|
| `mean_dwell_time` | Average duration a key is held down. |
| `mean_flight_time` | Average duration between key presses. |
| `typing_cadence` | Standard deviation of flight times (consistency). |
| `backspace_frequency` | Ratio of Backspace keys to total keystrokes. |

### Mouse
| Feature | Description |
|---------|-------------|
| `avg_mouse_velocity` | Mean velocity of mouse movements (px/ms). |
| `avg_mouse_acceleration` | Mean rate of change of mouse velocity. |
| `mouse_path_straightness` | Ratio of displacement to total path length (1.0 = perfect line). |
| `mouse_click_density` | Number of clicks per minute of interaction. |

### Session
| Feature | Description |
|---------|-------------|
| `navigation_speed` | Number of navigation events (page loads/tab changes) per minute. |
| `interaction_density` | Total telemetry events per minute. |

## Usage

```python
from src.engine.features import FeatureExtractor

extractor = FeatureExtractor()
features = extractor.extract_features(raw_telemetry_events)
```
