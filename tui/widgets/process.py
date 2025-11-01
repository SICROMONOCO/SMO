from textual.app import ComposeResult
from textual.widgets import Static
from rich.table import Table
from rich.text import Text
from rich.progress_bar import ProgressBar

from .metric_group import MetricGroup

class ProcessGroup(MetricGroup):
    """A widget to display process statistics for the SMO agent process."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static("Loading process data...", id="process-stats-renderable")

    def _get_usage_style(self, usage: float) -> str:
        """Get style based on usage percentage."""
        if usage < 50:
            return "green"
        elif usage < 80:
            return "yellow"
        else:
            return "red"

    def _format_bytes(self, value: int) -> str:
        """Format bytes to human-readable format."""
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}GB"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.2f}MB"
        elif value >= 1_000:
            return f"{value / 1_000:.2f}KB"
        return f"{value}B"

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in seconds to human-readable format."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def _format_count(self, value: int) -> str:
        """Format large numbers with K/M/B suffixes."""
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        elif value >= 1_000:
            return f"{value / 1_000:.2f}K"
        return str(value)

    def update_data(self, metrics: dict) -> None:
        process_data = metrics.get("process", {})

        # Main container table
        table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
        table.add_column(style="bold cyan", width=18)
        table.add_column()

        # Check for errors
        if "error" in process_data:
            error_text = Text(f"Error: {process_data['error']}", style="bold red")
            table.add_row("Status:", error_text)
            self.query_one("#process-stats-renderable", Static).update(table)
            return

        # --- Process ID ---
        pid = process_data.get("pid")
        if pid is not None:
            pid_text = Text(str(pid), style="bold yellow")
            table.add_row("PID:", pid_text)

        # --- Uptime ---
        uptime_data = process_data.get("uptime", {})
        uptime_value = uptime_data.get("value")
        if uptime_value is not None:
            uptime_str = self._format_uptime(uptime_value)
            uptime_text = Text(uptime_str, style="green")
            table.add_row("Uptime:", uptime_text)

        # --- CPU Usage ---
        cpu_data = process_data.get("cpu", {})
        cpu_percent = cpu_data.get("value", 0.0)
        
        # Style based on usage
        usage_style = self._get_usage_style(cpu_percent)
        cpu_text = Text(f"{cpu_percent:.1f}%", style=f"bold {usage_style}")
        
        cpu_bar = ProgressBar(total=100, completed=cpu_percent, width=35, style=usage_style)
        table.add_row("CPU Usage:", cpu_bar)
        table.add_row("", cpu_text)

        # --- Memory Information ---
        memory_data = process_data.get("memory", {})
        if memory_data:
            # Memory percentage with progress bar
            mem_percent_data = memory_data.get("percent", {})
            mem_percent = mem_percent_data.get("value", 0.0)
            
            mem_usage_style = self._get_usage_style(mem_percent)
            mem_text = Text(f"{mem_percent:.2f}%", style=f"bold {mem_usage_style}")
            
            mem_bar = ProgressBar(total=100, completed=mem_percent, width=35, style=mem_usage_style)
            table.add_row("Memory Usage:", mem_bar)
            table.add_row("", mem_text)

            # RSS and VMS
            rss_data = memory_data.get("rss", {})
            vms_data = memory_data.get("vms", {})
            
            if rss_data or vms_data:
                mem_info_text = Text()
                
                if rss_data:
                    rss_value = rss_data.get("value", 0)
                    rss_str = self._format_bytes(rss_value)
                    mem_info_text.append("RSS: ", style="dim")
                    mem_info_text.append(rss_str, style="cyan")
                    if vms_data:
                        mem_info_text.append("  ", style="dim")
                
                if vms_data:
                    vms_value = vms_data.get("value", 0)
                    vms_str = self._format_bytes(vms_value)
                    mem_info_text.append("VMS: ", style="dim")
                    mem_info_text.append(vms_str, style="magenta")
                
                table.add_row("Memory Size:", mem_info_text)

        # --- I/O Information ---
        io_data = process_data.get("io", {})
        if io_data:
            # Read/Write counts
            read_count_data = io_data.get("read_count", {})
            write_count_data = io_data.get("write_count", {})
            
            read_count = read_count_data.get("value", 0)
            write_count = write_count_data.get("value", 0)
            
            io_counts_text = Text()
            io_counts_text.append("Reads: ", style="dim")
            io_counts_text.append(self._format_count(read_count), style="cyan")
            io_counts_text.append("  ", style="dim")
            io_counts_text.append("Writes: ", style="dim")
            io_counts_text.append(self._format_count(write_count), style="yellow")
            
            table.add_row("I/O Counts:", io_counts_text)
            
            # Read/Write bytes
            read_bytes_data = io_data.get("read_bytes", {})
            write_bytes_data = io_data.get("write_bytes", {})
            
            read_bytes = read_bytes_data.get("value", 0)
            write_bytes = write_bytes_data.get("value", 0)
            
            io_bytes_text = Text()
            io_bytes_text.append("Read: ", style="dim")
            io_bytes_text.append(self._format_bytes(read_bytes), style="cyan")
            io_bytes_text.append("  ", style="dim")
            io_bytes_text.append("Written: ", style="dim")
            io_bytes_text.append(self._format_bytes(write_bytes), style="yellow")
            
            table.add_row("I/O Bytes:", io_bytes_text)

        # --- Threads Information ---
        threads_data = process_data.get("threads", {})
        if threads_data:
            count_data = threads_data.get("count", {})
            delta_data = threads_data.get("delta", {})
            
            thread_count = count_data.get("value", 0)
            thread_delta = delta_data.get("value", 0)
            
            threads_text = Text()
            threads_text.append(str(thread_count), style="bold cyan")
            threads_text.append(" threads", style="dim")
            
            if thread_delta != 0:
                delta_style = "red" if thread_delta > 0 else "green"
                delta_sign = "+" if thread_delta > 0 else ""
                threads_text.append(" (", style="dim")
                threads_text.append(f"{delta_sign}{thread_delta}", style=delta_style)
                threads_text.append(")", style="dim")
            
            table.add_row("Threads:", threads_text)

        self.query_one("#process-stats-renderable", Static).update(table)

