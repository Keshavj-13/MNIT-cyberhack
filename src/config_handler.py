import yaml
import os

DEFAULT_CONFIG = {
    "ensemble_weights": {
        "transaction": 0.40,
        "network": 0.25,
        "device": 0.15,
        "context": 0.20
    },
    "decision_rules": {
        "allow_threshold": 0.30,
        "block_threshold": 0.70
    }
}

def load_config():
    config_path = "config/config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return DEFAULT_CONFIG

def save_config(config):
    os.makedirs("config", exist_ok=True)
    with open("config/config.yaml", "w") as f:
        yaml.dump(config, f)
