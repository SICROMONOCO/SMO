from textual.app import ComposeResult
from textual.widgets import Static
from rich.table import Table
from rich.text import Text
from rich.progress_bar import ProgressBar

from .metric_group import MetricGroup

class MemoryGroup(MetricGroup):
    """A widget to display memory statistics using Rich renderables."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static(id="memory-stats-renderable")

    def update_data(self, metrics: dict) -> None:
        mem_data = metrics.get("memory", {})

        table = Table(box=None, expand=True, show_header=False)
        table.add_column(style="bold cyan", width=20)
        table.add_column()

        # --- Virtual Memory ---
        vmem = mem_data.get("virtual_memory", {})
        if vmem:
            vmem_pct = vmem.get("percent", {}).get("value", 0)
            vmem_bar = ProgressBar(total=100, completed=vmem_pct, width=30)
            table.add_row("Virtual Memory:", vmem_bar)

            total = vmem.get("total", {}).get("human_readable", "N/A")
            used = vmem.get("used", {}).get("human_readable", "N/A")
            available = vmem.get("available", {}).get("human_readable", "N/A")
            table.add_row("", f"Total: {total}, Used: {used}, Available: {available}")

        # --- Swap Memory ---
        swap = mem_data.get("swap_memory", {})
        if swap:
            swap_pct = swap.get("percent", {}).get("value", 0)
            swap_bar = ProgressBar(total=100, completed=swap_pct, width=30)
            table.add_row("Swap Memory:", swap_bar)

            total = swap.get("total", {}).get("human_readable", "N/A")
            used = swap.get("used", {}).get("human_readable", "N/A")
            free = swap.get("free", {}).get("human_readable", "N/A")
            table.add_row("", f"Total: {total}, Used: {used}, Free: {free}")

        self.query_one("#memory-stats-renderable", Static).update(table)
