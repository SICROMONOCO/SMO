"""
agent/agent.py
---------------
Main runtime controller and CLI for the SMO (System Monitoring Observer) agent.

Features:
  - Loads configuration from config/config.yaml (or defaults)
  - Starts threaded metrics updater (with per-metric refresh)
  - Periodically gathers snapshots from registry
  - Logs metrics to JSON and CSV files
  - Handles graceful shutdown via Ctrl+C
"""

import os
import sys
import time
import threading
import signal
import logging
import argparse
import importlib

def _load_yaml_module():
    try:
        return importlib.import_module("yaml")
    except Exception:
        # PyYAML not available — provide a minimal JSON-based shim so the
        # rest of the program can still run. Be explicit: YAML files with
        # non-JSON features (anchors, tags, comments) won't parse here.
        import json as _json
        import sys as _sys
        _sys.stderr.write(
            "[WARN] PyYAML not found; falling back to JSON-only config parsing.\n"
            "       Install PyYAML (`pip install pyyaml`) to use full YAML support.\n"
        )

        class _yaml:
            @staticmethod
            def safe_load(stream):
                if hasattr(stream, "read"):
                    content = stream.read()
                else:
                    content = stream
                if not content:
                    return {}
                try:
                    return _json.loads(content)
                except Exception as exc:
                    # Provide a helpful error so users understand why parsing failed
                    raise RuntimeError(
                        "Config parsing failed: file is not valid JSON and PyYAML is not installed. "
                        "Install PyYAML or convert the config to JSON."
                    ) from exc

            @staticmethod
            def safe_dump(data, stream=None):
                s = _json.dumps(data, indent=2)
                if stream is not None and hasattr(stream, "write"):
                    stream.write(s)
                    return
                return s

        return _yaml

yaml = _load_yaml_module()

import logger
from updater import start_all
from metrics import registry
import pathlib


# ---------------------------------------------------------------------------
# Configuration Loader (Fixed)
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "refresh": {"cpu": 2, "memory": 5, "disk": 10, "network": 5},
    "agent": {"snapshot_interval": 2},
}

# Resolve the root of the project dynamically
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent  # project root (this file sits in the repo root)
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

def load_config() -> dict:
    """Load YAML config or create a default one if missing."""
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(DEFAULT_CONFIG, f)
        print(f"[CONFIG] Created default config at {CONFIG_PATH}")
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_PATH, "r") as f:
            data = yaml.safe_load(f) or {}
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
        return merged
    except Exception as e:
        print(f"[CONFIG] Failed to load config from {CONFIG_PATH}: {e}")
        return DEFAULT_CONFIG



# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

def setup_signal_handler(stop_event: threading.Event):
    def handle_signal(sig, frame):
        print("\n⚠️  Received shutdown signal... stopping threads.")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


# ---------------------------------------------------------------------------
# Main Agent Loop
# ---------------------------------------------------------------------------

def run_agent(config: dict):
    stop_event = threading.Event()
    setup_signal_handler(stop_event)

    refresh_intervals = config["refresh"]
    snapshot_interval = config["agent"]["snapshot_interval"]

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    logging.info("🚀 Starting SMO Agent...")
    start_all(intervals=refresh_intervals, stop_event=stop_event)

    try:
        while not stop_event.is_set():
            snapshot = registry.gather_all()
            logger.log_snapshot(snapshot)
            time.sleep(snapshot_interval)
    except Exception:
        logging.exception("Agent loop crashed unexpectedly.")
    finally:
        logging.info("🧩 SMO Agent stopped cleanly.")


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(prog="smo", description="System Monitoring Observer (SMO) Agent")
    parser.add_argument("command", choices=["run", "once"], help="run = continuous mode, once = single snapshot")
    args = parser.parse_args()

    config = load_config()

    if args.command == "run":
        run_agent(config)
    elif args.command == "once":
        from rich import print as rprint
        snapshot = registry.gather_all()
        rprint(snapshot)
        logger.log_snapshot(snapshot)
        print("✅ Snapshot saved to logs/.")


if __name__ == "__main__":
    
    main()
