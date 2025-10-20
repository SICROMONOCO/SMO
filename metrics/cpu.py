# metrics/cpu.py
import psutil

def get_cpu_metrics():
    # CPU Percent (average + per core)
    per_core_usages = psutil.cpu_percent(interval=0.1, percpu=True)
    per_core = {
        f"core_{i}_usage": {
            "value": usage,
            "unit": "%",
            "type": "dynamic",
            "refresh_interval": 2,
            "description": f"CPU usage for core {i}"
        }
        for i, usage in enumerate(per_core_usages)
    }

    # Average CPU
    average = {
        "cpu_percent": {
            "value": psutil.cpu_percent(),
            "unit": "%",
            "type": "dynamic",
            "refresh_interval": 2,
            "description": "Average CPU utilization"
        }
    }

    # Frequency
    freq = psutil.cpu_freq()
    frequency = {
        "current_freq": {
            "value": freq.current if freq else 0,
            "unit": "MHz",
            "type": "dynamic",
            "refresh_interval": 5,
            "description": "Current CPU frequency"
        }
    }

    # CPU Count
    counts = psutil.cpu_count(logical=False)
    logical_counts = psutil.cpu_count(logical=True)
    count_info = {
        "count": {
            "value": {"logical": logical_counts, "physical": counts},
            "unit": "cores",
            "type": "static",
            "refresh_interval": None,
            "description": "Number of CPU cores"
        }
    }

    # Load Average
    loa = [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()]
    load_avg = {
        "load_average": {
            "value": {"1min": loa[0], "5min": loa[1], "15min": loa[2]},
            "unit": "%",
            "type": "dynamic",
            "refresh_interval": 10,
            "description": "System load averages normalized by CPU count"
        }
    }

    # CPU Stats
    stats = psutil.cpu_stats()._asdict()
    cpu_stats = {
        key: {
            "value": value,
            "unit": "count",
            "type": "dynamic",
            "refresh_interval": 5,
            "description": f"CPU stat: {key}"
        }
        for key, value in stats.items()
    }

    # Now return the full hierarchical CPU dictionary
    return {
        "per_core": per_core,
        "average": average,
        "frequency": frequency,
        "count": count_info,
        "load": load_avg,
        "stats": cpu_stats
    }
