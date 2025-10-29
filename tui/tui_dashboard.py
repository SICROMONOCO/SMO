
"""
The main TUI dashboard application.

This file brings together the modular UI components from the `widgets`
directory and orchestrates the application's behavior.
"""

from __future__ import annotations
import json
import yaml
import csv
from pathlib import Path

# Textual Imports
from textual.app import App, ComposeResult
from textual.dom import NoMatches
from textual.containers import Container, Horizontal, VerticalScroll, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Static,
    Switch,
    TabbedContent,
    TabPane,
    RadioButton,
    RadioSet,
)

# Local Widget Imports
from .widgets.metric_group import MetricGroup
from .widgets.cpu_stats import CPUStatsGroup
from .widgets.memory import MemoryGroup
from .widgets.disk import DiskUsageGroup
from .widgets.network import NetworkIOGroup
from .widgets.system_info import SystemInfoGroup


# ----------------------------------------------------------------------------
# 1. CSS - STYLING
# ----------------------------------------------------------------------------

DEFAULT_CSS = """
Screen {
    background: #0a0a0a;
    color: #f0f0f0;
}

TabbedContent {
    background: #1a1a1a;
}

TabPane {
    padding: 1 2;
}

MetricGroup {
    border: round #4a4a4a;
    background: #121212;
    margin-bottom: 1;
    padding: 0 1;
}

MetricGroup > Label {
    width: 100%;
    background: #2a2a2a;
    color: #e0e0e0;
    padding: 0 1;
    border-bottom: thick #4a4a4a;
    text-style: bold;
}

.stat-title {
    color: #888;
    text-style: bold;
    margin-top: 1;
}

#ui-editor-sidebar {
    width: 30%;
    min-width: 25;
    border-right: thick #2a2a2a;
    padding-right: 2;
    margin-right: 2;
}

.alert-highlight {
    background: #880000;
    color: white;
}
"""

# ----------------------------------------------------------------------------
# 2. MAIN APPLICATION
# ----------------------------------------------------------------------------

class TUIDashboardApp(App):
    """The main TUI Dashboard Application."""

    CSS = DEFAULT_CSS
    TITLE = "Modular TUI Dashboard"
    SUB_TITLE = "Live Stats, Config, and More"

    # --- State Management ---

    available_groups = {
        "cpu_stats": {"class": CPUStatsGroup, "name": "CPU Stats", "desc": "Shows real-time CPU load and per-core usage."},
        "memory": {"class": MemoryGroup, "name": "Memory", "desc": "Displays memory and swap usage."},
        "disk_usage": {"class": DiskUsageGroup, "name": "Disk Usage", "desc": "Shows disk space usage for mounted partitions."},
        "network_io": {"class": NetworkIOGroup, "name": "Network I/O", "desc": "Displays current network traffic (upload/download)."},
        "system_info": {"class": SystemInfoGroup, "name": "System Info", "desc": "Provides general system information like OS and hostname."},
    }

    active_groups: reactive[list[str]] = reactive(
        ["cpu_stats", "memory"]
    )

    latest_metrics: reactive[dict] = reactive({})

    # --- Data Loading ---

    CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"
    METRICS_LOG_PATH = Path(__file__).parent.parent / "logs" / "smo_metrics.jsonl"

    def load_config_to_ui(self) -> None:
        """Load config from YAML and populate the input fields."""
        try:
            with open(self.CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)

            alerts_config = config.get("alerts", {})
            self.query_one("#input_cpu_thresh", Input).value = str(alerts_config.get("cpu_percent", ""))
            self.query_one("#input_mem_thresh", Input).value = str(alerts_config.get("memory_percent", ""))

        except (IOError, yaml.YAMLError) as e:
            self.notify(f"Error loading config: {e}", severity="error")

    def save_config_from_ui(self) -> None:
        """Save the current UI input values to the config file."""
        try:
            with open(self.CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)

            config["alerts"]["cpu_percent"] = int(self.query_one("#input_cpu_thresh", Input).value)
            config["alerts"]["memory_percent"] = int(self.query_one("#input_mem_thresh", Input).value)

            with open(self.CONFIG_PATH, "w") as f:
                yaml.safe_dump(config, f)

            self.notify("Configuration saved successfully!", severity="information")

        except (IOError, yaml.YAMLError, ValueError) as e:
            self.notify(f"Error saving config: {e}", severity="error")


    def update_metrics(self) -> None:
        """Reads and parses the last line from the metrics log file."""
        if not self.METRICS_LOG_PATH.exists():
            self.sub_title = "Metrics log file not found."
            return

        try:
            with open(self.METRICS_LOG_PATH, "r", encoding="utf-8") as f:
                last_line = None
                for line in f:
                    if line.strip():
                        last_line = line

                if last_line:
                    self.latest_metrics = json.loads(last_line)

        except (json.JSONDecodeError, IOError) as e:
            self.sub_title = f"Error reading metrics: {e}"

    def watch_latest_metrics(self, old_metrics: dict, new_metrics: dict) -> None:
        """Called when self.latest_metrics changes. Passes data to visible widgets."""
        for group_id in self.active_groups:
            try:
                widget = self.query_one(f"#{group_id}", MetricGroup)
                if hasattr(widget, "update_data"):
                    widget.update_data(new_metrics)
            except NoMatches:
                continue

    def watch_active_groups(self, old_groups: list[str], new_groups: list[str]) -> None:
        """Called when self.active_groups changes. Updates the Live View tab."""
        try:
            live_view = self.query_one("#live-view-container", ScrollableContainer)
        except NoMatches:
            return

        live_view.remove_children()

        for group_id in new_groups:
            if group_id in self.available_groups:
                group_info = self.available_groups[group_id]
                new_widget = group_info["class"](title=group_info["name"], id=group_id)
                live_view.mount(new_widget)

        self.sub_title = f"Displaying {len(new_groups)} metric groups"

    # --- Main UI Composition ---

    def compose(self) -> ComposeResult:
        """Create the main layout and widgets for the app."""
        yield Header()

        with TabbedContent(initial="live_view_tab"):
            with TabPane("Live View", id="live_view_tab"):
                yield ScrollableContainer(id="live-view-container")

            with TabPane("Config Editor", id="config_editor_tab"):
                with Container(id="config-editor-container"):
                    yield Static("Edit Alert Thresholds:")
                    yield Input(placeholder="cpu_threshold: 80", id="input_cpu_thresh")
                    yield Input(placeholder="memory_threshold: 90", id="input_mem_thresh")
                    with Container(id="config-editor-buttons"):
                        yield Button("Save Changes", variant="success", id="save_config")
                        yield Button("Restore Defaults", variant="error", id="restore_config")

            with TabPane("UI Editor", id="ui_editor_tab"):
                with Horizontal(id="ui-editor-container"):
                    with VerticalScroll(id="ui-editor-sidebar"):
                        yield Label("Toggle Metric Groups:")
                        for group_id, info in self.available_groups.items():
                            is_active = group_id in self.active_groups
                            yield Switch(name=info["name"], value=is_active, id=f"toggle_{group_id}")

                    yield Static("Hover over a switch to see its description.", id="ui-editor-description")

                with Container(id="ui-editor-buttons"):
                    yield Button("Save UI", variant="primary", id="save_ui")
                    yield Button("Reset UI", variant="default", id="reset_ui")

            with TabPane("Log Exporter", id="log_exporter_tab"):
                with Container(id="log-exporter-container"):
                    yield Static("Select Export Format:")
                    with RadioSet(id="export_format"):
                        yield RadioButton("JSON", value=True)
                        yield RadioButton("CSV")
                        yield RadioButton("PDF")
                        yield RadioButton("Markdown")
                    yield Input(placeholder="/path/to/export.log", id="export_path")
                    yield Button("Export", variant="primary", id="export_logs")

        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        self.set_interval(2, self.update_metrics)
        self.load_config_to_ui()
        self.update_metrics()
        self.watch_active_groups(None, self.active_groups)


    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "save_ui":
            new_active_groups = []
            switches = self.query(Switch)
            for switch in switches:
                if switch.value:
                    group_id = switch.id.replace("toggle_", "")
                    new_active_groups.append(group_id)

            self.active_groups = new_active_groups
            self.query_one(TabbedContent).active = "live_view_tab"

        elif event.button.id == "save_config":
            self.save_config_from_ui()

        elif event.button.id == "restore_config":
            self.load_config_to_ui()
            self.notify("Restored unsaved changes from config file.", severity="information")

        elif event.button.id == "export_logs":
            self.export_logs()


    def on_switch_mouse_over(self, event: Switch.MouseOver) -> None:
        """Update description when hovering over a switch."""
        group_id = event.control.id.replace("toggle_", "")
        if group_id in self.available_groups:
            description = self.available_groups[group_id]["desc"]
            self.query_one("#ui-editor-description", Static).update(description)

    # --- Log Exporting ---

    def _flatten_dict(self, d: dict, parent_key: str = '', sep: str ='.') -> dict:
        items = []
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def export_logs(self) -> None:
        """Export metric logs to the specified format and path."""
        export_path_str = self.query_one("#export_path", Input).value
        if not export_path_str:
            self.notify("Export path cannot be empty.", severity="error")
            return

        export_path = Path(export_path_str)
        selected_format = self.query_one(RadioSet).pressed_button.label.plain.lower()

        try:
            with open(self.METRICS_LOG_PATH, "r", encoding="utf-8") as f:
                logs = [json.loads(line) for line in f if line.strip()]

            if not logs:
                self.notify("No logs to export.", severity="warning")
                return

            export_path.parent.mkdir(parents=True, exist_ok=True)

            if selected_format == "json":
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2)

            elif selected_format == "csv":
                flat_logs = [self._flatten_dict(log) for log in logs]
                if flat_logs:
                    headers = sorted(list(set(key for log in flat_logs for key in log.keys())))
                    with open(export_path, "w", newline='', encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=headers)
                        writer.writeheader()
                        writer.writerows(flat_logs)

            elif selected_format == "markdown":
                flat_logs = [self._flatten_dict(log) for log in logs]
                if flat_logs:
                    headers = sorted(list(set(key for log in flat_logs for key in log.keys())))
                    with open(export_path, "w", encoding="utf-8") as f:
                        f.write(f"| {' | '.join(headers)} |\n")
                        f.write(f"| {' | '.join(['---'] * len(headers))} |\n")
                        for log in flat_logs:
                            row = [str(log.get(h, '')) for h in headers]
                            f.write(f"| {' | '.join(row)} |\n")

            self.notify(f"Logs successfully exported to {export_path}", severity="information")

        except Exception as e:
            self.notify(f"Failed to export logs: {e}", severity="error")


# ----------------------------------------------------------------------------
# 3. RUN THE APP
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    app = TUIDashboardApp()
    app.run()
