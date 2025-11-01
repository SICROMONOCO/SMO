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
import subprocess
import platform
from logger import logger
from updater import start_all
from metrics import registry
import psutil
import rich
import pathlib
from rich.logging import RichHandler
from rich import print as rprint
from rich.console import Console
from rich.pretty import Pretty

# Central console for controlled, pretty printing
console = Console(highlight=True, markup=True)

# ---------------------------------------------------------------------------
# Configuration Loader
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent  # SMO directory is the root
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

DEFAULT_CONFIG = {
    "refresh": {"cpu": 2, "memory": 5, "disk": 10, "network": 5, "process": 2},
    "logging": {"format": "json"},
    "agent": {"snapshot_interval": 2},
    "display": {"show_snapshot_info": True, "pretty_max_depth": 2, "pretty_max_length": 1200},
    "alerts": {
        "cpu_percent": 80,         # Alert when CPU usage > 80%
        "memory_percent": 85,      # Alert when memory usage > 85%
        "disk_usage": 90,          # Alert when disk usage > 90%
        "network_bytes_sent": 1000000  # Alert when network traffic > 1MB/s
    }
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
    """Load YAML config with deep merge fallback."""
    rprint(f"[dim]🔍 Config path:[/] [cyan]{CONFIG_PATH}[/]")
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(DEFAULT_CONFIG, f)
        rprint(f"[green]✓[/] Created default config at [cyan]{CONFIG_PATH}[/]")
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_PATH, "r") as f:
            data = yaml.safe_load(f) or {}
        merged = _deep_merge_dicts(DEFAULT_CONFIG, data)
        rprint(f"[green]✓[/] Loaded config from [cyan]{CONFIG_PATH}[/]")
        return merged
    except Exception as e:
        rprint(f"[red]✗[/] Failed to load config: [yellow]{e}[/]")
        rprint(f"[yellow]⚠[/] Using default configuration")
        return DEFAULT_CONFIG



# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

def setup_signal_handler(stop_event: threading.Event):
    def handle_signal(sig, frame):
        rprint("\n[yellow]⚠[/] [bold yellow]Received shutdown signal... stopping threads.[/]")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


# ---------------------------------------------------------------------------
# Main Agent Loop
# ---------------------------------------------------------------------------

from datetime import datetime

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
        logging.warning("[yellow]⚠[/] No process metrics available in snapshot")
    elif "error" in process_data:
        logging.warning(f"[yellow]⚠[/] Process metrics error: {process_data['error']}")

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

    # Configure logging with Rich handler for unified formatting
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(
            rich_tracebacks=True,
            show_path=False,
            show_time=True,
            markup=True
        )]
    )

    rprint("[bold green]🚀 Starting SMO Agent...[/]")
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

            # Persist the complete snapshot with alerts
            logger.log(snapshot)

            # Console display (formatted like _print_snapshot_info)
            if config.get("display", {}).get("show_snapshot_info", True):
                _print_snapshot_info(snapshot)

            # If user asked for a printed snapshot in the console, print a truncated
            # pretty representation so the terminal doesn't get flooded.
            if print_console:
                depth = config.get("display", {}).get("pretty_max_depth", 2)
                max_len = config.get("display", {}).get("pretty_max_length", 1200)
                console.print(Pretty(snapshot, max_depth=depth, max_string=max_len))

            time.sleep(snapshot_interval)
    except Exception:
        logging.exception("[red]✗[/] Agent loop crashed unexpectedly.")
    finally:
        rprint("[bold blue]🧩[/] [blue]SMO Agent stopped cleanly.[/]")
    



# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def open_log_file():
    """Open the log file with the system's default editor or a pager."""
    log_file = PROJECT_ROOT / "logs" / "smo_metrics.jsonl"
    
    if not log_file.exists():
        rprint(f"[red]✗[/] Log file not found: [cyan]{log_file}[/]")
        rprint("[yellow]⚠[/] Run 'smo run' first to generate logs.")
        return 1
    
    rprint(f"[cyan]📂[/] Opening log file: [bold]{log_file}[/]")
    
    # Try to open with a reasonable editor/viewer
    system = platform.system().lower()
    
    if system == "linux":
        # Prefer pagers/readers for log files, then editors
        # Try less first (best for log files), then other options
        viewers = ["less", "more", "cat"]
        editors = ["xdg-open", "gedit", "nano", "vim"]
        
        # Try viewers first (non-interactive check by using which)
        for viewer in viewers:
            try:
                result = subprocess.run(["which", viewer], capture_output=True, check=False)
                if result.returncode == 0:
                    rprint(f"[dim]Using {viewer} to view logs...[/]")
                    subprocess.run([viewer, str(log_file)], check=False)
                    return 0
            except FileNotFoundError:
                continue
        
        # Try editors as fallback
        for editor in editors:
            try:
                result = subprocess.run(["which", editor], capture_output=True, check=False)
                if result.returncode == 0:
                    rprint(f"[dim]Using {editor} to open logs...[/]")
                    subprocess.run([editor, str(log_file)], check=False)
                    return 0
            except FileNotFoundError:
                continue
        
        # Fallback: just show file location and content preview
        rprint(f"[yellow]⚠[/] Could not find a suitable viewer. File location: [cyan]{log_file}[/]")
        rprint(f"[dim]File size: {log_file.stat().st_size} bytes[/]")
        rprint("[dim]You can open it manually with: less, nano, vim, or gedit[/]")
        # Show last few lines as preview
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    rprint("\n[dim]Last 3 log entries (preview):[/]")
                    for line in lines[-3:]:
                        rprint(f"[dim]{line.strip()[:100]}...[/]")
        except Exception:
            pass
        return 1
    elif system == "darwin":  # macOS
        subprocess.run(["open", str(log_file)], check=False)
        return 0
    elif system == "windows":
        subprocess.run(["start", str(log_file)], shell=True, check=False)
        return 0
    else:
        rprint(f"[yellow]⚠[/] Unsupported platform. Log file location: [cyan]{log_file}[/]")
        return 1


def run_tui():
    """Launch the TUI dashboard."""
    rprint("[bold cyan]🖥️[/] [cyan]Launching TUI Dashboard...[/]")
    try:
        # Import and run the TUI
        from tui.tui_dashboard import TUIDashboardApp
        app = TUIDashboardApp()
        app.run()
    except ImportError as e:
        rprint(f"[red]✗[/] Failed to import TUI: [yellow]{e}[/]")
        rprint("[yellow]⚠[/] Make sure all dependencies are installed.")
        return 1
    except KeyboardInterrupt:
        rprint("\n[yellow]⚠[/] TUI interrupted by user.")
        return 0
    except Exception as e:
        rprint(f"[red]✗[/] Failed to run TUI: [yellow]{e}[/]")
        logging.exception("TUI error")
        return 1


def main():
    parser = argparse.ArgumentParser(prog="smo", description="System Monitoring Observer (SMO) Agent")
    parser.add_argument("command", choices=["run", "once", "logs", "tui"], 
                       help="run = continuous mode, once = single snapshot, logs = view log file, tui = launch TUI dashboard")
    parser.add_argument("--print", dest="print", action="store_true", help="print snapshots to console in run mode")
    args = parser.parse_args()

    config = load_config()

    if args.command == "run":
        run_agent(config, print_console=args.print)
    elif args.command == "once":
        rprint("[bold cyan]📸[/] Gathering snapshot...")
        snapshot = registry.gather_all()
        # Print a truncated pretty snapshot (don't dump raw huge dicts)
        depth = config.get("display", {}).get("pretty_max_depth", 2)
        max_len = config.get("display", {}).get("pretty_max_length", 1200)
        console.print(Pretty(snapshot, max_depth=depth, max_string=max_len))
        logger.log(snapshot)
        rprint("[green]✓[/] Snapshot saved to logs/.")
    elif args.command == "logs":
        sys.exit(open_log_file())
    elif args.command == "tui":
        sys.exit(run_tui())


if __name__ == "__main__":
    main()
