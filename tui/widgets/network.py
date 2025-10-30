from collections import deque
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Sparkline, Static

from .metric_group import MetricGroup

class NetworkIOGroup(MetricGroup):
    """A widget to display network I/O statistics."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._sent_history = deque(maxlen=50)
        self._recv_history = deque(maxlen=50)

    def compose(self) -> ComposeResult:
        yield from super().compose()
        yield Static("Network I/O (Bytes Sent/Received):", classes="stat-title")
        yield Sparkline([0]*50, summary_function=lambda data: data[-1], id="net-io-sparkline")
        
        with Horizontal():
            yield Static("Active Interface:", classes="stat-title", id="net-active-title")
            yield Static("N/A", id="net-active-static")

    def update_data(self, metrics: dict) -> None:
        net_data = metrics.get("network", {})
        
        # --- Sparkline for I/O ---
        io_counters = net_data.get("io_counters", {}).get("metrics", {})
        bytes_sent = io_counters.get("bytes_sent", {}).get("value")
        bytes_recv = io_counters.get("bytes_recv", {}).get("value")

        if bytes_sent is not None:
            self._sent_history.append(bytes_sent)
            self.query_one("#net-io-sparkline", Sparkline).data = list(self._sent_history)
        
        if bytes_recv is not None:
            self._recv_history.append(bytes_recv)

        # --- Active Interface Stats ---
        active_iface_name = "N/A"
        iface_stats = net_data.get("stats", {}).get("interfaces", {})
        for name, stats in iface_stats.items():
            if stats.get("metrics", {}).get("isup", {}).get("value") and "loopback" not in name.lower():
                active_iface_name = name
                break
        
        if active_iface_name != "N/A":
            speed = iface_stats[active_iface_name].get("metrics", {}).get("speed", {}).get("value", "N/A")
            mtu = iface_stats[active_iface_name].get("metrics", {}).get("mtu", {}).get("value", "N/A")
            self.query_one("#net-active-static", Static).update(
                f"{active_iface_name}\nSpeed: {speed} Mbps, MTU: {mtu}"
            )

        # --- Handle Alerts ---
        alerts = metrics.get("alerts", [])
        is_alerting = any(alert["metric"] == "network_bytes_sent" for alert in alerts)
        self.query_one("#net-io-sparkline").set_class(is_alerting, "alert-highlight")
