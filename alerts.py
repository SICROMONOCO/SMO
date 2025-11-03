"""
alerts.py — threshold-based alert system for SMO agent
"""

import logging
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
        .get("virtual_memory", {})
        .get("percent", {})
        .get("value")
    )
    logging.debug(f"[dim]Memory value: {mem_val}, Threshold: {thresholds.get('memory_percent')}[/]")
    if mem_val is not None and "memory_percent" in thresholds:
        if check_threshold(mem_val, thresholds["memory_percent"], "above"):
            alert = {
                "metric": "memory_percent",  # Match the config key
                "value": mem_val,
                "threshold": thresholds["memory_percent"],
                "level": "warning",
                "time": ts,
                "message": f"Memory usage {mem_val}% > {thresholds['memory_percent']}%"
            }
            alerts.append(alert)
            logging.debug(f"[dim]Added memory alert: {alert}[/]")

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

    def _attach_alert(alert: dict):
        """Attach a minimal alert dict to the specific metric in snapshot.

        We avoid replacing the snapshot or dumping large structures. Instead we
        inject a small `alert` field on the specific metric dict so the metric
        remains the owner of its alert information.
        """
        metric = alert.get("metric", "")
        # Default minimal payload
        minimal = {
            "level": alert.get("level"),
            "time": alert.get("time"),
            "message": alert.get("message"),
            "value": alert.get("value"),
            "threshold": alert.get("threshold"),
        }

        try:
            if metric == "cpu_percent":
                target = snapshot.setdefault("cpu", {}).setdefault("average", {}).setdefault("cpu_percent", {})
                target.setdefault("alert", minimal)
            # Memory alerts
            elif metric == "memory_percent":
                target = snapshot.setdefault("memory", {}).setdefault("virtual_memory", {}).setdefault("percent", {})
                target["alert"] = minimal  # Use direct assignment instead of setdefault
            elif metric.startswith("disk_usage"):
                # format is disk_usage:<device>
                parts = metric.split(":", 1)
                if len(parts) == 2:
                    dev = parts[1]
                    target = snapshot.setdefault("disk", {}).setdefault(dev, {}).setdefault("metrics", {}).setdefault("usage_percent", {})
                    target.setdefault("alert", minimal)
            elif metric == "network_bytes_sent":
                target = snapshot.setdefault("network", {}).setdefault("io_counters", {}).setdefault("metrics", {}).setdefault("bytes_sent", {})
                target.setdefault("alert", minimal)
            else:
                # Fallback: attach at top-level `alerts_fallback` list so we don't lose info
                al = snapshot.setdefault("alerts_fallback", [])
                al.append(minimal)
        except Exception:
            # Do not allow attach failures to propagate
            logging.exception(f"[yellow]⚠[/] Failed to attach alert to snapshot for [cyan]{metric}[/]")

    # Log to console and attach minimal info to the specific metrics only
    if alerts:
        for alert in alerts:
            level = alert.get("level", "warning").lower()
            metric_name = alert.get("metric", "unknown")
            message = alert.get("message", "")

            # Format messages with rich markup
            if level == "info":
                logging.info(f"[blue]ℹ[/] [cyan]{metric_name}[/]: {message}")
            elif level == "error":
                logging.error(f"[red]✗[/] [cyan]{metric_name}[/]: {message}")
            else:
                logging.warning(f"[yellow]⚠[/] [cyan]{metric_name}[/]: {message}")

            _attach_alert(alert)

    return alerts
# ...existing code...
