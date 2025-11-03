import os
import re
import psutil
from psutil._common import bytes2human
from typing import Any

# ───────────────────────────────────────────────
# 🔧 Helpers
# ───────────────────────────────────────────────

_SANITIZE_RE = re.compile(r"[^0-9A-Za-z_]+")


def sanitize_key(s: str) -> str:
    """Sanitize strings to safe dictionary keys (for mountpoints, devices, etc)."""
    return _SANITIZE_RE.sub("_", s).strip("_")


def build_metrics_from_namedtuple(
    source_name: str,
    ntuple: Any,
    refresh_interval: int = 10,
    description_prefix: str = "Disk I/O",
) -> dict[str, dict[str, Any]]:
    """
    Convert a namedtuple of I/O stats into a dict of metric descriptors.
    Works for psutil.disk_io_counters, network IO, etc.
    """
    metrics: dict[str, dict[str, Any]] = {}
    fields = getattr(ntuple, "_fields", None) or [
        f for f in dir(ntuple) if not f.startswith("_")
    ]

    for field in fields:
        try:
            val = getattr(ntuple, field)
        except Exception:
            continue

        metric = {
            "value": val,
            "type": "dynamic",
            "refresh_interval": refresh_interval,
            "description": f"{description_prefix} {field.replace('_', ' ')} for {source_name}",
        }

        # Assign units + human-readable values
        if field in ("read_bytes", "write_bytes"):
            metric["unit"] = "B"
            metric["human_readable"] = bytes2human(val)
        elif field in ("read_time", "write_time", "busy_time"):
            metric["unit"] = "ms"
        else:
            metric["unit"] = "count"

        metrics[field] = metric

    return metrics


# ───────────────────────────────────────────────
# 💽 Disk Metrics
# ───────────────────────────────────────────────

def get_disk_metrics(all_partitions: bool = False) -> dict[str, Any]:
    """
    Collect disk usage and I/O metrics in a nested, modular structure.

    Structure:
    {
      "<device_mount>": { device, mountpoint, fstype, metrics: {...} },
      "io_counters": {...},
      "io_counters_perdisk": {...}
    }
    """
    metrics: dict[str, Any] = {}

    # ── Per-partition usage ─────────────────────
    for part in psutil.disk_partitions(all=all_partitions):
        if os.name == "nt" and ("cdrom" in part.opts or not part.fstype):
            continue

        try:
            usage = psutil.disk_usage(part.mountpoint)
        except Exception:
            continue  # skip inaccessible partitions

        key = sanitize_key(f"{part.device}_{part.mountpoint}")
        part_metrics = {}

        usage_data = [
            ("usage_percent", usage.percent, "%", "dynamic", f"Usage % for {part.device}"),
            ("total_bytes", usage.total, "B", "static", f"Total size for {part.device}"),
            ("used_bytes", usage.used, "B", "static", f"Used space for {part.device}"),
            ("free_bytes", usage.free, "B", "static", f"Free space for {part.device}"),
        ]

        for name, val, unit, mtype, desc in usage_data:
            part_metrics[name] = {
                "value": int(val),
                "human_readable": bytes2human(val) if unit == "B" else f"{val}%",
                "unit": unit,
                "type": mtype,
                "refresh_interval": 10,
                "description": desc,
            }

        metrics[key] = {
            "device": part.device,
            "mountpoint": part.mountpoint,
            "fstype": part.fstype,
            "metrics": part_metrics,
        }

    # ── System-wide I/O counters ─────────────────
    try:
        io = psutil.disk_io_counters(perdisk=False, nowrap=True)
        if io:
            metrics["io_counters"] = {
                "description": "System-wide disk I/O counters (aggregate)",
                "metrics": build_metrics_from_namedtuple("system", io),
            }
    except Exception:
        pass

    # ── Per-disk I/O counters ────────────────────
    try:
        io_perdisk = psutil.disk_io_counters(perdisk=True, nowrap=True)
        if io_perdisk:
            per_disk_group: dict[str, Any] = {}
            for disk_name, disk_io in io_perdisk.items():
                sanitized = sanitize_key(disk_name)
                per_disk_group[sanitized] = {
                    "device": disk_name,
                    "metrics": build_metrics_from_namedtuple(disk_name, disk_io),
                    "description": f"I/O counters for {disk_name}",
                }

            metrics["io_counters_perdisk"] = {
                "description": "Per-disk I/O counters (one entry per physical disk)",
                "metrics": per_disk_group,
            }
    except Exception:
        pass

    return metrics

