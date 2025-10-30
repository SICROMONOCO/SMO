from textual.app import ComposeResult
from textual.widgets import Static
from rich.table import Table
from rich.text import Text

from .metric_group import MetricGroup

class DiskUsageGroup(MetricGroup):
    """A widget to display disk usage statistics using Rich renderables."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static(id="disk-stats-renderable")

    def update_data(self, metrics: dict) -> None:
        disk_data = metrics.get("disk", {})

        table = Table(box=None, expand=True, show_header=False)
        table.add_column(style="bold cyan", width=20)
        table.add_column()

        # --- Main Disk Stats ---
        partitions = disk_data.get("partitions", {})
        main_disk_key = next((k for k, v in partitions.items() if v.get("mountpoint") == "/"), None)
        if not main_disk_key:
             main_disk_key = next((k for k, v in partitions.items() if "C:\\" in k), None)

        if main_disk_key and isinstance(partitions.get(main_disk_key), dict):
            main_disk_metrics = partitions[main_disk_key].get("metrics", {})
            total = main_disk_metrics.get("total_bytes", {}).get("human_readable", "N/A")
            used = main_disk_metrics.get("used_bytes", {}).get("human_readable", "N/A")
            free = main_disk_metrics.get("free_bytes", {}).get("human_readable", "N/A")
            percent = main_disk_metrics.get("usage_percent", {}).get("value", 0)

            table.add_row("Main Disk Usage:", f"{percent}%")
            table.add_row("", f"Total: {total}, Used: {used}, Free: {free}")

        # --- I/O Counters ---
        io_counters = disk_data.get("io_counters", {}).get("metrics", {})
        if io_counters:
            reads = io_counters.get("read_count", {}).get("value", "N/A")
            writes = io_counters.get("write_count", {}).get("value", "N/A")
            read_bytes = io_counters.get("read_bytes", {}).get("human_readable", "N/A")
            write_bytes = io_counters.get("write_bytes", {}).get("human_readable", "N/A")

            table.add_row("I/O Counters:", f"Reads: {reads}, Writes: {writes}")
            table.add_row("", f"Read: {read_bytes}, Written: {write_bytes}")

        self.query_one("#disk-stats-renderable", Static).update(table)
