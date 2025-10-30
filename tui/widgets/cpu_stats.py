from collections import deque
from textual.app import ComposeResult
from textual.widgets import Static
from rich.table import Table
from rich.text import Text
from rich.progress_bar import ProgressBar

from .metric_group import MetricGroup

class CPUStatsGroup(MetricGroup):
    """A widget to display CPU statistics using Rich renderables."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static(id="cpu-stats-renderable")

    def update_data(self, metrics: dict) -> None:
        cpu_data = metrics.get("cpu", {})

        # Create a Rich Table
        table = Table(box=None, expand=True, show_header=False)
        table.add_column(style="bold cyan", width=20)
        table.add_column()

        # --- Average Load ---
        avg_load = cpu_data.get("average", {}).get("cpu_percent", {}).get("value", 0.0)
        avg_load_text = Text(f"{avg_load:.2f}%", style="bold green" if avg_load < 80 else "bold red")
        table.add_row("Average Load:", avg_load_text)

        # --- Per-Core Usage ---
        per_core_list = cpu_data.get("per_core", {}).get("cpu_percent", [])
        for i, core_data in enumerate(per_core_list):
            usage = core_data.get("value", 0)
            bar = ProgressBar(total=100, completed=usage, width=30)
            table.add_row(f"Core {i} Usage:", bar)

        # --- Frequency and Load Average ---
        freq = cpu_data.get("frequency", {}).get("current_freq", {}).get("value", 0)
        table.add_row("Frequency:", f"{freq:.2f} MHz")

        load_avg = cpu_data.get("load", {}).get("load_average", {}).get("value", {})
        load_text = (
            f"1min: {load_avg.get('1min', 0):.2f}%, "
            f"5min: {load_avg.get('5min', 0):.2f}%, "
            f"15min: {load_avg.get('15min', 0):.2f}%"
        )
        table.add_row("Load Average:", load_text)

        # --- Static Info ---
        count_info = cpu_data.get("count", {}).get("count", {}).get("value", {})
        table.add_row("Physical Cores:", str(count_info.get("physical", "N/A")))
        table.add_row("Logical Cores:", str(count_info.get("logical", "N/A")))

        # Update the Static widget with the new table
        self.query_one("#cpu-stats-renderable", Static).update(table)
