"""
Process metrics collector for SMO.
Tracks resource usage of the SMO process itself.
"""

import os
import psutil
import threading
import time
from typing import Dict, Any

# Get the current process
_process = psutil.Process(os.getpid())
_start_time = _process.create_time()
_thread_count = threading.active_count()

def gather() -> Dict[str, Any]:
    """Gather metrics about the SMO process itself."""
    global _thread_count

    try:
        # Update thread count
        current_threads = threading.active_count()
        thread_delta = current_threads - _thread_count
        _thread_count = current_threads

        # Initialize CPU percent (first call will return 0.0)
        _process.cpu_percent()
        # Wait a bit to get a real measurement
        time.sleep(0.1)

        with _process.oneshot():  # More efficient collection of multiple metrics
            cpu_percent = _process.cpu_percent()
            mem_info = _process.memory_info()
            io_counters = _process.io_counters()
            mem_percent = _process.memory_percent()

            return {
                "type": "dynamic",
                "pid": _process.pid,
                "uptime": {
                    "type": "dynamic",
                    "value": time.time() - _start_time,
                    "unit": "seconds"
                },
                "cpu": {
                    "type": "dynamic",
                    "value": cpu_percent,
                    "unit": "percent"
                },
                "memory": {
                    "type": "dynamic",
                    "rss": {
                        "value": mem_info.rss,
                        "unit": "bytes",
                        "description": "Resident Set Size"
                    },
                    "vms": {
                        "value": mem_info.vms,
                        "unit": "bytes",
                        "description": "Virtual Memory Size"
                    },
                    "percent": {
                        "value": mem_percent,
                        "unit": "percent"
                    }
                },
                "io": {
                    "type": "dynamic",
                    "read_count": {
                        "value": io_counters.read_count,
                        "unit": "operations"
                    },
                    "write_count": {
                        "value": io_counters.write_count,
                        "unit": "operations"
                    },
                    "read_bytes": {
                        "value": io_counters.read_bytes,
                        "unit": "bytes"
                    },
                    "write_bytes": {
                        "value": io_counters.write_bytes,
                        "unit": "bytes"
                    }
                },
                "threads": {
                    "type": "dynamic",
                    "count": {
                        "value": current_threads,
                        "unit": "threads"
                    },
                    "delta": {
                        "value": thread_delta,
                        "description": "Change in thread count since last check"
                    }
                }
            }
    except Exception as e:
        return {
            "process": {
                "type": "dynamic",
                "error": str(e)
            }
        }
