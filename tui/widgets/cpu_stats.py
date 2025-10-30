from collections import deque
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.dom import NoMatches
from textual.widgets import Label, Sparkline, Static, ProgressBar
from rich.table import Table

from .metric_group import MetricGroup

class CPUStatsGroup(MetricGroup):
    """A widget to display CPU statistics."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._history = deque(maxlen=50)

    def compose(self) -> ComposeResult:
        yield from super().compose()
        with Horizontal(id="cpu-main-stats"):
            with VerticalScroll():
                yield Static("Average Core Load:", classes="stat-title")
                yield Sparkline([0]*50, summary_function=lambda data: data[-1], id="cpu-avg-sparkline")
                
                yield Static("CPU Frequency:", classes="stat-title")
                yield Static("N/A", id="cpu-freq-static")
                
                yield Static("Load Average:", classes="stat-title")
                yield Static("1min: N/A, 5min: N/A, 15min: N/A", id="cpu-load-avg-static")

            with VerticalScroll(id="cpu-cores-container"):
                yield Static("Per-Core Usage:", classes="stat-title")

        with Container(id="cpu-static-info"):
            yield Static("Static CPU Info:", classes="stat-title")
            yield Static(id="cpu-info-table")

    def update_data(self, metrics: dict) -> None:
        cpu_data = metrics.get("cpu", {})
        
        # --- Update Dynamic Stats ---
        avg_load = cpu_data.get("average", {}).get("cpu_percent", {}).get("value")
        if avg_load is not None:
            self._history.append(avg_load)
            self.query_one("#cpu-avg-sparkline", Sparkline).data = list(self._history)

        freq = cpu_data.get("frequency", {}).get("current_freq", {}).get("value")
        if freq is not None:
            self.query_one("#cpu-freq-static", Static).update(f"{freq:.2f} MHz")
            
        load_avg = cpu_data.get("load", {}).get("load_average", {}).get("value", {})
        if load_avg:
            self.query_one("#cpu-load-avg-static", Static).update(
                f"1min: {load_avg.get('1min', 'N/A'):.2f}%, "
                f"5min: {load_avg.get('5min', 'N/A'):.2f}%, "
                f"15min: {load_avg.get('15min', 'N/A'):.2f}%"
            )

        per_core = cpu_data.get("per_core", {})
        cores_container = self.query_one("#cpu-cores-container")
        for core_id, core_data in per_core.items():
            usage = core_data.get("value")
            if usage is not None:
                try:
                    bar = cores_container.query_one(f"#{core_id}", ProgressBar)
                    bar.progress = usage
                except NoMatches:
                    # Create the bar if it doesn't exist
                    cores_container.mount(Label(f"{core_id.replace('_', ' ').title()}:"))
                    cores_container.mount(ProgressBar(total=100, show_eta=False, id=core_id))

        # --- Update Static Info Table ---
        count_info = cpu_data.get("count", {}).get("count", {}).get("value", {})
        
        static_table = Table(box=None, show_header=False, expand=True)
        static_table.add_column(style="bold cyan")
        static_table.add_column()
        
        static_table.add_row("Physical Cores:", str(count_info.get("physical", "N/A")))
        static_table.add_row("Logical Cores:", str(count_info.get("logical", "N/A")))
        
        static_table.add_row("Architecture:", "x86_64 (Example)")
        static_table.add_row("Full Name:", "Intel Core i9 (Example)")
        
        self.query_one("#cpu-info-table", Static).update(static_table)
        
        # --- Handle Alerts ---
        alerts = metrics.get("alerts", [])
        is_alerting = any(alert["metric"] == "cpu_percent" for alert in alerts)
        self.query_one("#cpu-avg-sparkline").set_class(is_alerting, "alert-highlight")
