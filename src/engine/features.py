import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime

class FeatureExtractor:
    """
    Converts raw telemetry events into a vectorized feature dictionary.
    """

    def extract_features(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not events:
            return self._empty_features()

        # Sort events by timestamp just in case
        events = sorted(events, key=lambda x: x.get('timestamp', 0))
        
        keystrokes = [e for e in events if e.get('type') == 'keystroke']
        mouse_events = [e for e in events if e.get('type') == 'mouse']
        session_events = [e for e in events if e.get('type') == 'session']

        features = {}
        features.update(self._extract_behavioral_features(keystrokes))
        features.update(self._extract_mouse_features(mouse_events))
        features.update(self._extract_session_features(session_events, events))

        # raw deltas fed to BeaconBehavioralProvider — aggregated scalars lose the rhythm VarCNN needs
        ts = sorted(e.get("timestamp", 0) for e in events if e.get("timestamp"))
        features["inter_event_timings"] = [ts[i+1] - ts[i] for i in range(len(ts) - 1)]

        return features

    def _empty_features(self) -> Dict[str, Any]:
        return {
            "mean_dwell_time": 0.0,
            "mean_flight_time": 0.0,
            "typing_cadence": 0.0,
            "backspace_frequency": 0.0,
            "avg_mouse_velocity": 0.0,
            "avg_mouse_acceleration": 0.0,
            "mouse_path_straightness": 0.0,
            "mouse_click_density": 0.0,
            "navigation_speed": 0.0,
            "interaction_density": 0.0
        }

    def _extract_behavioral_features(self, keystrokes: List[Dict[str, Any]]) -> Dict[str, Any]:
        dwell = [k['data'].get('dwellTime') for k in keystrokes if k['data'].get('event') == 'dwell' and k['data'].get('dwellTime') is not None]
        flight = [k['data'].get('flightTime') for k in keystrokes if k['data'].get('event') == 'flight' and k['data'].get('flightTime') is not None]
        bk = sum(1 for k in keystrokes if k['data'].get('key') == 'Backspace')
        # lat = up-down latency, approximated as dwell + flight; rhythm = CV of flight times
        lat = [d + f for d, f in zip(dwell, flight[:len(dwell)])] if dwell and flight else []
        fs, fm = (float(np.std(flight)), float(np.mean(flight))) if flight else (0.0, 0.0)
        return {
            "mean_dwell_time": float(np.mean(dwell)) if dwell else 0.0,
            "mean_flight_time": fm,
            "typing_cadence": fs,
            "backspace_frequency": float(bk / len(keystrokes)) if keystrokes else 0.0,
            # expanded features for ATO 10-feature model
            "dwell_mean": float(np.mean(dwell)) if dwell else 0.0,
            "dwell_std":  float(np.std(dwell))  if dwell else 0.0,
            "dwell_range": float(np.max(dwell) - np.min(dwell)) if dwell else 0.0,
            "flight_mean": fm, "flight_std": fs,
            "flight_range": float(np.max(flight) - np.min(flight)) if flight else 0.0,
            "lat_mean":  float(np.mean(lat))  if lat else 0.0,
            "lat_std":   float(np.std(lat))   if lat else 0.0,
            "lat_range": float(np.max(lat) - np.min(lat)) if lat else 0.0,
            "rhythm": fs / (fm + 1e-9),
        }

    def _extract_mouse_features(self, mouse_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        move_events = [m for m in mouse_events if m['data'].get('event') == 'move']
        click_events = [m for m in mouse_events if m['data'].get('event') == 'click']
        
        velocities = [m['data'].get('velocity') for m in move_events if m['data'].get('velocity') is not None]
        
        # Acceleration
        accelerations = []
        for i in range(1, len(move_events)):
            v1 = move_events[i-1]['data'].get('velocity', 0)
            v2 = move_events[i]['data'].get('velocity', 0)
            t1 = move_events[i-1].get('timestamp', 0)
            t2 = move_events[i].get('timestamp', 0)
            dt = t2 - t1
            if dt > 0:
                accelerations.append((v2 - v1) / dt)

        # Straightness: distance_between_endpoints / total_path_length
        straightness = 0.0
        if len(move_events) > 1:
            start = move_events[0]['data']
            end = move_events[-1]['data']
            displacement = np.sqrt((end['x'] - start['x'])**2 + (end['y'] - start['y'])**2)
            
            total_path = 0.0
            for i in range(1, len(move_events)):
                p1 = move_events[i-1]['data']
                p2 = move_events[i]['data']
                total_path += np.sqrt((p2['x'] - p1['x'])**2 + (p2['y'] - p1['y'])**2)
            
            if total_path > 0:
                straightness = displacement / total_path
        
        # Click Density: clicks per minute
        click_density = 0.0
        if mouse_events:
            ts = [m.get('timestamp', 0) for m in mouse_events]
            duration_min = (max(ts) - min(ts)) / 60000.0
            if duration_min > 0:
                click_density = len(click_events) / duration_min

        return {
            "avg_mouse_velocity": float(np.mean(velocities)) if velocities else 0.0,
            "avg_mouse_acceleration": float(np.mean(accelerations)) if accelerations else 0.0,
            "mouse_path_straightness": float(straightness),
            "mouse_click_density": float(click_density)
        }

    def _extract_session_features(self, session_events: List[Dict[str, Any]], all_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Navigation speed: tab changes or page loads per minute
        nav_events = [s for s in session_events if s['data'].get('event') in ('tab_change', 'page_load')]
        
        interaction_density = 0.0
        navigation_speed = 0.0
        
        if all_events:
            ts = [e.get('timestamp', 0) for e in all_events]
            duration_min = (max(ts) - min(ts)) / 60000.0
            if duration_min > 0:
                interaction_density = len(all_events) / duration_min
                navigation_speed = len(nav_events) / duration_min

        return {
            "navigation_speed": float(navigation_speed),
            "interaction_density": float(interaction_density)
        }
