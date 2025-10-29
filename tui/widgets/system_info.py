from textual.app import ComposeResult
from textual.widgets import Static
from rich.table import Table

from .metric_group import MetricGroup

class SystemInfoGroup(MetricGroup):
    """A widget to display static system information."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static(id="system-info-table")

    def update_data(self, metrics: dict) -> None:
        table = Table(box=None, show_header=False, expand=True)
        table.add_column(style="bold cyan")
        table.add_column()

        # --- CPU Info ---
        cpu_data = metrics.get("cpu", {})
        count_info = cpu_data.get("count", {}).get("count", {}).get("value", {})
        table.add_row("CPU Cores:", f"{count_info.get('physical')} Physical, {count_info.get('logical')} Logical")

        # --- Memory Info ---
        mem_data = metrics.get("memory", {})
        vmem_total = mem_data.get("virtual_memory", {}).get("virtual_memory", {}).get("total", {}).get("human_readable")
        swap_total = mem_data.get("swap_memory", {}).get("swap_memory", {}).get("total", {}).get("human_readable")
        table.add_row("Total Memory:", vmem_total if vmem_total else "N/A")
        table.add_row("Total Swap:", swap_total if swap_total else "N/A")

        # --- Disk Info ---
        disk_data = metrics.get("disk", {})
        partitions = [f"{v.get('device')} ({v.get('fstype')})" for k, v in disk_data.items() if v.get("device")]
        table.add_row("Disk Partitions:", ", ".join(partitions))

        self.query_one("#system-info-table", Static).update(table)
