"""Quick test runner to gather a snapshot and run alerts.process_alerts.

Run this from the project root to check whether alerts trigger with the
current `config/config.yaml`.
"""
import json
from agent import load_config
from metrics import registry
import alerts
from logger import logger as metrics_logger

if __name__ == "__main__":
    config = load_config()
    snapshot = registry.gather_all()
    print("Snapshot keys:", list(snapshot.keys()))
    alerts_out = alerts.process_alerts(snapshot, config, logger=metrics_logger)
    print(json.dumps(alerts_out, indent=2))
