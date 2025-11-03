from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static
from rich.table import Table
from rich.text import Text

from .metric_group import MetricGroup

class NetworkIOGroup(MetricGroup):
    """A widget to display network I/O statistics using Rich renderables."""

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static("Loading network data...", id="network-stats-renderable")

    def _format_bytes(self, value: int) -> str:
        """Format bytes to human-readable format."""
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}GB"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.2f}MB"
        elif value >= 1_000:
            return f"{value / 1_000:.2f}KB"
        return f"{value}B"

    def _format_count(self, value: int) -> str:
        """Format large numbers with K/M/B suffixes."""
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        elif value >= 1_000:
            return f"{value / 1_000:.2f}K"
        return str(value)

    def _get_ip_address(self, addresses: list) -> tuple:
        """Extract IPv4 and MAC addresses from address list."""
        ipv4 = None
        mac = None
        for addr in addresses:
            family = addr.get("family")
            address = addr.get("address", "")
            if family == "2":  # IPv4
                ipv4 = address
            elif family == "-1":  # MAC/Link
                mac = address
        return (ipv4, mac)

    def update_data(self, metrics: dict) -> None:
        net_data = metrics.get("network", {})

        # Main container table
        table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
        table.add_column(style="bold cyan", width=18)
        table.add_column()

        # --- System-wide I/O Counters ---
        io_counters = net_data.get("io_counters", {}).get("metrics", {})
        if io_counters:
            bytes_sent_val = io_counters.get("bytes_sent", {}).get("value", 0)
            bytes_recv_val = io_counters.get("bytes_recv", {}).get("value", 0)
            packets_sent_val = io_counters.get("packets_sent", {}).get("value", 0)
            packets_recv_val = io_counters.get("packets_recv", {}).get("value", 0)

            # Check for alerts
            bytes_sent_alert = io_counters.get("bytes_sent", {}).get("alert")

            # Format bytes
            bytes_sent = self._format_bytes(bytes_sent_val)
            bytes_recv = self._format_bytes(bytes_recv_val)

            # Data transfer
            io_data_text = Text()
            io_data_text.append("Sent: ", style="dim")
            io_data_text.append(bytes_sent, style="yellow")
            if bytes_sent_alert:
                io_data_text.append(" ⚠", style="bold yellow")
            io_data_text.append("  ", style="dim")
            io_data_text.append("Recv: ", style="dim")
            io_data_text.append(bytes_recv, style="cyan")

            table.add_row("Data Transfer:", io_data_text)

            # Packets
            io_packets_text = Text()
            io_packets_text.append("Sent: ", style="dim")
            io_packets_text.append(self._format_count(packets_sent_val), style="yellow")
            io_packets_text.append("  ", style="dim")
            io_packets_text.append("Recv: ", style="dim")
            io_packets_text.append(self._format_count(packets_recv_val), style="cyan")

            table.add_row("Packets:", io_packets_text)

            # Errors and drops (only show if > 0)
            errin = io_counters.get("errin", {}).get("value", 0)
            errout = io_counters.get("errout", {}).get("value", 0)
            dropin = io_counters.get("dropin", {}).get("value", 0)
            dropout = io_counters.get("dropout", {}).get("value", 0)

            if errin > 0 or errout > 0 or dropin > 0 or dropout > 0:
                errors_text = Text()
                if errin > 0 or errout > 0:
                    errors_text.append("Err In: ", style="dim")
                    errors_text.append(str(errin), style="red")
                    errors_text.append("  ", style="dim")
                    errors_text.append("Err Out: ", style="dim")
                    errors_text.append(str(errout), style="red")
                if dropin > 0 or dropout > 0:
                    if errors_text:
                        errors_text.append("  ", style="dim")
                    errors_text.append("Drop In: ", style="dim")
                    errors_text.append(str(dropin), style="magenta")
                    errors_text.append("  ", style="dim")
                    errors_text.append("Drop Out: ", style="dim")
                    errors_text.append(str(dropout), style="magenta")

                table.add_row("Errors/Drops:", errors_text)

        # --- Active Interfaces (up and with traffic) ---
        iface_stats = net_data.get("stats", {}).get("interfaces", {})
        iface_addresses = net_data.get("interfaces", {}).get("interfaces", {})
        pernic_io = net_data.get("io_counters_pernic", {}).get("metrics", {})

        # Find active interfaces (up, not loopback, with significant traffic)
        active_interfaces = []
        for iface_name, stats in iface_stats.items():
            is_up = stats.get("metrics", {}).get("isup", {}).get("value", False)
            is_loopback = "loopback" in iface_name.lower()

            if is_up and not is_loopback:
                # Get I/O for this interface
                iface_io = pernic_io.get(iface_name, {}).get("metrics", {})
                bytes_sent = iface_io.get("bytes_sent", {}).get("value", 0) if iface_io else 0
                bytes_recv = iface_io.get("bytes_recv", {}).get("value", 0) if iface_io else 0
                total_traffic = bytes_sent + bytes_recv

                active_interfaces.append({
                    "name": iface_name,
                    "stats": stats.get("metrics", {}),
                    "addresses": iface_addresses.get(iface_name, {}).get("addresses", []),
                    "io": iface_io,
                    "traffic": total_traffic
                })

        # Sort by traffic (most active first)
        active_interfaces.sort(key=lambda x: x["traffic"], reverse=True)

        # Display active interfaces (limit to top 3 most active)
        for idx, iface in enumerate(active_interfaces[:3]):
            iface_name = iface["name"]
            iface_stats_data = iface["stats"]
            addresses = iface["addresses"]
            iface_io = iface["io"]

            # Interface name and status
            status_text = Text()
            status_text.append(iface_name, style="bold")
            status_text.append(" ✓", style="green")

            table.add_row(f"Interface {idx + 1}:", status_text)

            # IP and MAC addresses
            ipv4, mac = self._get_ip_address(addresses)
            if ipv4 or mac:
                addr_text = Text()
                if ipv4:
                    addr_text.append("IP: ", style="dim")
                    addr_text.append(ipv4, style="bold green")
                    if mac:
                        addr_text.append("  ", style="dim")
                if mac:
                    addr_text.append("MAC: ", style="dim")
                    addr_text.append(mac, style="dim")
                table.add_row("", addr_text)

            # Speed and MTU
            speed = iface_stats_data.get("speed", {}).get("value", 0)
            mtu = iface_stats_data.get("mtu", {}).get("value", 0)
            if speed > 0 or mtu > 0:
                stats_text = Text()
                if speed > 0:
                    stats_text.append("Speed: ", style="dim")
                    stats_text.append(f"{speed} Mbps", style="cyan")
                    if mtu > 0:
                        stats_text.append("  ", style="dim")
                if mtu > 0:
                    stats_text.append("MTU: ", style="dim")
                    stats_text.append(str(mtu), style="cyan")
                table.add_row("", stats_text)

            # Per-interface I/O
            if iface_io:
                bytes_sent_val = iface_io.get("bytes_sent", {}).get("value", 0)
                bytes_recv_val = iface_io.get("bytes_recv", {}).get("value", 0)
                packets_sent_val = iface_io.get("packets_sent", {}).get("value", 0)
                packets_recv_val = iface_io.get("packets_recv", {}).get("value", 0)

                if bytes_sent_val > 0 or bytes_recv_val > 0:
                    iface_io_text = Text()
                    iface_io_text.append("TX: ", style="dim")
                    iface_io_text.append(self._format_bytes(bytes_sent_val), style="yellow")
                    iface_io_text.append("  ", style="dim")
                    iface_io_text.append("RX: ", style="dim")
                    iface_io_text.append(self._format_bytes(bytes_recv_val), style="cyan")
                    iface_io_text.append("  ", style="dim")
                    iface_io_text.append("Pkts: ", style="dim")
                    iface_io_text.append(f"{self._format_count(packets_sent_val)}/{self._format_count(packets_recv_val)}", style="dim")

                    table.add_row("", iface_io_text)

        # Show count of total interfaces if there are more than 3
        all_ifaces = list(iface_stats.keys())
        if len(all_ifaces) > 3:
            total_text = Text()
            total_text.append(f"Total: {len(all_ifaces)} interfaces", style="dim")
            table.add_row("", total_text)

        self.query_one("#network-stats-renderable", Static).update(table)
