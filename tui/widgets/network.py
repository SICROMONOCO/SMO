from textual.app import ComposeResult
from textual.widgets import Static
from rich.table import Table
from rich.text import Text

from .metric_group import MetricGroup

class NetworkIOGroup(MetricGroup):
    """A widget to display network I/O statistics using Rich renderables."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static(id="network-stats-renderable")

    def update_data(self, metrics: dict) -> None:
        net_data = metrics.get("network", {})

        table = Table(box=None, expand=True, show_header=False)
        table.add_column(style="bold cyan", width=20)
        table.add_column()

        # --- I/O Counters ---
        io_counters = net_data.get("io_counters", {}).get("metrics", {})
        if io_counters:
            bytes_sent = io_counters.get("bytes_sent", {}).get("human_readable", "N/A")
            bytes_recv = io_counters.get("bytes_recv", {}).get("human_readable", "N/A")
            packets_sent = io_counters.get("packets_sent", {}).get("value", "N/A")
            packets_recv = io_counters.get("packets_recv", {}).get("value", "N/A")

            table.add_row("Data Sent:", bytes_sent)
            table.add_row("Data Received:", bytes_recv)
            table.add_row("Packets Sent:", str(packets_sent))
            table.add_row("Packets Received:", str(packets_recv))

        # --- Active Interface ---
        active_iface_name = "N/A"
        iface_stats = net_data.get("stats", {}).get("interfaces", {})
        for name, stats in iface_stats.items():
            if stats.get("metrics", {}).get("isup", {}).get("value") and "loopback" not in name.lower():
                active_iface_name = name
                break

        if active_iface_name != "N/A":
            speed = iface_stats[active_iface_name].get("metrics", {}).get("speed", {}).get("value", "N/A")
            mtu = iface_stats[active_iface_name].get("metrics", {}).get("mtu", {}).get("value", "N/A")
            table.add_row("Active Interface:", active_iface_name)
            table.add_row("", f"Speed: {speed} Mbps, MTU: {mtu}")

        self.query_one("#network-stats-renderable", Static).update(table)
