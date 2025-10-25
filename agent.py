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
import yaml
from logger import logger
from updater import start_all
from metrics import registry
import psutil
import rich
import pathlib

# ---------------------------------------------------------------------------
# Configuration Loader
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent  # SMO directory is the root
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

DEFAULT_CONFIG = {
    "refresh": {"cpu": 2, "memory": 5, "disk": 10, "network": 5, "process": 2},
    "logging": {"format": "json"},
    "agent": {"snapshot_interval": 2},
    "display": {"show_snapshot_info": True},
    "alerts": {"cpu_percent": 90, "memory_percent": 90, "disk_usage": 90, "network_bytes_sent": 1000000}
}


def _deep_merge_dicts(base: dict, override: dict) -> dict:
    """Recursively merge two dictionaries."""
    result = base.copy()
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge_dicts(result[k], v)
        else:
            result[k] = v
    return result


def load_config() -> dict:
    print("🔍 CONFIG PATH:", CONFIG_PATH)
    """Load YAML config with deep merge fallback."""
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(DEFAULT_CONFIG, f)
        print(f"[CONFIG] Created default config at {CONFIG_PATH}")
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_PATH, "r") as f:
            data = yaml.safe_load(f) or {}
        merged = _deep_merge_dicts(DEFAULT_CONFIG, data)
        return merged
    except Exception as e:
        print(f"[CONFIG] Failed to load config: {e}")
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

from datetime import datetime
from rich import print as rprint

def _print_snapshot_info(snapshot: dict, active_alerts=None):
    ts = snapshot.get("timestamp", time.time())
    dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    
    # System metrics
    cpu_avg = snapshot.get("cpu", {}).get("average", {}).get("cpu_percent", {}).get("value")
    mem_pct = snapshot.get("memory", {}).get("virtual_memory", {}).get("percent", {}).get("value")
    
    # Agent process metrics
    process_data = snapshot.get("process", {})
    agent_cpu = process_data.get("cpu", {}).get("value")
    agent_mem = process_data.get("memory", {}).get("percent", {}).get("value")
    agent_threads = process_data.get("threads", {}).get("count", {}).get("value")
    agent_uptime = process_data.get("uptime", {}).get("value")
    
    # For debugging
    if not process_data:
        logging.warning("No process metrics available in snapshot")
    elif "error" in process_data:
        logging.warning(f"Process metrics error: {process_data['error']}")

    # Format uptime nicely
    uptime_str = ""
    if agent_uptime is not None:
        minutes, seconds = divmod(int(agent_uptime), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            uptime_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            uptime_str = f"{minutes}m {seconds}s"
        else:
            uptime_str = f"{seconds}s"

    # Build the display string
    info = f"🕒 [bold cyan]{dt}[/] | "
    
    # System metrics
    if cpu_avg is not None:
        info += f"Sys CPU: [bold yellow]{cpu_avg}%[/] "
    if mem_pct is not None:
        info += f"| Sys Mem: [bold green]{mem_pct}%[/]"
    
    info += "\n🔍 Agent: "
    # Agent metrics
    if agent_cpu is not None:
        info += f"CPU: [bold magenta]{agent_cpu:.1f}%[/] "
    if agent_mem is not None:
        info += f"| Mem: [bold blue]{agent_mem:.1f}%[/] "
    if agent_threads is not None:
        info += f"| Threads: [bold cyan]{agent_threads}[/] "
    if uptime_str:
        info += f"| Uptime: [bold green]{uptime_str}[/]"

    rprint(info)

def run_agent(config: dict, print_console: bool = False):
    stop_event = threading.Event()
    setup_signal_handler(stop_event)

    refresh_intervals = config.get("refresh", {})
    snapshot_interval = config.get("agent", {}).get("snapshot_interval", 2)

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    logging.info("🚀 Starting SMO Agent...")
    start_all(intervals=refresh_intervals, stop_event=stop_event)

    try:
        from alerts import process_alerts  # Import alerts module

        while not stop_event.is_set():
            # Gather a full snapshot from the registry
            snapshot = registry.gather_all()

            # Process alerts and attach to snapshot if any
            active_alerts = process_alerts(snapshot, config)  # Don't pass logger to avoid duplicate logging
            if active_alerts:
                snapshot["alerts"] = active_alerts
                # Print alerts in a more formatted way
                rprint("\n[bold red]═══════════════ ACTIVE ALERTS ═══════════════[/]")
                for alert in active_alerts:
                    level_color = "yellow" if alert["level"] == "warning" else "red" if alert["level"] == "error" else "blue"
                    rprint(f"[bold {level_color}]⚠️  {alert['metric']}:[/] {alert['message']}")
                rprint("[bold red]═══════════════════════════════════════[/]\n")

            # Persist the complete snapshot with alerts
            logger.log(snapshot)

            # Console display (formatted like _print_snapshot_info)
            if config.get("display", {}).get("show_snapshot_info", True):
                _print_snapshot_info(snapshot)

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
    parser.add_argument("--print", dest="print", action="store_true", help="print snapshots to console in run mode")
    args = parser.parse_args()

    config = load_config()

    if args.command == "run":
        run_agent(config, print_console=args.print)
    elif args.command == "once":
        from rich import print as rprint
        snapshot = registry.gather_all()
        rprint(snapshot)
        logger.log(snapshot)
        print("✅ Snapshot saved to logs/.")


if __name__ == "__main__":
    main()
