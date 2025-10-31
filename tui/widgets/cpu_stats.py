from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static
import logging

logger = logging.getLogger(__name__)
from rich.table import Table
from rich.text import Text
from rich.progress_bar import ProgressBar
from rich.console import Group
from rich.columns import Columns

from .metric_group import MetricGroup

class CPUStatsGroup(MetricGroup):
    """A widget to display CPU statistics using Rich renderables."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static("Loading...", id="cpu-stats-renderable")

    def _get_usage_style(self, usage: float) -> str:
        """Get style based on CPU usage percentage."""
        if usage < 50:
            return "green"
        elif usage < 80:
            return "yellow"
        else:
            return "red"

    def update_data(self, metrics: dict) -> None:
        cpu_data = metrics.get("cpu", {})

        # Main container table
        main_table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
        main_table.add_column(style="bold cyan", width=18)
        main_table.add_column()

        # --- Average CPU Usage ---
        avg_data = cpu_data.get("average", {}).get("cpu_percent", {})
        avg_load = avg_data.get("value", 0.0)
        alert = avg_data.get("alert")
        
        # Style based on usage
        usage_style = self._get_usage_style(avg_load)
        avg_text = Text(f"{avg_load:.1f}%", style=f"bold {usage_style}")
        
        
        avg_bar = ProgressBar(total=100, completed=avg_load, width=35, style=usage_style)
        main_table.add_row("Average CPU:", avg_bar)
        main_table.add_row("", avg_text)

        # --- Per-Core Usage (Compact Grid) ---
        per_core_data = cpu_data.get("per_core", {})
        if per_core_data:
            # Extract core usages and sort by core number
            core_usages = []
            for key, core_info in sorted(per_core_data.items()):
                if key.startswith("core_") and key.endswith("_usage"):
                    core_num = key.replace("core_", "").replace("_usage", "")
                    try:
                        core_idx = int(core_num)
                        usage = core_info.get("value", 0.0)
                        core_usages.append((core_idx, usage))
                    except ValueError:
                        continue
            
            if core_usages:
                # Create compact per-core display with percentages
                # Format: C0: 0.0%  C1: 0.0%  C2: 16.7%  ...
                core_text = Text()
                cores_per_line = 4
                for idx, (core_idx, usage) in enumerate(sorted(core_usages)):
                    if idx > 0 and idx % cores_per_line == 0:
                        core_text.append("\n", style="dim")
                    style = self._get_usage_style(usage)
                    core_text.append(f"C{core_idx}:", style="dim")
                    core_text.append(f"{usage:5.1f}%", style=style)
                    if idx < len(core_usages) - 1:
                        core_text.append("  ", style="dim")
                
                main_table.add_row("Per-Core:", core_text)
                
                # Add visual bars in a compact horizontal layout
                all_bars = []
                for core_idx, usage in sorted(core_usages):
                    style = self._get_usage_style(usage)
                    bar = ProgressBar(total=100, completed=usage, width=12, style=style)
                    all_bars.append(bar)
                
                if all_bars:
                    # Display bars in rows of 4
                    bars_lines = []
                    cores_per_row = 4
                    for i in range(0, len(all_bars), cores_per_row):
                        row_bars = all_bars[i:i+cores_per_row]
                        bars_row = Columns(row_bars, equal=True, expand=True, padding=(0, 1))
                        bars_lines.append(bars_row)
                    
                    if len(bars_lines) == 1:
                        main_table.add_row("", bars_lines[0])
                    else:
                        bars_group = Group(*bars_lines)
                        main_table.add_row("", bars_group)

        # --- CPU Frequency ---
        freq_data = cpu_data.get("frequency", {}).get("current_freq", {})
        freq = freq_data.get("value", 0)
        if freq > 0:
            freq_text = Text(f"{freq:.0f} MHz", style="bold blue")
            main_table.add_row("Frequency:", freq_text)

        # --- Load Averages ---
        load_data = cpu_data.get("load", {}).get("load_average", {}).get("value", {})
        if load_data:
            load_text = Text()
            load_text.append("1m: ", style="dim")
            load_text.append(f"{load_data.get('1min', 0):.2f}", style="cyan")
            load_text.append("  ")
            load_text.append("5m: ", style="dim")
            load_text.append(f"{load_data.get('5min', 0):.2f}", style="cyan")
            load_text.append("  ")
            load_text.append("15m: ", style="dim")
            load_text.append(f"{load_data.get('15min', 0):.2f}", style="cyan")
            main_table.add_row("Load Avg:", load_text)

        # --- Core Count Info ---
        count_data = cpu_data.get("count", {}).get("count", {}).get("value", {})
        if count_data:
            cores_text = Text()
            cores_text.append(f"{count_data.get('physical', 'N/A')}", style="bold")
            cores_text.append(" physical", style="dim")
            cores_text.append(" / ", style="dim")
            cores_text.append(f"{count_data.get('logical', 'N/A')}", style="bold")
            cores_text.append(" logical", style="dim")
            main_table.add_row("Cores:", cores_text)

        # --- CPU Stats (Context Switches, Interrupts, etc.) ---
        stats_data = cpu_data.get("stats", {})
        if stats_data:
            # Format large numbers
            def format_count(value: int) -> str:
                if value >= 1_000_000_000:
                    return f"{value / 1_000_000_000:.2f}B"
                elif value >= 1_000_000:
                    return f"{value / 1_000_000:.2f}M"
                elif value >= 1_000:
                    return f"{value / 1_000:.2f}K"
                return str(value)
            
            stats_text = Text()
            if "ctx_switches" in stats_data:
                ctx_val = stats_data["ctx_switches"].get("value", 0)
                stats_text.append("Ctx: ", style="dim")
                stats_text.append(format_count(ctx_val), style="magenta")
                stats_text.append("  ")
            
            if "interrupts" in stats_data:
                int_val = stats_data["interrupts"].get("value", 0)
                stats_text.append("Int: ", style="dim")
                stats_text.append(format_count(int_val), style="cyan")
                stats_text.append("  ")
            
            if "soft_interrupts" in stats_data:
                soft_val = stats_data["soft_interrupts"].get("value", 0)
                stats_text.append("Soft: ", style="dim")
                stats_text.append(format_count(soft_val), style="yellow")
                stats_text.append("  ")
            
            if "syscalls" in stats_data:
                sys_val = stats_data["syscalls"].get("value", 0)
                stats_text.append("Sys: ", style="dim")
                stats_text.append(format_count(sys_val), style="green")
            
            if stats_text:
                main_table.add_row("Stats:", stats_text)

        # Update the Static widget with the new table
        try:
            static_widget = self.query_one("#cpu-stats-renderable", Static)
            static_widget.update(main_table)
        except Exception as e:
            # Log error with more details
            logger.error(f"Failed to update CPU stats widget: {e}", exc_info=True)
            # Try to create the widget if it doesn't exist
            try:
                # Check if we can find it at all
                self.query_one("#cpu-stats-renderable")
            except:
                # Widget doesn't exist, try to mount it
                logger.warning("CPU stats Static widget not found, attempting to create it")
                self.mount(Static("Error: Widget not initialized", id="cpu-stats-renderable"))
