import psutil
from psutil._common import bytes2human
from typing import Any


def get_network_metrics() -> dict[str, Any]:
    """
    Collect network interface, I/O, and connection metrics in a structured format.

    Structure:
    {
      "io_counters": {...},
      "io_counters_pernic": {...},
      "interfaces": {...},
      "stats": {...}
    }
    """
    metrics: dict[str, Any] = {}

    # ──────────────────────────────
    # 1️⃣ System-wide network I/O (aggregate)
    # ──────────────────────────────
    try:
        io = psutil.net_io_counters(pernic=False, nowrap=True)
        if io:
            metrics["io_counters"] = {
                "description": "System-wide network I/O statistics (aggregate)",
                "metrics": {
                    k: {
                        "value": v,
                        "unit": "count" if not k.endswith("bytes") else "B",
                        "human_readable": bytes2human(v)
                        if k.endswith("bytes")
                        else str(v),
                        "type": "dynamic",
                        "refresh_interval": 5,
                        "description": f"Network I/O field: {k}",
                    }
                    for k, v in io._asdict().items()
                },
            }
    except Exception:
        pass

    # ──────────────────────────────
    # 2️⃣ Per-interface network I/O
    # ──────────────────────────────
    try:
        pernic = psutil.net_io_counters(pernic=True, nowrap=True)
        if pernic:
            pernic_metrics: dict[str, Any] = {}
            for iface, stats in pernic.items():
                pernic_metrics[iface] = {
                    "description": f"Network I/O for interface {iface}",
                    "metrics": {
                        k: {
                            "value": v,
                            "unit": "count" if not k.endswith("bytes") else "B",
                            "human_readable": bytes2human(v)
                            if k.endswith("bytes")
                            else str(v),
                            "type": "dynamic",
                            "refresh_interval": 5,
                            "description": f"{k} for interface {iface}",
                        }
                        for k, v in stats._asdict().items()
                    },
                }

            metrics["io_counters_pernic"] = {
                "description": "Per-interface network I/O counters",
                "metrics": pernic_metrics,
            }
    except Exception:
        pass

    # ──────────────────────────────
    # 3️⃣ Interface addresses
    # ──────────────────────────────
    try:
        addrs = psutil.net_if_addrs()
        if addrs:
            iface_addrs: dict[str, Any] = {}
            for iface, addr_list in addrs.items():
                iface_addrs[iface] = {
                    "description": f"Addresses for interface {iface}",
                    "addresses": [
                        {
                            "family": str(addr.family),
                            "address": addr.address,
                            "netmask": addr.netmask,
                            "broadcast": addr.broadcast,
                            "ptp": addr.ptp,
                        }
                        for addr in addr_list
                    ],
                }
            metrics["interfaces"] = {
                "description": "Network interface addresses (IPv4, IPv6, MAC)",
                "interfaces": iface_addrs,
            }
    except Exception:
        pass

    # ──────────────────────────────
    # 4️⃣ Interface stats
    # ──────────────────────────────
    try:
        stats = psutil.net_if_stats()
        if stats:
            iface_stats: dict[str, Any] = {}
            for iface, s in stats.items():
                iface_stats[iface] = {
                    "description": f"Network interface stats for {iface}",
                    "metrics": {
                        "isup": {
                            "value": s.isup,
                            "unit": "bool",
                            "type": "dynamic",
                            "description": f"Interface {iface} up/down state",
                        },
                        "duplex": {
                            "value": str(s.duplex),
                            "unit": "",
                            "type": "static",
                            "description": f"Duplex mode for {iface}",
                        },
                        "speed": {
                            "value": s.speed,
                            "unit": "Mbps",
                            "type": "dynamic",
                            "refresh_interval": 10,
                            "description": f"Speed of {iface}",
                        },
                        "mtu": {
                            "value": s.mtu,
                            "unit": "bytes",
                            "type": "static",
                            "description": f"MTU for {iface}",
                        },
                        "flags": {
                            "value": s.flags,
                            "unit": "",
                            "type": "static",
                            "description": f"Interface flags for {iface}",
                        },
                    },
                }
            metrics["stats"] = {
                "description": "Per-interface operational statistics",
                "interfaces": iface_stats,
            }
    except Exception:
        pass

    return metrics
