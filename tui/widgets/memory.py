from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static
from rich.table import Table
from rich.text import Text
from rich.progress_bar import ProgressBar

from .metric_group import MetricGroup

class MemoryGroup(MetricGroup):
    """A widget to display memory statistics using Rich renderables."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static("Loading memory data...", id="memory-stats-renderable")

    def _get_usage_style(self, usage: float) -> str:
        """Get style based on memory usage percentage."""
        if usage < 50:
            return "green"
        elif usage < 80:
            return "yellow"
        else:
            return "red"

    def update_data(self, metrics: dict) -> None:
        mem_data = metrics.get("memory", {})

        # Main container table
        table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
        table.add_column(style="bold cyan", width=18)
        table.add_column()

        # --- Virtual Memory ---
        vmem = mem_data.get("virtual_memory", {})
        if vmem:
            # Percentage with progress bar
            percent_data = vmem.get("percent", {})
            vmem_pct = percent_data.get("value", 0.0)
            
            # Style based on usage
            usage_style = self._get_usage_style(vmem_pct)
            vmem_text = Text(f"{vmem_pct:.1f}%", style=f"bold {usage_style}")
            
            vmem_bar = ProgressBar(total=100, completed=vmem_pct, width=35, style=usage_style)
            table.add_row("Virtual Memory:", vmem_bar)
            table.add_row("", vmem_text)

            # Memory values in compact format
            total = vmem.get("total", {}).get("human_readable", "N/A")
            used = vmem.get("used", {}).get("human_readable", "N/A")
            available = vmem.get("available", {}).get("human_readable", "N/A")
            free = vmem.get("free", {}).get("human_readable", "N/A")
            
            mem_info_text = Text()
            mem_info_text.append("Total: ", style="dim")
            mem_info_text.append(total, style="bold")
            mem_info_text.append("  ", style="dim")
            mem_info_text.append("Used: ", style="dim")
            mem_info_text.append(used, style="yellow")
            mem_info_text.append("  ", style="dim")
            mem_info_text.append("Avail: ", style="dim")
            mem_info_text.append(available, style="green")
            mem_info_text.append("  ", style="dim")
            mem_info_text.append("Free: ", style="dim")
            mem_info_text.append(free, style="cyan")
            
            table.add_row("", mem_info_text)

        # --- Swap Memory ---
        swap = mem_data.get("swap_memory", {})
        if swap:
            # Percentage with progress bar
            swap_pct_data = swap.get("percent", {})
            swap_pct = swap_pct_data.get("value", 0.0)
            
            # Style based on usage (swap is more critical at lower thresholds)
            swap_usage_style = self._get_usage_style(swap_pct)
            swap_text = Text(f"{swap_pct:.1f}%", style=f"bold {swap_usage_style}")
            
            swap_bar = ProgressBar(total=100, completed=swap_pct, width=35, style=swap_usage_style)
            table.add_row("Swap Memory:", swap_bar)
            table.add_row("", swap_text)

            # Swap values
            total = swap.get("total", {}).get("human_readable", "N/A")
            used = swap.get("used", {}).get("human_readable", "N/A")
            free = swap.get("free", {}).get("human_readable", "N/A")
            
            swap_info_text = Text()
            swap_info_text.append("Total: ", style="dim")
            swap_info_text.append(total, style="bold")
            swap_info_text.append("  ", style="dim")
            swap_info_text.append("Used: ", style="dim")
            swap_info_text.append(used, style="yellow")
            swap_info_text.append("  ", style="dim")
            swap_info_text.append("Free: ", style="dim")
            swap_info_text.append(free, style="green")
            
            table.add_row("", swap_info_text)
            
            # Swap I/O (sin/sout)
            sin_data = swap.get("sin", {})
            sout_data = swap.get("sout", {})
            
            if sin_data or sout_data:
                sin_val = sin_data.get("value", 0) if sin_data else 0
                sout_val = sout_data.get("value", 0) if sout_data else 0
                
                # Format bytes to human readable
                def format_bytes(value: int) -> str:
                    if value >= 1_000_000_000:
                        return f"{value / 1_000_000_000:.2f}GB"
                    elif value >= 1_000_000:
                        return f"{value / 1_000_000:.2f}MB"
                    elif value >= 1_000:
                        return f"{value / 1_000:.2f}KB"
                    return f"{value}B"
                
                swap_io_text = Text()
                swap_io_text.append("Swap In: ", style="dim")
                swap_io_text.append(format_bytes(sin_val), style="magenta")
                swap_io_text.append("  ", style="dim")
                swap_io_text.append("Swap Out: ", style="dim")
                swap_io_text.append(format_bytes(sout_val), style="cyan")
                
                table.add_row("Swap I/O:", swap_io_text)

        self.query_one("#memory-stats-renderable", Static).update(table)
