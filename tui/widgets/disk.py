from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static
from rich.table import Table
from rich.text import Text
from rich.progress_bar import ProgressBar

from .metric_group import MetricGroup

class DiskUsageGroup(MetricGroup):
    """A widget to display disk usage statistics using Rich renderables."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static("Loading disk data...", id="disk-stats-renderable")

    def _get_usage_style(self, usage: float) -> str:
        """Get style based on disk usage percentage."""
        if usage < 70:
            return "green"
        elif usage < 90:
            return "yellow"
        else:
            return "red"

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
        disk_data = metrics.get("disk", {})

        # Main container table
        table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
        table.add_column(style="bold cyan", width=18)
        table.add_column()

        # --- Partitions ---
        # Partitions are at the top level, not under a "partitions" key
        # Filter out non-partition keys
        partition_keys = [k for k in disk_data.keys()
                         if k not in ("io_counters", "io_counters_perdisk")
                         and isinstance(disk_data.get(k), dict)]

        # Sort partitions to show main drive first (C:\ or /)
        def partition_priority(key):
            partition = disk_data.get(key, {})
            mountpoint = partition.get("mountpoint", "")
            if mountpoint == "/" or mountpoint == "C:\\":
                return 0
            return 1

        partition_keys = sorted(partition_keys, key=partition_priority)

        for part_key in partition_keys:
            partition = disk_data.get(part_key, {})
            if not partition:
                continue

            metrics_data = partition.get("metrics", {})
            if not metrics_data:
                continue

            # Get partition info
            device = partition.get("device", part_key)
            mountpoint = partition.get("mountpoint", "N/A")
            fstype = partition.get("fstype", "N/A")

            # Usage percentage
            usage_data = metrics_data.get("usage_percent", {})
            usage_pct = usage_data.get("value", 0.0)
            usage_style = self._get_usage_style(usage_pct)

            # Create partition label
            partition_label = f"Disk {mountpoint}"

            # Progress bar and percentage
            usage_bar = ProgressBar(total=100, completed=usage_pct, width=35, style=usage_style)
            usage_text = Text(f"{usage_pct:.1f}%", style=f"bold {usage_style}")
            table.add_row(partition_label, usage_bar)
            table.add_row("", usage_text)

            # Disk information
            total = metrics_data.get("total_bytes", {}).get("human_readable", "N/A")
            used = metrics_data.get("used_bytes", {}).get("human_readable", "N/A")
            free = metrics_data.get("free_bytes", {}).get("human_readable", "N/A")

            disk_info_text = Text()
            disk_info_text.append("Total: ", style="dim")
            disk_info_text.append(total, style="bold")
            disk_info_text.append("  ", style="dim")
            disk_info_text.append("Used: ", style="dim")
            disk_info_text.append(used, style="yellow")
            disk_info_text.append("  ", style="dim")
            disk_info_text.append("Free: ", style="dim")
            disk_info_text.append(free, style="green")

            table.add_row("", disk_info_text)

            # File system type
            fs_text = Text()
            fs_text.append("FS: ", style="dim")
            fs_text.append(fstype, style="cyan")
            fs_text.append("  ", style="dim")
            fs_text.append("Device: ", style="dim")
            fs_text.append(device, style="dim")

            table.add_row("", fs_text)

        # --- System-wide I/O Counters ---
        io_counters = disk_data.get("io_counters", {}).get("metrics", {})
        if io_counters:
            # Read/Write counts
            read_count = io_counters.get("read_count", {}).get("value", 0)
            write_count = io_counters.get("write_count", {}).get("value", 0)

            io_counts_text = Text()
            io_counts_text.append("Reads: ", style="dim")
            io_counts_text.append(self._format_count(read_count), style="cyan")
            io_counts_text.append("  ", style="dim")
            io_counts_text.append("Writes: ", style="dim")
            io_counts_text.append(self._format_count(write_count), style="yellow")

            table.add_row("I/O Counts:", io_counts_text)

            # Read/Write bytes
            read_bytes = io_counters.get("read_bytes", {}).get("human_readable", "N/A")
            write_bytes = io_counters.get("write_bytes", {}).get("human_readable", "N/A")

            io_bytes_text = Text()
            io_bytes_text.append("Read: ", style="dim")
            io_bytes_text.append(read_bytes, style="cyan")
            io_bytes_text.append("  ", style="dim")
            io_bytes_text.append("Written: ", style="dim")
            io_bytes_text.append(write_bytes, style="yellow")

            table.add_row("I/O Bytes:", io_bytes_text)

            # Read/Write times
            read_time = io_counters.get("read_time", {}).get("value", 0)
            write_time = io_counters.get("write_time", {}).get("value", 0)

            if read_time > 0 or write_time > 0:
                io_time_text = Text()
                io_time_text.append("Read Time: ", style="dim")
                io_time_text.append(f"{read_time}ms", style="magenta")
                io_time_text.append("  ", style="dim")
                io_time_text.append("Write Time: ", style="dim")
                io_time_text.append(f"{write_time}ms", style="red")

                table.add_row("I/O Times:", io_time_text)

        # --- Per-Disk I/O Counters ---
        io_perdisk = disk_data.get("io_counters_perdisk", {}).get("metrics", {})
        if io_perdisk:
            # Show first disk's per-disk stats (usually there's only one or the main one)
            disk_names = list(io_perdisk.keys())
            if disk_names:
                disk_name = disk_names[0]
                disk_metrics = io_perdisk[disk_name].get("metrics", {})

                if disk_metrics:
                    perdisk_read = disk_metrics.get("read_bytes", {}).get("human_readable", "N/A")
                    perdisk_write = disk_metrics.get("write_bytes", {}).get("human_readable", "N/A")

                    perdisk_text = Text()
                    perdisk_text.append(f"{disk_name}: ", style="bold dim")
                    perdisk_text.append("Read ", style="dim")
                    perdisk_text.append(perdisk_read, style="cyan")
                    perdisk_text.append(" / Write ", style="dim")
                    perdisk_text.append(perdisk_write, style="yellow")

                    table.add_row("Per-Disk I/O:", perdisk_text)

        self.query_one("#disk-stats-renderable", Static).update(table)
