import unittest
import numpy as np
from src.engine.features import FeatureExtractor

class TestFeatureExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = FeatureExtractor()

    def test_extract_features_empty(self):
        features = self.extractor.extract_features([])
        self.assertEqual(features["mean_dwell_time"], 0.0)
        self.assertEqual(features["mean_flight_time"], 0.0)
        self.assertEqual(features["interaction_density"], 0.0)

    def test_behavioral_features(self):
        events = [
            {"type": "keystroke", "timestamp": 1000, "data": {"event": "dwell", "dwellTime": 100, "key": "a"}},
            {"type": "keystroke", "timestamp": 1100, "data": {"event": "flight", "flightTime": 50, "key": "b"}},
            {"type": "keystroke", "timestamp": 1200, "data": {"event": "dwell", "dwellTime": 150, "key": "b"}},
            {"type": "keystroke", "timestamp": 1300, "data": {"event": "flight", "flightTime": 70, "key": "Backspace"}},
            {"type": "keystroke", "timestamp": 1400, "data": {"event": "dwell", "dwellTime": 120, "key": "Backspace"}},
        ]
        features = self.extractor.extract_features(events)
        
        self.assertAlmostEqual(features["mean_dwell_time"], (100 + 150 + 120) / 3)
        self.assertAlmostEqual(features["mean_flight_time"], (50 + 70) / 2)
        self.assertAlmostEqual(features["backspace_frequency"], 2 / 5)

    def test_mouse_features(self):
        events = [
            {"type": "mouse", "timestamp": 1000, "data": {"event": "move", "x": 0, "y": 0, "velocity": 1.0}},
            {"type": "mouse", "timestamp": 2000, "data": {"event": "move", "x": 10, "y": 10, "velocity": 2.0}},
            {"type": "mouse", "timestamp": 3000, "data": {"event": "move", "x": 20, "y": 20, "velocity": 1.5}},
            {"type": "mouse", "timestamp": 3500, "data": {"event": "click", "x": 20, "y": 20}},
        ]
        features = self.extractor.extract_features(events)
        
        self.assertAlmostEqual(features["avg_mouse_velocity"], (1.0 + 2.0 + 1.5) / 3)
        # Straight line: (0,0) to (20,20)
        # Total path: dist((0,0),(10,10)) + dist((10,10),(20,20)) = 14.1421356 + 14.1421356 = 28.2842712
        # Displacement: dist((0,0),(20,20)) = 28.2842712
        self.assertAlmostEqual(features["mouse_path_straightness"], 1.0)
        
        # Click density: 1 click in 2.5 seconds = 1 / (2.5 / 60) = 24 clicks/min
        self.assertAlmostEqual(features["mouse_click_density"], 24.0)

    def test_session_features(self):
        events = [
            {"type": "session", "timestamp": 10000, "data": {"event": "page_load", "url": "home"}},
            {"type": "keystroke", "timestamp": 15000, "data": {"event": "dwell", "dwellTime": 100, "key": "a"}},
            {"type": "session", "timestamp": 70000, "data": {"event": "tab_change", "tab": "dashboard"}},
        ]
        features = self.extractor.extract_features(events)
        
        # Duration: 60000ms = 1 min
        # Interactions: 3
        # Navigation events: 2
        self.assertAlmostEqual(features["interaction_density"], 3.0)
        self.assertAlmostEqual(features["navigation_speed"], 2.0)

if __name__ == '__main__':
    unittest.main()
