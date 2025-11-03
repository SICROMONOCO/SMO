# metrics/memory.py
import psutil
from psutil._common import bytes2human



def get_memory_metrics():
    # Virtual Memory
    virtual_mem = psutil.virtual_memory()
    virtual_memory = {
        "virtual_memory": {
            "total": {
                "value": virtual_mem.total,
                "human_readable": bytes2human(virtual_mem.total),
                "unit": "bytes",
                "type": "static",
                "description": "Total virtual memory"
            },
            "available": {
                "value": virtual_mem.available,
                "human_readable": bytes2human(virtual_mem.available),
                "unit": "bytes",
                "type": "dynamic",
                "refresh_interval": 5,
                "description": "Available virtual memory"
            },
            "used": {
                "value": virtual_mem.used,
                "human_readable": bytes2human(virtual_mem.used),
                "unit": "bytes",
                "type": "dynamic",
                "refresh_interval": 5,
                "description": "Used virtual memory"
            },
            "free": {
                "value": virtual_mem.free,
                "human_readable": bytes2human(virtual_mem.free),
                "unit": "bytes",
                "type": "dynamic",
                "refresh_interval": 5,
                "description": "Free virtual memory"
            },
            "percent": {
                "value": virtual_mem.percent,
                "unit": "%",
                "type": "dynamic",
                "refresh_interval": 5,
                "description": "Percentage of used virtual memory"
            }
        }
    }

    # Swap Memory
    swap_mem = psutil.swap_memory()
    swap_memory = {
        "swap_memory": {
            "total": {
                "value": swap_mem.total,
                "human_readable": bytes2human(swap_mem.total),
                "unit": "bytes",
                "type": "static",
                "description": "Total swap memory"
            },
            "used": {
                "value": swap_mem.used,
                "human_readable": bytes2human(swap_mem.used),
                "unit": "bytes",
                "type": "dynamic",
                "refresh_interval": 5,
                "description": "Used swap memory"
            },
            "free": {
                "value": swap_mem.free,
                "human_readable": bytes2human(swap_mem.free),
                "unit": "bytes",
                "type": "dynamic",
                "refresh_interval": 5,
                "description": "Free swap memory"
            },
            "percent": {
                "value": swap_mem.percent,
                "unit": "%",
                "type": "dynamic",
                "refresh_interval": 5,
                "description": "Percentage of used swap memory"
            },
            "sin": {
                "value": swap_mem.sin,
                "unit": "bytes",
                "type": "dynamic",
                "refresh_interval": 10,
                "description": "Swap memory sin"
            },
            "sout": {
                "value": swap_mem.sout,
                "unit": "bytes",
                "type": "dynamic",
                "refresh_interval": 10,
                "description": "Swap memory sout"
            }
        }
    }

    # Combine all memory metrics
    memory_metrics = {**virtual_memory, **swap_memory}
    return memory_metrics

