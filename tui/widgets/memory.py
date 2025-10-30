from collections import deque
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Sparkline, Static

from .metric_group import MetricGroup

class MemoryGroup(MetricGroup):
    """A widget to display memory statistics."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._vmem_history = deque(maxlen=50)
        self._swap_history = deque(maxlen=50)

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static("Virtual & Swap Memory Usage (%):", classes="stat-title")
        yield Sparkline([0]*50, summary_function=lambda data: data[-1], id="memory-sparkline")
        
        with Horizontal():
            with Container(id="virtual-mem-container"):
                yield Static("Virtual Memory:", classes="stat-title")
                yield Static("N/A", id="vmem-static")
            with Container(id="swap-mem-container"):
                yield Static("Swap Memory:", classes="stat-title")
                yield Static("N/A", id="swap-static")

    def update_data(self, metrics: dict) -> None:
        mem_data = metrics.get("memory", {})
        
        # Virtual Memory
        vmem = mem_data.get("virtual_memory", {}).get("virtual_memory", {})
        if vmem:
            vmem_pct = vmem.get("percent", {}).get("value")
            if vmem_pct is not None:
                self._vmem_history.append(vmem_pct)
                self.query_one("#memory-sparkline", Sparkline).data = list(self._vmem_history)
            
            total = vmem.get("total", {}).get("human_readable", "N/A")
            used = vmem.get("used", {}).get("human_readable", "N/A")
            available = vmem.get("available", {}).get("human_readable", "N/A")
            self.query_one("#vmem-static", Static).update(
                f"Total: {total}\nUsed: {used}\nAvailable: {available}"
            )

        # Swap Memory
        swap = mem_data.get("swap_memory", {}).get("swap_memory", {})
        if swap:
            swap_pct = swap.get("percent", {}).get("value")
            if swap_pct is not None:
                self._swap_history.append(swap_pct)
            
            total = swap.get("total", {}).get("human_readable", "N/A")
            used = swap.get("used", {}).get("human_readable", "N/A")
            free = swap.get("free", {}).get("human_readable", "N/A")
            self.query_one("#swap-static", Static).update(
                f"Total: {total}\nUsed: {used}\nFree: {free}"
            )
        
        # --- Handle Alerts ---
        alerts = metrics.get("alerts", [])
        is_alerting = any(alert["metric"] == "memory_percent" for alert in alerts)
        self.query_one("#memory-sparkline").set_class(is_alerting, "alert-highlight")
