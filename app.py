import updater
from metrics import registry
import time
import rich
import threading
import signal
import sys
import logging
import psutil
from agent import load_config  # Import the config loader
from logger import logger as metrics_logger
from alerts import process_alerts

def main():
    print("🚀 SMO Agent starting ...")
    logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
    )   
    config = load_config()
    stop_event = threading.Event()
    refresh_intervals = config.get("refresh", {})
    updater.start_all(intervals=refresh_intervals, stop_event=stop_event)
    

    try:
        
        while not stop_event.is_set():
                # prefer a cached snapshot if registry exposes one to avoid re-querying psutil
                get_cached = getattr(registry, "get_cached", None)
                if callable(get_cached):
                    snapshot = get_cached()
                else:
                    # fallback to a stored attribute (set_latest()/set_last() style), or gather if not available
                    snapshot = getattr(registry, "last_snapshot", None) or getattr(registry, "latest", None) or registry.gather_all()
                
                # evaluate alerts using the metrics logger (it exposes write_alert)
                active_alerts = process_alerts(snapshot, config, logger=metrics_logger)

                # Add alerts to snapshot and create a formatted display
                if active_alerts:
                    snapshot["alerts"] = active_alerts
                    # Create a visually distinct section for alerts
                    rich.print("\n[bold red]═══════════════ 🚨 ACTIVE ALERTS 🚨 ═══════════════[/]")
                    for alert in active_alerts:
                        rich.print(f"[bold yellow]⚠️  {alert['metric']}:[/] [red]{alert['message']}[/]")
                    rich.print("[bold red]═══════════════════════════════════════════════[/]\n")

                # Display the main metrics with custom formatting
                rich.print("[bold blue]════════════════ SYSTEM METRICS ════════════════[/]")
                for section, data in snapshot.items():
                    if section != "alerts":  # Display alerts separately
                        rich.print(f"[bold cyan]{section.upper()}:[/]")
                        rich.print(data)
                    rich.print("")
                
                # persist snapshot to JSONL
                metrics_logger.log(snapshot)
                
                time.sleep(config["agent"]["snapshot_interval"])
        
    except KeyboardInterrupt:
        print("Shutting down...")
        stop_event.set()
        time.sleep(0.2)  # let threads exit
        sys.exit(0)

if __name__ == "__main__":
    main()
