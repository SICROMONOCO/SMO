from collections import deque
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Sparkline, Static

from .metric_group import MetricGroup

class DiskUsageGroup(MetricGroup):
    """A widget to display disk usage statistics."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._read_history = deque(maxlen=50)
        self._write_history = deque(maxlen=50)

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static("Disk I/O (Read/Write Bytes):", classes="stat-title")
        yield Sparkline([0]*50, summary_function=lambda data: data[-1], id="disk-io-sparkline")
        
        with Horizontal():
            yield Static("Main Disk Stats:", classes="stat-title", id="main-disk-title")
            yield Static("N/A", id="main-disk-static")
        
        with Horizontal():
            yield Static("I/O Counters:", classes="stat-title", id="io-counters-title")
            yield Static("N/A", id="io-counters-static")

    def update_data(self, metrics: dict) -> None:
        disk_data = metrics.get("disk", {})
        
        # --- Sparkline for I/O ---
        io_counters = disk_data.get("io_counters", {}).get("metrics", {})
        read_bytes = io_counters.get("read_bytes", {}).get("value")
        write_bytes = io_counters.get("write_bytes", {}).get("value")

        if read_bytes is not None and write_bytes is not None:
            self._read_history.append(read_bytes)
            self.query_one("#disk-io-sparkline", Sparkline).data = list(self._read_history)

        # --- Main Disk Stats ---
        main_disk_key = next((k for k, v in disk_data.items() if v.get("mountpoint") == "/"), None)
        if not main_disk_key:
             main_disk_key = next((k for k, v in disk_data.items() if "C_" in k), None)

        if main_disk_key and isinstance(disk_data.get(main_disk_key), dict):
            main_disk_metrics = disk_data[main_disk_key].get("metrics", {})
            total = main_disk_metrics.get("total_bytes", {}).get("human_readable", "N/A")
            used = main_disk_metrics.get("used_bytes", {}).get("human_readable", "N/A")
            free = main_disk_metrics.get("free_bytes", {}).get("human_readable", "N/A")
            percent = main_disk_metrics.get("usage_percent", {}).get("value", "N/A")
            self.query_one("#main-disk-static", Static).update(
                f"Total: {total}, Used: {used} ({percent}%), Free: {free}"
            )

        # --- Compact I/O Counters ---
        if io_counters:
            reads = io_counters.get("read_count", {}).get("value", "N/A")
            writes = io_counters.get("write_count", {}).get("value", "N/A")
            self.query_one("#io-counters-static", Static).update(
                f"Reads: {reads}, Writes: {writes}"
            )
        
        # --- Handle Alerts ---
        alerts = metrics.get("alerts", [])
        is_alerting = any(alert["metric"].startswith("disk_usage") for alert in alerts)
        self.query_one("#disk-io-sparkline").set_class(is_alerting, "alert-highlight")
