import updater
from metrics import registry
import time
import rich
import threading
import signal
import sys
import logging

def main():
    print("🚀 SMO Agent starting ...")
    logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
    )   
    stop_event = threading.Event()
    updater.start_all(stop_event=stop_event)

    try:
        while True:
            # prefer a cached snapshot if registry exposes one to avoid re-querying psutil
            get_cached = getattr(registry, "get_cached", None)
            if callable(get_cached):
                snapshot = get_cached()
            else:
                # fallback to a stored attribute (set_latest()/set_last() style), or gather if not available
                snapshot = getattr(registry, "last_snapshot", None) or getattr(registry, "latest", None) or registry.gather_all()
            rich.print(snapshot)
            time.sleep(2)
    except KeyboardInterrupt:
        print("Shutting down...")
        stop_event.set()
        time.sleep(0.2)  # let threads exit
        sys.exit(0)

if __name__ == "__main__":
    main()
