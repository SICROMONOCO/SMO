"""
alerts.py — threshold-based alert system for SMO agent
"""

import time
import logging
import json
from datetime import datetime


def check_threshold(value, threshold, direction="above"):
    if value is None:
        return False
    if direction == "above":
        return value > threshold
    elif direction == "below":
        return value < threshold
    return False


def evaluate_alerts(snapshot: dict, config: dict) -> list:
    """Check snapshot metrics against config thresholds."""
    alerts = []
    thresholds = config.get("alerts", {})

    ts = datetime.now().isoformat(timespec="seconds")

    # CPU
    cpu_val = (
        snapshot.get("cpu", {})
        .get("average", {})
        .get("cpu_percent", {})
        .get("value")
    )
    # allow zero values; check for None explicitly
    if cpu_val is not None and "cpu_percent" in thresholds:
        if check_threshold(cpu_val, thresholds["cpu_percent"], "above"):
            alerts.append({
                "metric": "cpu_percent",
                "value": cpu_val,
                "threshold": thresholds["cpu_percent"],
                "level": "warning",
                "time": ts,
                "message": f"CPU usage {cpu_val}% > {thresholds['cpu_percent']}%"
            })

    # Memory
    mem_val = (
        snapshot.get("memory", {})
        .get("virtual", {})
        .get("percent", {})
        .get("value")
    )
    if mem_val is not None and "memory_percent" in thresholds:
        if check_threshold(mem_val, thresholds["memory_percent"], "above"):
            alerts.append({
                "metric": "memory_percent",
                "value": mem_val,
                "threshold": thresholds["memory_percent"],
                "level": "warning",
                "time": ts,
                "message": f"Memory usage {mem_val}% > {thresholds['memory_percent']}%"
            })

    # Disk usage
    for dev, part in snapshot.get("disk", {}).items():
        usage = (
            part.get("metrics", {})
            .get("usage_percent", {})
            .get("value")
        )
        if usage is not None and "disk_usage" in thresholds:
            if check_threshold(usage, thresholds["disk_usage"], "above"):
                alerts.append({
                    "metric": f"disk_usage:{dev}",
                    "value": usage,
                    "threshold": thresholds["disk_usage"],
                    "level": "warning",
                    "time": ts,
                    "message": f"Disk {dev} usage {usage}% > {thresholds['disk_usage']}%"
                })

    # Network I/O
    net_io = snapshot.get("network", {}).get("io_counters", {}).get("metrics", {})
    # net_io may be an empty dict; still try to read bytes_sent (default 0)
    if "network_bytes_sent" in thresholds and isinstance(net_io, dict):
        sent_val = net_io.get("bytes_sent", {}).get("value", 0)
        # sent_val may be 0; check explicitly
        if sent_val is not None and check_threshold(sent_val, thresholds["network_bytes_sent"], "above"):
            alerts.append({
                "metric": "network_bytes_sent",
                "value": sent_val,
                "threshold": thresholds["network_bytes_sent"],
                "level": "info",
                "time": ts,
                "message": f"High network TX: {sent_val} bytes > {thresholds['network_bytes_sent']}"
            })

    return alerts


def process_alerts(snapshot: dict, config: dict, logger=None):
    alerts = evaluate_alerts(snapshot, config)
    
    # If there are alerts, add them to the metrics structure
    if alerts:
        for alert in alerts:
            msg = f"[{alert['level'].upper()}] {alert['message']}"
            # log at the appropriate level for console output
            level = alert.get("level", "warning").lower()
            if level == "info":
                logging.info(msg)
            elif level == "error":
                logging.error(msg)
            else:
                logging.warning(msg)
                
        # Add alerts to the snapshot instead of logging separately
        snapshot["alerts"] = alerts
    return alerts

    

