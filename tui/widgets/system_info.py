from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static
from rich.table import Table
from rich.text import Text
import platform
import socket
import psutil
from datetime import datetime, timedelta

from .metric_group import MetricGroup

class SystemInfoGroup(MetricGroup):
    """A widget to display static system information."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static("Loading system info...", id="system-info-table")

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in seconds to human readable format."""
        if seconds is None:
            return "N/A"
        delta = timedelta(seconds=int(seconds))
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        return " ".join(parts)

    def _format_bytes(self, value: int) -> str:
        """Format bytes to human-readable format."""
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}GB"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.2f}MB"
        elif value >= 1_000:
            return f"{value / 1_000:.2f}KB"
        return f"{value}B"

    def update_data(self, metrics: dict) -> None:
        table = Table(box=None, show_header=False, expand=True, padding=(0, 1))
        table.add_column(style="bold cyan", width=20)
        table.add_column()

        # --- System Information (OS/Platform) ---
        try:
            os_name = platform.system()
            os_release = platform.release()
            os_version = platform.version()
            hostname = socket.gethostname()

            sys_text = Text()
            sys_text.append(f"{os_name} {os_release}", style="bold")
            table.add_row("OS:", sys_text)

            host_text = Text()
            host_text.append(hostname, style="bold green")
            table.add_row("Hostname:", host_text)

            # Boot time
            try:
                boot_time = psutil.boot_time()
                boot_dt = datetime.fromtimestamp(boot_time)
                boot_str = boot_dt.strftime("%Y-%m-%d %H:%M:%S")
                table.add_row("Boot Time:", boot_str)

                # System uptime
                system_uptime = datetime.now().timestamp() - boot_time
                uptime_str = self._format_uptime(system_uptime)
                uptime_text = Text()
                uptime_text.append(uptime_str, style="cyan")
                table.add_row("System Uptime:", uptime_text)
            except Exception:
                pass

            # Python version
            python_ver = platform.python_version()
            table.add_row("Python:", f"v{python_ver}")

        except Exception:
            pass

        # --- CPU Info (Static) ---
        cpu_data = metrics.get("cpu", {})
        count_info = cpu_data.get("count", {}).get("value", {})
        if count_info:
            cpu_text = Text()
            cpu_text.append(f"{count_info.get('physical', 'N/A')}", style="bold")
            cpu_text.append(" physical", style="dim")
            cpu_text.append(" / ", style="dim")
            cpu_text.append(f"{count_info.get('logical', 'N/A')}", style="bold")
            cpu_text.append(" logical", style="dim")
            table.add_row("CPU Cores:", cpu_text)

        # --- Memory Info (Static totals) ---
        mem_data = metrics.get("memory", {})
        vmem_total = mem_data.get("virtual_memory", {}).get("total", {}).get("human_readable")
        swap_total = mem_data.get("swap_memory", {}).get("total", {}).get("human_readable")
        if vmem_total:
            table.add_row("Total Memory:", vmem_total)
        if swap_total:
            table.add_row("Total Swap:", swap_total)

        # --- Process Information (SMO Agent) ---
        process_data = metrics.get("process", {})
        if process_data:
            pid = process_data.get("pid")
            if pid:
                pid_text = Text()
                pid_text.append(str(pid), style="bold yellow")
                table.add_row("Process PID:", pid_text)

            # Process uptime
            process_uptime = process_data.get("uptime", {}).get("value")
            if process_uptime is not None:
                uptime_str = self._format_uptime(process_uptime)
                uptime_text = Text()
                uptime_text.append(uptime_str, style="green")
                table.add_row("Process Uptime:", uptime_text)

            # Process threads
            threads = process_data.get("threads", {}).get("count", {}).get("value")
            if threads is not None:
                threads_text = Text()
                threads_text.append(str(threads), style="cyan")
                table.add_row("Threads:", threads_text)

            # Process memory (RSS)
            proc_mem = process_data.get("memory", {})
            if proc_mem:
                rss = proc_mem.get("rss", {}).get("value")
                if rss:
                    rss_str = self._format_bytes(rss)
                    table.add_row("Process Memory:", rss_str)

        # --- Disk Info (Partition list) ---
        disk_data = metrics.get("disk", {})
        # Check for partitions in different possible locations
        partitions_data = disk_data.get("partitions", {})
        if not partitions_data:
            # Check top-level keys that might be partitions
            partition_keys = [k for k in disk_data.keys()
                             if k not in ("io_counters", "io_counters_perdisk")
                             and isinstance(disk_data.get(k), dict)]
            if partition_keys:
                partitions_list = []
                for key in partition_keys[:5]:  # Limit to 5 to keep it compact
                    part = disk_data[key]
                    device = part.get("device", key)
                    fstype = part.get("fstype", "unknown")
                    partitions_list.append(f"{device} ({fstype})")

                if partitions_list:
                    partitions_text = Text()
                    partitions_text.append(", ".join(partitions_list), style="dim")
                    if len(partition_keys) > 5:
                        partitions_text.append(f" ... ({len(partition_keys)} total)", style="dim")
                    table.add_row("Partitions:", partitions_text)

        self.query_one("#system-info-table", Static).update(table)
