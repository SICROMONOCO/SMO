"""
agent/updater.py
----------------
Enhanced updater that respects per-metric refresh intervals
and avoids re-fetching static metrics unnecessarily.
"""

import threading
import time
import traceback
from metrics import registry
import logging

DEFAULT_INTERVALS = {
    "cpu": 2,
    "memory": 5,
    "disk": 10,
    "network": 5,
}

_registry_lock = threading.Lock()


def _metric_needs_update(last_time: float, interval: int) -> bool:
    """Check if enough time has passed to update."""
    return (time.time() - last_time) >= interval


def _update_loop(name: str, interval: int, stop_event: threading.Event | None = None):
    """Continuously refresh metrics for a specific module."""
    func = registry.get_provider(name)
    if not func:
        logging.warning("No provider found for %s", name)
        return

    cache = registry.get_latest(name) or {}
    last_update = 0.0

    while not (stop_event and stop_event.is_set()):
        try:
            # If no dynamic metrics need refresh, skip this cycle
            if not _metric_needs_update(last_update, interval):
                time.sleep(0.5)
                continue

            new_data = func()

            # Merge intelligently — keep static metrics from cache
            merged = _merge_metrics(cache, new_data)
            with _registry_lock:
                registry.set_latest(name, merged)
            cache = merged
            last_update = time.time()

            time.sleep(interval)
        except Exception:
            logging.exception("Updating %s failed", name)
            time.sleep(interval * 2)


def _merge_metrics(old: dict, new: dict) -> dict:
    """Merge old and new metric dicts, preserving static metrics."""
    merged = dict(old)
    for key, val in new.items():
        if isinstance(val, dict):
            if key not in merged:
                merged[key] = val
            else:
                merged[key] = _merge_metrics(merged[key], val)
        else:
            merged[key] = val

        # Replace dynamic values only
        if isinstance(val, dict) and val.get("type") == "dynamic":
            merged[key] = val
    return merged


def start_all(intervals: dict[str, int] | None = None, stop_event: threading.Event | None = None):
    """Start updater threads for all registered providers."""
    if intervals is None:
        intervals = DEFAULT_INTERVALS

    logging.info("Starting SMO updater threads...")
    for name in list(registry.get_providers()):
        interval = intervals.get(name, 5)
        t = threading.Thread(
            target=_update_loop,
            args=(name, interval, stop_event),
            daemon=True,
            name=f"Updater-{name}"
        )
        t.start()
        logging.info("  ➜ %s updater running every %ss", name, interval)
    logging.info("All updater threads started.")
